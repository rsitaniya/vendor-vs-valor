"""Stage 3 — synthesis (four-path lenses) + challenger -> strategy.{md,json}.

Two LLM steps over the same two evidence pools, then deterministic assembly:
(a) synthesize: a dossier per path + recommendation + decisive factors + open
    questions + the engine's own runner-up.
(b) challenger (degradable): the strongest *cited* case for a different path,
    shown as a first-class counter-recommendation when it mounts one. It can also
    concur (return the recommended path) or degrade (invalid/ungrounded output);
    all three states are recorded and rendered, never silently swallowed.
(c) assemble (code): strategy.md (the deliverable, md is truth) + strategy.json
    (section manifest + referenced claim ids + a compact claims index the report
    renders from). Idempotent via the input-hash guard.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import BaseModel

from agents import load_prompt
from engine.hashing import stage_input_hash
from engine.runstore import RunStore
from llm import get_provider, pro_model
from llm.provider import LLMProvider
from rubric import CANONICAL_PATHS, load_paths
from skills.grounded_claim import PRICE_CONFLICT
from skills.schema_stage import ContractError

_INPUTS = ("profile.json", "build-research.json", "buy-research.json")
_PATH_TITLES = {"build": "Build", "buy": "Buy", "buy_then_extend": "Buy-then-extend",
                "adopt_self_host": "Adopt & self-host"}
_MONEY_RE = re.compile(r"(?:\$|USD\s*)(\d[\d,]*(?:\.\d+)?)\s*(k|m|thousand|million)?", re.I)


# --- LLM output shapes (no defaults -> Gemini struct-output safe) ---

class CitedBullet(BaseModel):
    text: str
    cited_claim_ids: list[str]


class PathDossier(BaseModel):
    path: str
    pros: list[CitedBullet]
    cons: list[CitedBullet]
    key_risks: list[CitedBullet]
    reversibility: CitedBullet


class DecisiveFactor(BaseModel):
    dimension: str
    why: str


class SynthesisOutput(BaseModel):
    recommendation_path: str
    thesis: str
    dossiers: list[PathDossier]
    decisive_factors: list[DecisiveFactor]
    open_questions: list[str]
    runner_up_path: str
    runner_up_wins_when: list[str]


class ChallengerOutput(BaseModel):
    runner_up_path: str
    wins_when: list[str]
    case: str
    cited_claim_ids: list[str]


@dataclass
class SynthesisResult:
    skipped: bool
    strategy: dict


# --- context builders ---

def _claims_block(claims_index: dict[str, dict]) -> str:
    lines = ["EVIDENCE (cite by id; only these ids exist):"]
    for cid, c in claims_index.items():
        src = c["sources"][0]
        flags = f" flags={c['flags']}" if c.get("flags") else ""
        lines.append(f"[{cid}] ({c['track']}/{c['dimension']}/{c['status']}){flags} "
                     f"{c['text']} | source: {src['url']}")
    return "\n".join(lines)


def _source_host(claim: dict) -> str:
    url = claim["sources"][0]["url"]
    return urlparse(url).netloc.lower().removeprefix("www.")


def _money_values(claim: dict) -> list[float]:
    src = claim["sources"][0]
    text = f"{claim.get('text', '')} {src.get('display_quote', '')}"
    values: list[float] = []
    for match in _MONEY_RE.finditer(text):
        value = float(match.group(1).replace(",", ""))
        scale = (match.group(2) or "").lower()
        if scale in {"k", "thousand"}:
            value *= 1_000
        elif scale in {"m", "million"}:
            value *= 1_000_000
        values.append(value)
    return values


def _flag_price_conflicts(claims_index: dict[str, dict]) -> dict[str, dict]:
    """Flag obvious conflicting cost claims from the same source host/dimension.

    MVP deliberately stays conservative: it only flags numeric money conflicts
    where the track, dimension, and source host match. It does not try to solve
    vendor normalization across arbitrary domains.
    """
    flagged = {cid: {**claim, "flags": list(claim.get("flags", []))}
               for cid, claim in claims_index.items()}
    groups: dict[tuple[str, str, str], list[tuple[str, float]]] = defaultdict(list)
    for cid, claim in flagged.items():
        if not claim.get("cost_tagged"):
            continue
        for value in _money_values(claim):
            groups[(claim["track"], claim["dimension"], _source_host(claim))].append((cid, value))

    for entries in groups.values():
        values = [value for _, value in entries]
        if len(values) < 2 or min(values) <= 0 or max(values) / min(values) < 1.2:
            continue
        for cid, _ in entries:
            if PRICE_CONFLICT not in flagged[cid]["flags"]:
                flagged[cid]["flags"].append(PRICE_CONFLICT)
    return flagged


def _profile_block(profile: dict) -> str:
    need = profile["need"]
    return (f"PROFILE\ncapability: {need['capability']}\ncontext: {need['business_context']}\n"
            f"problem: {need['problem']}\nintent: {profile.get('intent', {})}\n"
            f"constraints: {profile.get('constraints', {})}\n"
            f"customization_need: {profile.get('customization_need')}\n"
            f"soft_steer: {profile.get('soft_steer', '')}")


# --- validation + assembly ---

def _validate_known_claim_ids(ids: list[str], claims_index: dict[str, dict], context: str) -> None:
    unknown = sorted({cid for cid in ids if cid not in claims_index})
    if unknown:
        raise ContractError(f"{context} cites unknown claim ids: {unknown}")


def _open_questions_cover_path(open_questions: list[str], path: str) -> bool:
    title = _PATH_TITLES[path].lower()
    tokens = {path.lower(), title, title.replace("&", "and")}
    return any(any(token in question.lower() for token in tokens) for question in open_questions)


def _has_buy_api_surface_claim(ids: list[str], claims_index: dict[str, dict]) -> bool:
    return any(
        claims_index[cid]["track"] == "BUY" and claims_index[cid]["dimension"] == "m10"
        for cid in ids
        if cid in claims_index
    )


def _evaluate_challenger(
    cand: ChallengerOutput,
    recommendation_path: str,
    synth_runner_up_path: str,
    claims_index: dict[str, dict],
    paths_spec: dict[str, dict],
) -> tuple[ChallengerOutput | None, str, str | None]:
    """Classify a challenger result into one of three visible states.

    Returns ``(accepted, status, note)``:
    - ``"mounted"``  — a distinct, grounded counter-recommendation (``accepted`` set).
      ``note`` flags convergence with synthesis' own second-best, else ``None``.
    - ``"concurred"``— the challenger returned the *recommended* path: the adversarial
      pass could not beat it. That agreement is signal, not failure.
    - ``"degraded"`` — the output was invalid/ungrounded (``accepted`` ``None``); ``note``
      carries the reason. The challenger is spec-degradable (§5.3) so this never raises,
      but the reason is recorded so degradation is visible, not silent (Contract rule 12).

    Parity with synthesis: a mounted counter's cited ids must exist, be non-empty, come
    from the runner-up path's own evidence pools, and a ``buy_then_extend`` runner-up
    needs a BUY m10 API-surface claim.
    """
    if cand.runner_up_path == recommendation_path:
        return None, "concurred", "it could not make a stronger case for any alternative path"
    if cand.runner_up_path not in CANONICAL_PATHS:
        return None, "degraded", f"challenger returned an unknown path: {cand.runner_up_path!r}"
    unknown = sorted({cid for cid in cand.cited_claim_ids if cid not in claims_index})
    if unknown:
        return None, "degraded", f"challenger cited unknown claim ids: {unknown}"
    if not cand.cited_claim_ids:
        return None, "degraded", "challenger case was uncited"
    if not cand.case.strip() or not any(w.strip() for w in cand.wins_when):
        return None, "degraded", "challenger case or wins_when was empty"
    pools = set(paths_spec[cand.runner_up_path]["pools"])
    outside = sorted({cid for cid in cand.cited_claim_ids
                      if claims_index[cid]["track"] not in pools})
    if outside:
        return None, "degraded", (f"challenger cited claims outside the {cand.runner_up_path} "
                                  f"evidence pool {sorted(pools)}: {outside}")
    if (cand.runner_up_path == "buy_then_extend"
            and not _has_buy_api_surface_claim(cand.cited_claim_ids, claims_index)):
        return None, "degraded", "challenger runner-up buy_then_extend lacks a BUY m10 API-surface claim"
    note = None
    if cand.runner_up_path == synth_runner_up_path:
        note = "the engine's own second-best and the challenger independently converged on this path"
    return cand, "mounted", note


def _dossier_bullets(dossier: PathDossier) -> list[CitedBullet]:
    return [*dossier.pros, *dossier.cons, *dossier.key_risks, dossier.reversibility]


def _dossier_claim_ids(dossier: PathDossier) -> list[str]:
    seen: list[str] = []
    for bullet in _dossier_bullets(dossier):
        for cid in bullet.cited_claim_ids:
            if cid not in seen:
                seen.append(cid)
    return seen


def _validate_synthesis(out: SynthesisOutput, claims_index: dict[str, dict]) -> None:
    if out.recommendation_path not in CANONICAL_PATHS:
        raise ContractError(f"recommendation_path not a known path: {out.recommendation_path!r}")
    if not out.thesis.strip():
        raise ContractError("synthesis thesis is empty")
    if out.runner_up_path not in CANONICAL_PATHS:
        raise ContractError(f"runner_up_path not a known path: {out.runner_up_path!r}")
    if out.runner_up_path == out.recommendation_path:
        raise ContractError("runner_up_path must differ from recommendation_path")

    dossier_paths = [d.path for d in out.dossiers]
    unknown_paths = sorted({p for p in dossier_paths if p not in CANONICAL_PATHS})
    if unknown_paths:
        raise ContractError(f"synthesis has dossiers for unknown paths: {unknown_paths}")
    missing = sorted(set(CANONICAL_PATHS) - set(dossier_paths))
    duplicates = sorted({p for p in dossier_paths if dossier_paths.count(p) > 1})
    if missing or duplicates:
        raise ContractError(f"synthesis must include each path exactly once; "
                            f"missing={missing} duplicates={duplicates}")

    for dossier in out.dossiers:
        for bullet in _dossier_bullets(dossier):
            if bullet.text.strip() and not bullet.cited_claim_ids:
                raise ContractError(f"dossier {dossier.path} has an uncited bullet")
            _validate_known_claim_ids(bullet.cited_claim_ids, claims_index,
                                      f"dossier {dossier.path}")
        dossier_ids = _dossier_claim_ids(dossier)
        if not dossier_ids and not _open_questions_cover_path(out.open_questions, dossier.path):
            raise ContractError(
                f"dossier {dossier.path} has no cited claims and no matching open question"
            )

    buy_then_extend = next(d for d in out.dossiers if d.path == "buy_then_extend")
    buy_then_extend_ids = _dossier_claim_ids(buy_then_extend)
    has_api_surface = _has_buy_api_surface_claim(buy_then_extend_ids, claims_index)
    if out.recommendation_path == "buy_then_extend" and not has_api_surface:
        raise ContractError("buy_then_extend recommendation requires a BUY m10 API-surface claim")
    if (buy_then_extend_ids and not has_api_surface
            and not _open_questions_cover_path(out.open_questions, "buy_then_extend")):
        raise ContractError("buy_then_extend dossier lacks a BUY m10 API-surface claim")


def _compact(claim: dict) -> dict:
    src = claim["sources"][0]
    return {
        "text": claim["text"], "status": claim["status"], "flags": claim.get("flags", []),
        "dimension": claim["dimension"], "track": claim["track"],
        "source": {"url": src["url"], "title": src.get("title"),
                   "display_quote": src["display_quote"], "source_date": src.get("source_date")},
    }


def _assemble(synth: SynthesisOutput, challenger: ChallengerOutput | None,
              claims_index: dict[str, dict], challenger_status: str = "disabled",
              challenger_note: str | None = None) -> dict:
    def bullet(b: CitedBullet) -> dict:
        return {"text": b.text, "cited_claim_ids": b.cited_claim_ids}

    dossiers = [{
        "path": d.path,
        "pros": [bullet(b) for b in d.pros],
        "cons": [bullet(b) for b in d.cons],
        "key_risks": [bullet(b) for b in d.key_risks],
        "reversibility": bullet(d.reversibility),
        "cited_claim_ids": _dossier_claim_ids(d),
    } for d in synth.dossiers if d.path in CANONICAL_PATHS]

    if challenger is not None:
        runner_up = {"path": challenger.runner_up_path, "wins_when": challenger.wins_when,
                     "case": challenger.case, "cited_claim_ids": challenger.cited_claim_ids,
                     "from_challenger": True}
    else:
        runner_up = {"path": synth.runner_up_path, "wins_when": synth.runner_up_wins_when,
                     "case": "", "cited_claim_ids": [], "from_challenger": False}

    referenced = {i for d in dossiers for i in d["cited_claim_ids"]} | set(runner_up["cited_claim_ids"])
    return {
        "recommendation": {"path": synth.recommendation_path, "thesis": synth.thesis},
        "decisive_factors": [{"dimension": f.dimension, "why": f.why} for f in synth.decisive_factors],
        "dossiers": dossiers,
        "runner_up": runner_up,
        "open_questions": synth.open_questions,
        "claims_index": {i: _compact(claims_index[i]) for i in referenced},
        "challenger_ran": challenger is not None,
        "challenger_status": challenger_status,
        "challenger_note": challenger_note,
    }

def _render_evidence(ids: list[str], idx: dict[str, dict]) -> list[str]:
    lines = []
    for cid in ids:
        c = idx.get(cid)
        if not c:
            continue
        flags = f" _[{', '.join(c['flags'])}]_" if c["flags"] else ""
        s = c["source"]
        lines.append(f"  - [{cid}] \"{s['display_quote']}\"{flags} — [{s['title'] or s['url']}]({s['url']})")
    return lines


def _render_bullets(label: str, bullets: list[dict]) -> list[str]:
    lines = [f"**{label}:**"]
    if not bullets:
        return [f"**{label}:** —"]
    for bullet in bullets:
        cites = ", ".join(f"[{cid}]" for cid in bullet["cited_claim_ids"])
        suffix = f" {cites}" if cites else ""
        lines.append(f"- {bullet['text']}{suffix}")
    return lines


def render_strategy_md(strategy: dict) -> str:
    rec = strategy["recommendation"]
    idx = strategy["claims_index"]
    out = [f"# Strategy — recommendation: {_PATH_TITLES.get(rec['path'], rec['path'])}", "",
           f"**Recommendation:** {rec['path']}", "", rec["thesis"], "",
           "## Decisive factors"]
    for f in strategy["decisive_factors"]:
        out.append(f"- **{f['dimension']}** — {f['why']}")
    out += ["", "## Path dossiers"]
    for d in strategy["dossiers"]:
        out.append(f"\n### {_PATH_TITLES.get(d['path'], d['path'])}")
        out += _render_bullets("Pros", d["pros"])
        out += _render_bullets("Cons", d["cons"])
        out += _render_bullets("Key risks", d["key_risks"])
        rev_cites = ", ".join(f"[{cid}]" for cid in d["reversibility"]["cited_claim_ids"])
        out.append(f"**Reversibility:** {d['reversibility']['text']} {rev_cites}".rstrip())
        ev = _render_evidence(d["cited_claim_ids"], idx)
        if ev:
            out.append("**Evidence:**")
            out += ev
    ru = strategy["runner_up"]
    status = strategy.get("challenger_status", "disabled")
    note = strategy.get("challenger_note")
    ru_title = _PATH_TITLES.get(ru["path"], ru["path"])
    if status == "mounted":
        out += ["", f"## Challenger's counter-recommendation: {ru_title}"]
        if note:
            out += [f"_{note[0].upper()}{note[1:]}._"]
    else:
        out += ["", f"## Runner-up: {ru_title}"]
        if status == "concurred":
            out += [f"_Challenger concurred: {note}. The runner-up below is the engine's own "
                    "second-best._"]
        elif status == "degraded":
            out += [f"_Challenger could not mount a counter-case ({note}). The runner-up below is "
                    "the engine's own second-best._"]
        else:  # disabled
            out += ["_Challenger disabled; the runner-up below is the engine's own second-best._"]
    if ru["wins_when"]:
        out.append("**Wins when:**")
        out += [f"- {w}" for w in ru["wins_when"]]
    if ru["case"]:
        out += ["", ru["case"]]
    out += _render_evidence(ru["cited_claim_ids"], idx)
    out += ["", "## Open questions"]
    out += [f"- {q}" for q in strategy["open_questions"]] or ["- (none)"]
    return "\n".join(out) + "\n"


def run_synthesis(
    run_dir: str,
    *,
    provider: LLMProvider | None = None,
    model: str | None = None,
    run_challenger: bool = True,
) -> SynthesisResult:
    store = RunStore(run_dir)
    synth_prompt = load_prompt("synthesis")
    chall_prompt = load_prompt("challenger")
    model = model or pro_model()
    engine_version = os.environ.get("ENGINE_VERSION", "0")
    input_paths = [store.artifact_path(f) for f in _INPUTS]
    combined_prompt = synth_prompt + "\n===CHALLENGER===\n" + (chall_prompt if run_challenger else "(disabled)")
    current_hash = stage_input_hash(
        input_paths=input_paths, prompt=combined_prompt, model_id=model, engine_version=engine_version
    )
    json_path = store.artifact_path("strategy.json")
    md_path = store.artifact_path("strategy.md")

    record = store.get_stage("strategy")
    if record and record.status == "done" and record.recorded_hash == current_hash and json_path.exists():
        return SynthesisResult(skipped=True, strategy=json.loads(json_path.read_text(encoding="utf-8")))

    provider = provider or get_provider()
    profile = json.loads(input_paths[0].read_text(encoding="utf-8"))
    build = json.loads(input_paths[1].read_text(encoding="utf-8"))
    buy = json.loads(input_paths[2].read_text(encoding="utf-8"))
    claims_index = _flag_price_conflicts({c["id"]: c for c in build["claims"] + buy["claims"]})

    paths_spec = load_paths()
    paths_block = f"PATH->POOL MAPPING\n{json.dumps(paths_spec)}"
    synth_context = "\n\n".join([synth_prompt, _profile_block(profile), paths_block,
                                 _claims_block(claims_index)])
    synth = provider.complete(synth_context, response_schema=SynthesisOutput, model=model)
    _validate_synthesis(synth, claims_index)

    challenger = None
    challenger_status = "disabled"
    challenger_note = None
    if run_challenger:
        cand = None
        try:
            chall_context = "\n\n".join([
                chall_prompt, _profile_block(profile), _claims_block(claims_index),
                f"SYNTHESIS RECOMMENDATION: {synth.recommendation_path}\nTHESIS: {synth.thesis}",
            ])
            cand = provider.complete(chall_context, response_schema=ChallengerOutput, model=model)
        except Exception as exc:  # noqa: BLE001 — generation failure is degradable (spec §5.3)
            challenger_status = "degraded"
            challenger_note = f"challenger generation failed: {exc}"
        if cand is not None:
            challenger, challenger_status, challenger_note = _evaluate_challenger(
                cand, synth.recommendation_path, synth.runner_up_path, claims_index, paths_spec)

    strategy = _assemble(synth, challenger, claims_index, challenger_status, challenger_note)
    md_path.write_text(render_strategy_md(strategy), encoding="utf-8")
    json_path.write_text(json.dumps(strategy, indent=2, ensure_ascii=False), encoding="utf-8")
    store.set_stage("strategy", status="done", recorded_hash=current_hash,
                    artifacts=["strategy.md", "strategy.json"])
    return SynthesisResult(skipped=False, strategy=strategy)
