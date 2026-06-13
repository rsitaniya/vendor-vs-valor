"""Stage 2 — research substrates -> *-research.{md,json} (spec §5.2).

One parameterized track (BUILD | BUY). Flow: discover (search) -> fetch + cache
content -> LLM authors atomic ClaimDrafts grounded in the cached sources ->
assert_claim (cache-constrained, locator computed) -> verify (re-reads cache) ->
filter. The .md is generated from the filtered json so prose never drifts from
evidence. Idempotent via the input-hash guard; failures degrade to coverage
gaps, never crashes (spec §7).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field

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

_MIN_CONTENT_CHARS = 400
_EXCERPT_CHARS = 2500


class ResearchClaims(BaseModel):
    """Container for the LLM's structured output (a list of drafts)."""
    claims: list[ClaimDraft]


@dataclass
class ResearchResult:
    track: str
    name: str
    skipped: bool
    kept: list[Claim] = field(default_factory=list)
    dropped: list[Claim] = field(default_factory=list)
    assert_rejected: list[dict] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)


def _queries(capability: str, track: str) -> list[str]:
    cap = capability.strip()
    if track == "BUILD":
        return [f"{cap} open source", f"how to build {cap}",
                f"{cap} self-hosting cost", f"{cap} maintenance challenges"]
    return [f"{cap} pricing", f"{cap} vendors comparison",
            f"best {cap} platform", f"{cap} API integration"]


def _discover(queries, searcher, max_sources, per_query) -> list[str]:
    seen: list[str] = []
    for query in queries:
        for url in searcher(query, per_query):
            if url not in seen:
                seen.append(url)
            if len(seen) >= max_sources:
                return seen
    return seen


def _track_dimensions(track: str) -> list[dict]:
    return [d for d in load_metrics() if track in d.get("tracks", [])]


def _dimensions_block(dims: list[dict], track: str) -> str:
    lines = ["ALLOWED DIMENSIONS (use these ids):"]
    for d in dims:
        hints = "; ".join(d["look_for"][track])
        lines.append(f"- {d['id']} ({d['name']}): {d['question']} | look for: {hints}")
    return "\n".join(lines)


def _sources_block(cache: SourceCache, urls: list[str]) -> str:
    blocks = ["SOURCES (cite only these urls; copy display_quote verbatim from the matching content):"]
    for url in urls:
        excerpt = cache.get_content(url)[:_EXCERPT_CHARS]
        blocks.append(f"\nurl: {url}\ncontent:\n{excerpt}\n---")
    return "\n".join(blocks)


def _profile_block(profile: dict) -> str:
    need = profile["need"]
    return (f"PROFILE\ncapability: {need['capability']}\ncontext: {need['business_context']}\n"
            f"problem: {need['problem']}\nsoft_steer: {profile.get('soft_steer', '')}\n"
            f"customization_need: {profile.get('customization_need', '')}")


def _author(prompt, profile, track, dims, cache, urls, provider, model) -> list[ClaimDraft]:
    context = "\n\n".join([
        prompt,
        _profile_block(profile),
        _dimensions_block(dims, track),
        _sources_block(cache, urls),
    ])
    out = provider.complete(context, response_schema=ResearchClaims, model=model)
    return out.claims


def _render_md(track: str, kept: list[Claim], gaps: list[str]) -> str:
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
    if gaps:
        lines.append("## Coverage gaps")
        lines += [f"- {g}" for g in gaps]
    return "\n".join(lines)


def _merge_verify_report(store: RunStore, track: str, section: dict) -> None:
    path = store.artifact_path("verify-report.json")
    report = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    report[track] = section
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def run_research(
    track: str,
    run_dir: str,
    *,
    profile_name: str = "profile.json",
    provider: LLMProvider | None = None,
    model: str | None = None,
    searcher: Callable[[str, int], list[str]] | None = None,
    max_sources: int = 6,
    per_query: int = 4,
) -> ResearchResult:
    if track not in ("BUILD", "BUY"):
        raise ValueError(f"unknown track {track!r}")
    store = RunStore(run_dir)
    name = "build-research" if track == "BUILD" else "buy-research"
    prompt = load_prompt("research_build" if track == "BUILD" else "research_buy")
    model = model or flash_model()
    engine_version = os.environ.get("ENGINE_VERSION", "0")
    profile_path = store.artifact_path(profile_name)
    json_path = store.artifact_path(f"{name}.json")
    md_path = store.artifact_path(f"{name}.md")

    # Hash only the profile fields research actually uses (not soft_steer, which
    # is synthesis-only) so a gate-3 steer edit does not re-run research (§4).
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    projection = json.dumps({
        "need": profile["need"],
        "constraints": profile.get("constraints"),
        "customization_need": profile.get("customization_need"),
    }, sort_keys=True).encode("utf-8")
    current_hash = stage_input_hash(
        input_paths=[], prompt=prompt, model_id=model,
        engine_version=engine_version, extra=projection,
    )
    record = store.get_stage(name)
    if record and record.status == "done" and record.recorded_hash == current_hash and json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return ResearchResult(
            track=track, name=name, skipped=True,
            kept=[Claim.model_validate(c) for c in data["claims"]],
            dropped=[Claim.model_validate(c) for c in data.get("dropped", [])],
            coverage_gaps=data.get("coverage_gaps", []),
        )

    provider = provider or get_provider()
    searcher = searcher or ddg_search
    capability = profile["need"]["capability"]

    # 1) discover + 2) fetch/cache
    cache = SourceCache(run_dir)
    gaps: list[str] = []
    cached: list[str] = []
    for url in _discover(_queries(capability, track), searcher, max_sources, per_query):
        if cache.has(url):
            cached.append(url)
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
    drafts = (_author(prompt, profile, track, _track_dimensions(track), cache, cached, provider, model)
              if cached else [])

    # 4) assert (cache-constrained; locator computed; rejects ungrounded)
    claims: list[Claim] = []
    assert_rejected: list[dict] = []
    for draft in drafts:
        try:
            claims.append(assert_claim(draft.text, draft.sources, draft.dimension, track, cache))
        except GroundingError as exc:
            assert_rejected.append({"text": draft.text, "reason": str(exc)})

    # 5) verify (re-reads cached bytes) + 6) filter
    verified = [verify(c, cache, provider) for c in claims]
    filtered = filter_claims(verified)

    # 7) persist (json is truth; md generated from it)
    json_path.write_text(json.dumps({
        "track": track,
        "claims": [c.model_dump() for c in filtered.kept],
        "dropped": [c.model_dump() for c in filtered.dropped],
        "kept_count": len(filtered.kept),
        "dropped_count": len(filtered.dropped),
        "coverage_gaps": gaps,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_render_md(track, filtered.kept, gaps), encoding="utf-8")
    _merge_verify_report(store, track, {
        "labeled": [{"id": c.id, "status": c.status.value} for c in verified],
        "dropped_unsupported": [{"id": c.id} for c in filtered.dropped],
        "assert_rejected": assert_rejected,
        "coverage_gaps": gaps,
    })
    store.set_stage(name, status="done", recorded_hash=current_hash,
                    artifacts=[json_path.name, md_path.name, "verify-report.json"])

    return ResearchResult(
        track=track, name=name, skipped=False, kept=filtered.kept, dropped=filtered.dropped,
        assert_rejected=assert_rejected, coverage_gaps=gaps,
    )
