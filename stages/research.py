"""Stage 2 — research substrates -> *-research.{md,json} (spec §5.2).

One parameterized track (BUILD | BUY). Flow: PLAN (LLM expands profile +
dimensions into diversified, profile-aware search queries) -> discover (search,
domain-diverse) -> fetch + cache content -> READ/REASON (LLM authors atomic
ClaimDrafts grounded in the cached sources) -> assert_claim (cache-constrained,
locator computed) -> verify (re-reads cache) -> filter -> per-dimension coverage.
The .md is generated from the filtered json so prose never drifts from evidence.
Idempotent via the input-hash guard; failures degrade to coverage gaps, never
crashes (spec §7).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

from pydantic import BaseModel

from agents import load_prompt
from engine.hashing import stage_input_hash
from engine.runstore import RunStore
from llm import flash_model, get_provider
from llm.provider import LLMProvider
from rubric import load_metrics
from skills.grounded_claim import (
    Claim,
    ClaimDraft,
    GroundingError,
    SourceCache,
    assert_claim,
    filter_claims,
    verify,
)
from stages.search import ddg_search
from engine.constants import (
    COST_WINDOW_BUDGET as _COST_WINDOW_BUDGET,
    COST_WINDOW_PAD as _COST_WINDOW_PAD,
    ENTITY_DISCOVERY_MAX_SOURCES as _ENTITY_DISCOVERY_MAX_SOURCES,
    ENTITY_DISCOVERY_QUERIES as _ENTITY_DISCOVERY_QUERIES,
    EXCERPT_CHARS as _EXCERPT_CHARS,
    MAX_PER_DOMAIN as _DEFAULT_MAX_PER_DOMAIN,
    MAX_SOURCES as _DEFAULT_MAX_SOURCES,
    MIN_CONTENT_CHARS as _MIN_CONTENT_CHARS,
    PER_QUERY as _DEFAULT_PER_QUERY,
)

# Deterministic "find the numbers" pass (Rule 5: non-language work stays in code).
# Pulls pricing/effort/date spans buried past the head excerpt to the front so
# truncation never starves the cost-tagged dimensions.
_COST_RE = re.compile(
    r"(\$\s?\d|€\s?\d|£\s?\d"
    r"|\d+\s?(?:/\s?mo|/\s?month|/\s?yr|/\s?year)"
    r"|per\s+(?:month|seat|user|year|query|request|1m|million)"
    r"|\b(?:team|engineer|developer|person|man)[- ]months?\b"
    r"|\bFTE\b|\b20\d{2}\b)",
    re.I,
)

Track = Literal["BUILD", "BUY"]
_TRACKS: tuple[Track, ...] = ("BUILD", "BUY")
_RESEARCH_NAMES: dict[Track, str] = {
    "BUILD": "build-research",
    "BUY": "buy-research",
}
_PROMPT_NAMES: dict[Track, str] = {
    "BUILD": "research_build",
    "BUY": "research_buy",
}
_VERIFY_REPORT_NAMES: dict[Track, str] = {
    "BUILD": "build-verify-report.json",
    "BUY": "buy-verify-report.json",
}
_DISCOVERY_NAMES: dict[Track, str] = {
    "BUILD": "build-entity-discovery",
    "BUY": "buy-entity-discovery",
}


class ResearchClaims(BaseModel):
    """Container for the LLM's structured output (a list of drafts)."""
    claims: list[ClaimDraft]


class PriorityDimension(BaseModel):
    id: str
    why: str


class PlannedQuery(BaseModel):
    query: str
    dimension: str


class QueryPlan(BaseModel):
    """Phase-A planner output: which dimensions matter + the queries to run."""
    priority_dimensions: list[PriorityDimension]
    queries: list[PlannedQuery]


class DiscoveryQueries(BaseModel):
    queries: list[str]


class CuratedEntity(BaseModel):
    name: str
    rationale: str
    commercial_twin: str | None = None


class EntityDiscovery(BaseModel):
    selected: list[CuratedEntity]
    excluded: list[str]
    source_urls: list[str]


@dataclass
class ResearchResult:
    track: str
    name: str
    skipped: bool
    kept: list[Claim] = field(default_factory=list)
    dropped: list[Claim] = field(default_factory=list)
    assert_rejected: list[dict] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)
    priority_dimensions: list[dict] = field(default_factory=list)
    coverage: list[dict] = field(default_factory=list)
    discovered_entities: list[str] = field(default_factory=list)


def _queries(capability: str, track: Track) -> list[str]:
    """Deterministic fallback used only if the LLM planner is unavailable."""
    cap = capability.strip()
    if track == "BUILD":
        return [f"{cap} open source", f"how to build {cap}",
                f"{cap} self-hosting cost", f"{cap} maintenance challenges"]
    return [f"{cap} pricing", f"{cap} vendors comparison",
            f"best {cap} platform", f"{cap} API integration"]


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return url


def _discover(queries, searcher, max_sources, per_query, max_per_domain) -> list[str]:
    """Domain-diverse discovery: cap sources per domain so one SEO listicle/site
    cannot dominate the evidence pool."""
    seen: list[str] = []
    per_domain: dict[str, int] = {}
    for query in queries:
        for url in searcher(query, per_query):
            if url in seen:
                continue
            dom = _domain(url)
            if per_domain.get(dom, 0) >= max_per_domain:
                continue
            seen.append(url)
            per_domain[dom] = per_domain.get(dom, 0) + 1
            if len(seen) >= max_sources:
                return seen
    return seen


def _excerpt(content: str, head_budget: int) -> str:
    """Head of the content plus any cost/pricing/date windows that fall past the
    head, so deep pricing tables survive truncation (the cost dims are the
    schedule risk, spec §7)."""
    if len(content) <= head_budget:
        return content
    head = content[:head_budget]
    windows: list[str] = []
    used = 0
    for m in _COST_RE.finditer(content, head_budget):
        start = max(0, m.start() - _COST_WINDOW_PAD)
        end = min(len(content), m.end() + _COST_WINDOW_PAD)
        win = content[start:end]
        if any(win in w or w in win for w in windows):
            continue
        windows.append(win)
        used += len(win)
        if used >= _COST_WINDOW_BUDGET:
            break
    if not windows:
        return head
    return head + "\n…\n" + "\n…\n".join(windows)


def _as_track(track: str) -> Track:
    if track not in _TRACKS:
        raise ValueError(f"unknown track {track!r}")
    return cast(Track, track)


def _track_dimensions(track: Track) -> list[dict]:
    return [d for d in load_metrics() if track in d.get("tracks", [])]


def _dimensions_block(dims: list[dict], track: Track) -> str:
    lines = ["ALLOWED DIMENSIONS (use these ids):"]
    for d in dims:
        hints = "; ".join(d["look_for"][track])
        lines.append(f"- {d['id']} ({d['name']}): {d['question']} | look for: {hints}")
    return "\n".join(lines)


def _sources_block(cache: SourceCache, urls: list[str]) -> str:
    blocks = [
        "SOURCES (cite only these urls; copy display_quote verbatim from "
        "the matching content):"
    ]
    for url in urls:
        meta = cache.get_meta(url)
        dated = f" (dated: {meta.get('source_date')})" if meta.get("source_date") else ""
        excerpt = _excerpt(cache.get_content(url), _EXCERPT_CHARS)
        blocks.append(f"\nurl: {url}{dated}\ncontent:\n{excerpt}\n---")
    return "\n".join(blocks)


def _profile_block(profile: dict) -> str:
    # NB: deliberately omits soft_steer — it is synthesis-only (spec §4); a gate-3
    # steer edit must not change the research evidence pool. Feed the decision
    # signals research IS allowed to reason over (and that ARE in the hash).
    need = profile["need"]
    intent = profile.get("intent", {})
    res = profile.get("resources", {})
    con = profile.get("constraints", {})
    return "\n".join([
        "PROFILE",
        f"capability: {need['capability']}",
        f"business_context: {need.get('business_context', '')}",
        f"problem: {need.get('problem', '')}",
        "core_value_proximity: "
        f"{intent.get('core_value_proximity', '')} — {intent.get('rationale', '')}",
        f"resources: eng_headcount={res.get('eng_headcount', '?')}, "
        f"skills={res.get('relevant_skills', [])}, budget={res.get('budget_note', '')}, "
        f"runway={res.get('runway_note', '')}, "
        f"expected_scale={res.get('expected_scale', '')}, "
        f"procurement_process={res.get('procurement_process', '')}",
        f"constraints: compliance={con.get('compliance', [])}, "
        f"data_sensitivity={con.get('data_sensitivity', '')}, "
        f"data_residency={con.get('data_residency', '')}, "
        f"required_certifications={con.get('required_certifications', [])}, "
        f"existing_stack={con.get('existing_stack', [])}, "
        f"integration_requirements={con.get('integration_requirements', [])}, "
        f"timeline_hard_stop={con.get('timeline_hard_stop', '')}",
        f"customization_need: {profile.get('customization_need', '')}",
    ])


def _discovery_query_prompt(profile: dict, track: Track) -> str:
    cap = profile["need"]["capability"]
    ctx = profile["need"].get("business_context", "")
    if track == "BUY":
        focus = (
            "commercial vendors, SaaS platforms, and APIs. "
            "Target comparison articles, listicles ('best X providers'), "
            "G2/Capterra/analyst reports, and industry reviews."
        )
    else:
        focus = (
            "open-source libraries, frameworks, and self-hostable tools. "
            "Target OSS comparison articles ('best X library'), GitHub Awesome lists, "
            "engineering blog comparisons, and benchmark articles."
        )
    profile_ctx = f"Capability: {cap}"
    if ctx:
        profile_ctx += f"\nBusiness context: {ctx}"
    return (
        f"Generate {_ENTITY_DISCOVERY_QUERIES} diverse web search queries to discover "
        f"the leading {focus}\n\n"
        f"{profile_ctx}\n\n"
        "Return queries that surface authoritative comparison sources, "
        "not individual vendor marketing pages."
    )


def _curation_prompt(
    profile: dict, track: Track, content_block: str,
    commercial_twins_hint: list[str] | None,
) -> str:
    cap = profile["need"]["capability"]
    ctx = profile["need"].get("business_context", "")
    if track == "BUY":
        entity_type = "commercial vendors, SaaS platforms, and API providers"
        twin_note = "Set commercial_twin to null for all entries."
    else:
        entity_type = "open-source libraries, frameworks, and self-hostable tools"
        twin_note = (
            "For each OSS project identify its commercial_twin if one exists "
            "(e.g., 'Qdrant' → commercial_twin='Qdrant Cloud'). "
            "Set null if no managed/cloud version exists."
        )

    cap_ctx = f"Capability: {cap}"
    if ctx:
        cap_ctx += f"\nBusiness context: {ctx}"

    twins_block = ""
    if commercial_twins_hint:
        twins_block = (
            "\nHINT — these commercial products map to OSS projects from the BUILD track "
            "(validates commercial_twin fields): " + ", ".join(commercial_twins_hint) + "\n"
        )

    return (
        f"Curate a list of {track} options for: {cap_ctx}\n\n"
        f"From the web research below, select the {entity_type} that are:\n"
        "1. Mentioned across multiple sources (cross-validated, not just self-reported)\n"
        "2. Currently active and maintained\n"
        "3. Relevant to the capability and business context above\n"
        "4. Have real documentation or pricing worth deeper research\n\n"
        f"{twin_note}{twins_block}\n"
        "Put explicitly rejected candidates in the `excluded` list.\n\n"
        f"WEB RESEARCH CONTENT:\n{content_block}"
    )


def _discover_entities_via_search(
    profile: dict,
    track: Track,
    searcher: Callable[[str, int], list[str]],
    cache: SourceCache,
    provider: LLMProvider,
    model: str,
    *,
    store: RunStore,
    commercial_twins_hint: list[str] | None = None,
) -> EntityDiscovery:
    """Phase 0: web-search-backed entity discovery.

    Generates discovery queries via LLM, fetches listicles/comparison pages,
    then asks the LLM to curate a reasoned list of vendors (BUY) or OSS
    projects (BUILD). Never relies on LLM world-knowledge for entity names —
    everything is derived from fetched content.
    """
    # 1) Generate discovery queries from profile
    try:
        disc = provider.complete(
            _discovery_query_prompt(profile, track),
            response_schema=DiscoveryQueries,
            model=model,
        )
        queries = disc.queries[:_ENTITY_DISCOVERY_QUERIES]
    except Exception:  # noqa: BLE001 — deterministic fallback
        cap = profile["need"]["capability"]
        if track == "BUY":
            queries = [
                f"best {cap} vendors comparison",
                f"top {cap} platforms api providers",
                f"{cap} software comparison review",
            ]
        else:
            queries = [
                f"best open source {cap} library",
                f"{cap} framework comparison github",
                f"awesome {cap} tools self-hosted",
            ]

    # 2) Collect URLs — no domain cap for discovery (listicles are ideal here)
    seen: list[str] = []
    for query in queries:
        for url in searcher(query, _ENTITY_DISCOVERY_MAX_SOURCES):
            if url not in seen:
                seen.append(url)
            if len(seen) >= _ENTITY_DISCOVERY_MAX_SOURCES:
                break
        if len(seen) >= _ENTITY_DISCOVERY_MAX_SOURCES:
            break

    # 3) Fetch (Jina fallback already in cache.fetch)
    fetched_urls: list[str] = []
    for url in seen:
        try:
            content = cache.fetch(url)
            if len(content.strip()) >= _MIN_CONTENT_CHARS:
                fetched_urls.append(url)
        except Exception:  # noqa: BLE001
            pass

    # 4) LLM curation over all fetched content
    if fetched_urls:
        content_block = "\n---\n".join(
            f"[{url}]\n{cache.get_content(url)[:_EXCERPT_CHARS]}"
            for url in fetched_urls
        )
        try:
            discovery = provider.complete(
                _curation_prompt(profile, track, content_block, commercial_twins_hint),
                response_schema=EntityDiscovery,
                model=model,
            )
        except Exception:  # noqa: BLE001
            discovery = EntityDiscovery(selected=[], excluded=[], source_urls=fetched_urls)
    else:
        discovery = EntityDiscovery(selected=[], excluded=[], source_urls=[])

    if not discovery.source_urls:
        discovery = discovery.model_copy(update={"source_urls": fetched_urls})

    # 5) Persist artifact
    store.artifact_path(f"{_DISCOVERY_NAMES[track]}.json").write_text(
        json.dumps(discovery.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return discovery


def _entity_context_block(discovery: EntityDiscovery, track: Track) -> str:
    if not discovery.selected:
        return ""
    label = "commercial vendors/platforms" if track == "BUY" else "OSS projects/frameworks"
    lines = [f"DISCOVERED_ENTITIES ({label} found via web search — use these names in your queries):"]
    for e in discovery.selected:
        twin = f" [commercial_twin: {e.commercial_twin}]" if e.commercial_twin else ""
        lines.append(f"- {e.name}{twin}: {e.rationale}")
    return "\n".join(lines)


def _plan_queries(
    plan_prompt, profile, track: Track, dims, provider, model,
    entity_context: str = "",
) -> QueryPlan | None:
    """Phase A: LLM expands profile + dimensions into diversified, profile-aware
    queries. Degrades to None (-> deterministic fallback) rather than crashing."""
    parts = [plan_prompt, f"TRACK: {track}", _profile_block(profile), _dimensions_block(dims, track)]
    if entity_context:
        parts.append(entity_context)
    try:
        return provider.complete("\n\n".join(parts), response_schema=QueryPlan, model=model)
    except Exception:  # noqa: BLE001 — a planner failure is degradation, not a crash
        return None


def _author(
    prompt, profile, track: Track, dims, cache, urls, provider, model,
    entity_context: str = "",
) -> list[ClaimDraft]:
    parts = [prompt, _profile_block(profile), _dimensions_block(dims, track)]
    if entity_context:
        parts.append(entity_context)
    parts.append(_sources_block(cache, urls))
    out = provider.complete("\n\n".join(parts), response_schema=ResearchClaims, model=model)
    return out.claims


def _coverage(track_dims: list[dict], kept: list[Claim], priority_ids: set[str]) -> list[dict]:
    """Per-dimension coverage so Gate 2 + synthesis see what came back empty."""
    rows = []
    for d in track_dims:
        count = sum(1 for c in kept if c.dimension == d["id"])
        rows.append({
            "id": d["id"], "name": d["name"],
            "covered": count > 0, "claim_count": count,
            "priority": d["id"] in priority_ids,
        })
    return rows


def _render_md(track: Track, kept: list[Claim], gaps: list[str], coverage: list[dict]) -> str:
    by_dim: dict[str, list[Claim]] = {}
    for c in kept:
        by_dim.setdefault(c.dimension, []).append(c)
    lines = [f"# {track} research", "", f"{len(kept)} verified claims.", ""]
    for dim in sorted(by_dim):
        lines.append(f"## {dim}")
        for c in by_dim[dim]:
            flags = f" _[{', '.join(c.flags)}]_" if c.flags else ""
            src = c.sources[0]
            lines.append(f"- {c.text} ({c.status.value}){flags}")
            lines.append(f"  > \"{src.display_quote}\" — [{src.title or src.url}]({src.url})")
        lines.append("")
    if coverage:
        lines.append("## Dimension coverage")
        for row in coverage:
            mark = "✓" if row["covered"] else "✗"
            star = " ★" if row["priority"] else ""
            lines.append(
                f"- {mark} {row['id']} {row['name']}{star} — "
                f"{row['claim_count']} claim(s)"
            )
        lines.append("")
    if gaps:
        lines.append("## Coverage gaps")
        lines += [f"- {g}" for g in gaps]
    return "\n".join(lines)


def _load_skipped_result(track: Track, name: str, json_path: Path) -> ResearchResult:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return ResearchResult(
        track=track,
        name=name,
        skipped=True,
        kept=[Claim.model_validate(c) for c in data["claims"]],
        dropped=[Claim.model_validate(c) for c in data.get("dropped", [])],
        coverage_gaps=data.get("coverage_gaps", []),
        priority_dimensions=data.get("priority_dimensions", []),
        coverage=data.get("coverage", []),
        discovered_entities=data.get("discovered_entities", []),
    )


def _write_verify_report_section(store: RunStore, track: Track, section: dict) -> str:
    name = _VERIFY_REPORT_NAMES[track]
    store.artifact_path(name).write_text(
        json.dumps(section, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return name


def _write_research_outputs(
    store: RunStore,
    *,
    track: Track,
    json_path: Path,
    md_path: Path,
    kept: list[Claim],
    dropped: list[Claim],
    verified: list[Claim],
    assert_rejected: list[dict],
    priority: list[dict],
    coverage: list[dict],
    gaps: list[str],
    discovered_entities: list[str],
) -> str:
    json_path.write_text(json.dumps({
        "track": track,
        "discovered_entities": discovered_entities,
        "claims": [c.model_dump() for c in kept],
        "dropped": [c.model_dump() for c in dropped],
        "kept_count": len(kept),
        "dropped_count": len(dropped),
        "priority_dimensions": priority,
        "coverage": coverage,
        "coverage_gaps": gaps,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_render_md(track, kept, gaps, coverage), encoding="utf-8")
    return _write_verify_report_section(store, track, {
        "labeled": [{"id": c.id, "status": c.status.value} for c in verified],
        "dropped_unsupported": [{"id": c.id} for c in dropped],
        "assert_rejected": assert_rejected,
        "priority_dimensions": priority,
        "coverage": coverage,
        "coverage_gaps": gaps,
    })


def merge_verify_reports(run_dir: str) -> dict:
    """Combine per-track verify reports after BUILD and BUY branches finish."""
    store = RunStore(run_dir)
    report: dict[str, dict] = {}
    for track in _TRACKS:
        path = store.artifact_path(_VERIFY_REPORT_NAMES[track])
        if path.exists():
            report[track] = json.loads(path.read_text(encoding="utf-8"))
    out = store.artifact_path("verify-report.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    store.set_stage("research", status="done", artifacts=["verify-report.json"])
    return report


def run_research(
    track: str,
    run_dir: str,
    *,
    profile_name: str = "profile.json",
    provider: LLMProvider | None = None,
    model: str | None = None,
    searcher: Callable[[str, int], list[str]] | None = None,
    max_sources: int = _DEFAULT_MAX_SOURCES,
    per_query: int = _DEFAULT_PER_QUERY,
    max_per_domain: int = _DEFAULT_MAX_PER_DOMAIN,
) -> ResearchResult:
    track = _as_track(track)
    store = RunStore(run_dir)
    name = _RESEARCH_NAMES[track]
    prompt = load_prompt(_PROMPT_NAMES[track])
    plan_prompt = load_prompt("research_query_plan")
    model = model or flash_model()
    engine_version = os.environ.get("ENGINE_VERSION", "0")
    profile_path = store.artifact_path(profile_name)
    json_path = store.artifact_path(f"{name}.json")
    md_path = store.artifact_path(f"{name}.md")

    # Hash only the profile fields research actually uses (NOT soft_steer, which
    # is synthesis-only) so a gate-3 steer edit does not re-run research (§4).
    # The planner prompt rides in `extra` so editing either prompt invalidates.
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    projection = json.dumps({
        "need": profile["need"],
        "intent": profile.get("intent"),
        "resources": profile.get("resources"),
        "constraints": profile.get("constraints"),
        "customization_need": profile.get("customization_need"),
        "plan_prompt": plan_prompt,
    }, sort_keys=True).encode("utf-8")
    current_hash = stage_input_hash(
        input_paths=[], prompt=prompt, model_id=model,
        engine_version=engine_version, extra=projection,
    )
    record = store.get_stage(name)
    if (
        record
        and record.status == "done"
        and record.recorded_hash == current_hash
        and json_path.exists()
    ):
        return _load_skipped_result(track, name, json_path)

    provider = provider or get_provider()
    searcher = searcher or ddg_search
    capability = profile["need"]["capability"]
    track_dims = _track_dimensions(track)

    # 0a) ENTITY DISCOVERY — web-search-backed; never LLM world-knowledge.
    #     For BUY, try to seed with commercial_twins from BUILD if it already ran.
    commercial_twins_hint: list[str] | None = None
    if track == "BUY":
        build_disc_path = store.artifact_path("build-entity-discovery.json")
        if build_disc_path.exists():
            try:
                build_disc = json.loads(build_disc_path.read_text(encoding="utf-8"))
                twins = [
                    e["commercial_twin"]
                    for e in build_disc.get("selected", [])
                    if e.get("commercial_twin")
                ]
                if twins:
                    commercial_twins_hint = twins
            except Exception:  # noqa: BLE001
                pass

    discovery = _discover_entities_via_search(
        profile, track, searcher, SourceCache(run_dir), provider, model,
        store=store, commercial_twins_hint=commercial_twins_hint,
    )
    entity_context = _entity_context_block(discovery, track)

    # 0b) PLAN — LLM expands profile + dimensions into diversified, profile-aware
    # queries; degrade to deterministic templates if the planner is unavailable.
    plan = _plan_queries(plan_prompt, profile, track, track_dims, provider, model, entity_context)
    if plan and plan.queries:
        query_strings = [q.query for q in plan.queries]
        priority = [{"id": p.id, "why": p.why} for p in plan.priority_dimensions]
    else:
        query_strings = _queries(capability, track)
        priority = []
        gaps_planner = "query planner unavailable; used fallback templates"
    priority_ids = {p["id"] for p in priority}

    # 1) discover + 2) fetch/cache
    cache = SourceCache(run_dir)
    gaps: list[str] = []
    if not (plan and plan.queries):
        gaps.append(gaps_planner)
    cached: list[str] = []
    for url in _discover(query_strings, searcher, max_sources, per_query, max_per_domain):
        if cache.has(url):
            if len(cache.get_content(url).strip()) >= _MIN_CONTENT_CHARS:
                cached.append(url)
            else:
                gaps.append(f"thin content: {url}")
            continue
        try:
            content = cache.fetch(url)
        except Exception as exc:  # noqa: BLE001 — a bad fetch is a gap, not a crash
            gaps.append(f"fetch failed: {url} ({type(exc).__name__})")
            continue
        if len(content.strip()) >= _MIN_CONTENT_CHARS:
            cached.append(url)
        else:
            gaps.append(f"thin content: {url}")
    if not cached:
        gaps.append(f"no fetchable sources for track {track}")

    # 3) author claims grounded in cached content
    drafts: list[ClaimDraft] = []
    if cached:
        try:
            drafts = _author(prompt, profile, track, track_dims, cache, cached, provider,
                              model, entity_context)
        except Exception as exc:  # noqa: BLE001 — an authoring failure is a gap, not a crash
            gaps.append(f"claim authoring failed: {type(exc).__name__}: {exc}")

    # 4) assert (cache-constrained; locator computed; rejects ungrounded)
    claims: list[Claim] = []
    assert_rejected: list[dict] = []
    for draft in drafts:
        try:
            claims.append(assert_claim(draft.text, draft.sources, draft.dimension, track, cache))
        except GroundingError as exc:
            assert_rejected.append({"text": draft.text, "reason": str(exc)})

    # 5) verify (re-reads cached bytes) + 6) filter
    verified: list[Claim] = []
    for c in claims:
        try:
            verified.append(verify(c, cache, provider))
        except Exception as exc:  # noqa: BLE001 — a verify failure is a gap, not a crash
            gaps.append(f"verification failed for claim {c.id}: {type(exc).__name__}: {exc}")
    filtered = filter_claims(verified)

    # 6b) per-dimension coverage; an empty PRIORITY dimension is a surfaced gap.
    coverage = _coverage(track_dims, filtered.kept, priority_ids)
    for row in coverage:
        if row["priority"] and not row["covered"]:
            gaps.append(f"no evidence for priority dimension {row['id']} ({row['name']})")

    discovered_entity_names = [e.name for e in discovery.selected]
    discovery_artifact = f"{_DISCOVERY_NAMES[track]}.json"

    # 7) persist (json is truth; md generated from it)
    verify_report_name = _write_research_outputs(
        store,
        track=track,
        json_path=json_path,
        md_path=md_path,
        kept=filtered.kept,
        dropped=filtered.dropped,
        verified=verified,
        assert_rejected=assert_rejected,
        priority=priority,
        coverage=coverage,
        gaps=gaps,
        discovered_entities=discovered_entity_names,
    )
    store.set_stage(name, status="done", recorded_hash=current_hash,
                    artifacts=[json_path.name, md_path.name, verify_report_name, discovery_artifact])

    return ResearchResult(
        track=track, name=name, skipped=False, kept=filtered.kept, dropped=filtered.dropped,
        assert_rejected=assert_rejected, coverage_gaps=gaps,
        priority_dimensions=priority, coverage=coverage,
        discovered_entities=discovered_entity_names,
    )
