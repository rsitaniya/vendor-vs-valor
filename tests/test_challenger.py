"""Challenger stage unit tests."""

from __future__ import annotations

from stages.challenger import ChallengerOutput, evaluate_challenger


PATHS_SPEC = {
    "build": {"pools": ["BUILD"]},
    "buy": {"pools": ["BUY"]},
    "buy_then_extend": {"pools": ["BUY"]},
    "adopt_self_host": {"pools": ["BUILD"]},
}

CLAIMS_INDEX = {
    "b1": {"track": "BUILD", "dimension": "m3"},
    "y1": {"track": "BUY", "dimension": "m5"},
    "yapi": {"track": "BUY", "dimension": "m10"},
}


def test_challenger_mounts_grounded_counter_case():
    result = evaluate_challenger(
        ChallengerOutput(
            runner_up_path="build",
            wins_when=["if differentiation matters"],
            case="Build wins on differentiated workflow control.",
            cited_claim_ids=["b1"],
        ),
        recommendation_path="buy",
        synthesis_runner_up_path="build",
        claims_index=CLAIMS_INDEX,
        paths_spec=PATHS_SPEC,
    )

    assert result.status == "mounted"
    assert result.challenger is not None
    assert "converged" in result.note


def test_challenger_concurrence_is_signal_not_failure():
    result = evaluate_challenger(
        ChallengerOutput(
            runner_up_path="buy",
            wins_when=["n/a"],
            case="No alternative beats buy.",
            cited_claim_ids=["y1"],
        ),
        recommendation_path="buy",
        synthesis_runner_up_path="build",
        claims_index=CLAIMS_INDEX,
        paths_spec=PATHS_SPEC,
    )

    assert result.status == "concurred"
    assert result.challenger is None


def test_challenger_degrades_on_unknown_claim_ids():
    result = evaluate_challenger(
        ChallengerOutput(
            runner_up_path="build",
            wins_when=["if X"],
            case="Build wins.",
            cited_claim_ids=["ghost"],
        ),
        recommendation_path="buy",
        synthesis_runner_up_path="build",
        claims_index=CLAIMS_INDEX,
        paths_spec=PATHS_SPEC,
    )

    assert result.status == "degraded"
    assert result.challenger is None
    assert "unknown claim ids" in result.note
