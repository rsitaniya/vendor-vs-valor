"""Stage 3 — synthesis (four-path lenses) + challenger -> strategy.{md,json}.

Two LLM steps over the same two evidence pools, then deterministic assembly:
(a) synthesize: a dossier per path + recommendation + decisive factors + open
    questions + the engine's own runner-up.
(b) challenger (degradable): the strongest *cited* case for a different path,
    which becomes the runner-up if it runs.
(c) assemble (code): strategy.md (the deliverable, md is truth) + strategy.json
    (section manifest + referenced claim ids + a compact claims index the report
    renders from). Idempotent via the input-hash guard.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from pydantic import BaseModel

from agents import load_prompt
from engine.hashing import stage_input_hash
from engine.runstore import RunStore
from llm import get_provider, pro_model
from llm.provider import LLMProvider
from rubric import CANONICAL_PATHS, load_paths
from skills.schema_stage import ContractError

_INPUTS = ("profile.json", "build-research.json", "buy-research.json")


# --- LLM output shapes (no defaults -> Gemini struct-output safe) ---

class PathDossier(BaseModel):
    path: str
    pros: list[str]
    cons: list[str]
    key_risks: list[str]
    reversibility: str
    cited_claim_ids: list[str]


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


def _profile_block(profile: dict) -> str:
    need = profile["need"]
    return (f"PROFILE\ncapability: {need['capability']}\ncontext: {need['business_context']}\n"
            f"problem: {need['problem']}\nintent: {profile.get('intent', {})}\n"
            f"constraints: {profile.get('constraints', {})}\n"
            f"customization_need: {profile.get('customization_need')}\n"
            f"soft_steer: {profile.get('soft_steer', '')}")


# --- validation + assembly ---

def _validate_synthesis(out: SynthesisOutput) -> None:
    if out.recommendation_path not in CANONICAL_PATHS:
        raise ContractError(f"recommendation_path not a known path: {out.recommendation_path!r}")
    if not out.thesis.strip():
        raise ContractError("synthesis thesis is empty")


def _compact(claim: dict) -> dict:
    src = claim["sources"][0]
    return {
        "text": claim["text"], "status": claim["status"], "flags": claim.get("flags", []),
        "dimension": claim["dimension"], "track": claim["track"],
        "source": {"url": src["url"], "title": src.get("title"),
                   "display_quote": src["display_quote"], "source_date": src.get("source_date")},
    }


def _assemble(synth: SynthesisOutput, challenger: ChallengerOutput | None,
              claims_index: dict[str, dict]) -> dict:
    def known(ids: list[str]) -> list[str]:
        return [i for i in ids if i in claims_index]

    dossiers = [{
        "path": d.path, "pros": d.pros, "cons": d.cons, "key_risks": d.key_risks,
        "reversibility": d.reversibility, "cited_claim_ids": known(d.cited_claim_ids),
    } for d in synth.dossiers if d.path in CANONICAL_PATHS]

    if challenger is not None:
        runner_up = {"path": challenger.runner_up_path, "wins_when": challenger.wins_when,
                     "case": challenger.case, "cited_claim_ids": known(challenger.cited_claim_ids),
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
    }


_PATH_TITLES = {"build": "Build", "buy": "Buy", "buy_then_extend": "Buy-then-extend",
                "adopt_self_host": "Adopt & self-host"}


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
        out.append("**Pros:** " + ("; ".join(d["pros"]) or "—"))
        out.append("**Cons:** " + ("; ".join(d["cons"]) or "—"))
        out.append("**Key risks:** " + ("; ".join(d["key_risks"]) or "—"))
        out.append(f"**Reversibility:** {d['reversibility']}")
        ev = _render_evidence(d["cited_claim_ids"], idx)
        if ev:
            out.append("**Evidence:**")
            out += ev
    ru = strategy["runner_up"]
    out += ["", f"## Runner-up: {_PATH_TITLES.get(ru['path'], ru['path'])}"]
    if ru["wins_when"]:
        out.append("**Wins when:**")
        out += [f"- {w}" for w in ru["wins_when"]]
    if ru["case"]:
        out += ["", ru["case"]]
    out += _render_evidence(ru["cited_claim_ids"], idx)
    out += ["", "## Open questions"]
    out += [f"- {q}" for q in strategy["open_questions"]] or ["- (none)"]
    if not strategy["challenger_ran"]:
        out += ["", "_Challenger degraded to single-pass synthesis; runner-up is the engine's own._"]
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
    claims_index = {c["id"]: c for c in build["claims"] + buy["claims"]}

    paths_block = f"PATH->POOL MAPPING\n{json.dumps(load_paths())}"
    synth_context = "\n\n".join([synth_prompt, _profile_block(profile), paths_block,
                                 _claims_block(claims_index)])
    synth = provider.complete(synth_context, response_schema=SynthesisOutput, model=model)
    _validate_synthesis(synth)

    challenger = None
    if run_challenger:
        try:
            chall_context = "\n\n".join([
                chall_prompt, _claims_block(claims_index),
                f"SYNTHESIS RECOMMENDATION: {synth.recommendation_path}\nTHESIS: {synth.thesis}",
            ])
            cand = provider.complete(chall_context, response_schema=ChallengerOutput, model=model)
            # a runner-up identical to the recommendation is no challenge; degrade
            if cand.runner_up_path in CANONICAL_PATHS and cand.runner_up_path != synth.recommendation_path:
                challenger = cand
        except Exception:  # noqa: BLE001 — challenger is degradable (spec §5.3)
            challenger = None

    strategy = _assemble(synth, challenger, claims_index)
    md_path.write_text(render_strategy_md(strategy), encoding="utf-8")
    json_path.write_text(json.dumps(strategy, indent=2, ensure_ascii=False), encoding="utf-8")
    store.set_stage("strategy", status="done", recorded_hash=current_hash,
                    artifacts=["strategy.md", "strategy.json"])
    return SynthesisResult(skipped=False, strategy=strategy)
