"""Adversarial challenger pass for Stage 3.

The challenger is intentionally separate from synthesis: it receives the
synthesis recommendation plus the same grounded evidence index, then tries to
mount a cited counter-recommendation. Invalid challenger output degrades visibly
instead of failing the strategy stage.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from llm.provider import LLMProvider
from rubric import CANONICAL_PATHS


class ChallengerOutput(BaseModel):
    runner_up_path: str
    wins_when: list[str]
    case: str
    cited_claim_ids: list[str]


@dataclass
class ChallengerResult:
    challenger: ChallengerOutput | None
    status: str
    note: str | None = None


def has_buy_api_surface_claim(ids: list[str], claims_index: dict[str, dict]) -> bool:
    return any(
        claims_index[cid]["track"] == "BUY" and claims_index[cid]["dimension"] == "m10"
        for cid in ids
        if cid in claims_index
    )


def evaluate_challenger(
    candidate: ChallengerOutput,
    *,
    recommendation_path: str,
    synthesis_runner_up_path: str,
    claims_index: dict[str, dict],
    paths_spec: dict[str, dict],
) -> ChallengerResult:
    """Classify challenger output into mounted, concurred, or degraded."""
    if candidate.runner_up_path == recommendation_path:
        return ChallengerResult(
            None,
            "concurred",
            "it could not make a stronger case for any alternative path",
        )
    if candidate.runner_up_path not in CANONICAL_PATHS:
        return ChallengerResult(
            None,
            "degraded",
            f"challenger returned an unknown path: {candidate.runner_up_path!r}",
        )

    unknown = sorted({cid for cid in candidate.cited_claim_ids if cid not in claims_index})
    if unknown:
        return ChallengerResult(
            None,
            "degraded",
            f"challenger cited unknown claim ids: {unknown}",
        )
    if not candidate.cited_claim_ids:
        return ChallengerResult(None, "degraded", "challenger case was uncited")
    if not candidate.case.strip() or not any(w.strip() for w in candidate.wins_when):
        return ChallengerResult(None, "degraded", "challenger case or wins_when was empty")

    pools = set(paths_spec[candidate.runner_up_path]["pools"])
    outside = sorted({
        cid
        for cid in candidate.cited_claim_ids
        if claims_index[cid]["track"] not in pools
    })
    if outside:
        return ChallengerResult(
            None,
            "degraded",
            f"challenger cited claims outside the {candidate.runner_up_path} "
            f"evidence pool {sorted(pools)}: {outside}",
        )
    if (
        candidate.runner_up_path == "buy_then_extend"
        and not has_buy_api_surface_claim(candidate.cited_claim_ids, claims_index)
    ):
        return ChallengerResult(
            None,
            "degraded",
            "challenger runner-up buy_then_extend lacks a BUY m10 API-surface claim",
        )

    note = None
    if candidate.runner_up_path == synthesis_runner_up_path:
        note = (
            "the engine's own second-best and the challenger independently "
            "converged on this path"
        )
    return ChallengerResult(candidate, "mounted", note)


def run_challenger(
    *,
    enabled: bool,
    provider: LLMProvider,
    prompt: str,
    profile_context: str,
    evidence_context: str,
    recommendation_path: str,
    thesis: str,
    synthesis_runner_up_path: str,
    claims_index: dict[str, dict],
    paths_spec: dict[str, dict],
    model: str,
) -> ChallengerResult:
    if not enabled:
        return ChallengerResult(None, "disabled")

    try:
        context = "\n\n".join([
            prompt,
            profile_context,
            evidence_context,
            f"SYNTHESIS RECOMMENDATION: {recommendation_path}\nTHESIS: {thesis}",
        ])
        candidate = provider.complete(
            context,
            response_schema=ChallengerOutput,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001 - generation failure is degradable.
        return ChallengerResult(None, "degraded", f"challenger generation failed: {exc}")

    return evaluate_challenger(
        candidate,
        recommendation_path=recommendation_path,
        synthesis_runner_up_path=synthesis_runner_up_path,
        claims_index=claims_index,
        paths_spec=paths_spec,
    )
