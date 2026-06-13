"""Slice 6: synthesis (four-path) + challenger -> strategy.{md,json}."""

from __future__ import annotations

import json

import pytest

from engine.runstore import RunStore
from skills.grounded_claim import Claim, ClaimStatus, Locator, Source
from stages.synthesis import (
    ChallengerOutput,
    DecisiveFactor,
    PathDossier,
    SynthesisOutput,
    run_synthesis,
)


def _claim(cid, track, dim, text):
    return Claim(
        id=cid, text=text, dimension=dim, track=track, status=ClaimStatus.SUPPORTED,
        sources=[Source(url=f"https://ex.com/{cid}", title="T", accessed_date="2026-06-13",
                        source_date="2025-10-01", locator=Locator(start=0, end=4),
                        display_quote="quote")],
    )


def _dossier(path, ids):
    return PathDossier(path=path, pros=["p"], cons=["c"], key_risks=["r"],
                       reversibility="reversible", cited_claim_ids=ids)


def _synth_out(rec="buy_then_extend", dossier_ids=("b1",)):
    return SynthesisOutput(
        recommendation_path=rec, thesis="Buy the base, build the edge.",
        dossiers=[_dossier("build", ["b1"]), _dossier("buy", ["y1"]),
                  _dossier("buy_then_extend", list(dossier_ids)), _dossier("adopt_self_host", [])],
        decisive_factors=[DecisiveFactor(dimension="m8", why="reversibility")],
        open_questions=["pricing at scale unknown"],
        runner_up_path="build", runner_up_wins_when=["if differentiation matters"],
    )


@pytest.fixture
def run_dir(tmp_path):
    store = RunStore(tmp_path)
    store.write_text("profile.json", json.dumps({
        "need": {"capability": "widget", "business_context": "x", "problem": "y"},
        "constraints": {}, "customization_need": "low", "soft_steer": "cost matters"}))
    store.write_text("build-research.json", json.dumps({
        "track": "BUILD", "claims": [_claim("b1", "BUILD", "m3", "build is costly").model_dump()]}))
    store.write_text("buy-research.json", json.dumps({
        "track": "BUY", "claims": [_claim("y1", "BUY", "m5", "vendor priced at $x").model_dump()]}))
    return tmp_path


class SynthProvider:
    """Serves the synthesis call then the challenger call by schema."""

    def __init__(self, synth, challenger=None):
        self.synth = synth
        self.challenger = challenger
        self.calls = 0

    def complete(self, prompt, *, response_schema=None, model=None):
        self.calls += 1
        if response_schema is SynthesisOutput:
            return self.synth
        if response_schema is ChallengerOutput:
            if self.challenger is None:
                raise RuntimeError("challenger failed")
            return self.challenger
        raise AssertionError(response_schema)


def test_synthesis_produces_strategy_with_recommendation_and_dossiers(run_dir):
    chall = ChallengerOutput(runner_up_path="adopt_self_host", wins_when=["if data must stay in"],
                             case="Self-host wins under residency.", cited_claim_ids=["b1"])
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), chall), model="m")
    assert not res.skipped
    strat = res.strategy
    assert strat["recommendation"]["path"] == "buy_then_extend"
    assert len(strat["dossiers"]) == 4
    assert strat["runner_up"]["path"] == "adopt_self_host" and strat["runner_up"]["from_challenger"]
    md = (run_dir / "strategy.md").read_text()
    assert "recommendation: Buy-then-extend" in md
    assert "**Recommendation:** buy_then_extend" in md
    assert "Runner-up" in md and "Open questions" in md


def test_challenger_degrades_to_synthesis_runner_up(run_dir):
    # challenger raises -> runner-up falls back to synthesis' own second-best
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), challenger=None), model="m")
    assert res.strategy["runner_up"]["path"] == "build"
    assert res.strategy["challenger_ran"] is False


def test_challenger_disabled_is_single_pass(run_dir):
    prov = SynthProvider(_synth_out())
    res = run_synthesis(run_dir, provider=prov, model="m", run_challenger=False)
    assert prov.calls == 1  # no challenger call
    assert res.strategy["challenger_ran"] is False


def test_unknown_cited_ids_are_filtered_out(run_dir):
    synth = _synth_out(dossier_ids=("b1", "ghost"))
    res = run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")
    bte = next(d for d in res.strategy["dossiers"] if d["path"] == "buy_then_extend")
    assert "ghost" not in bte["cited_claim_ids"] and "b1" in bte["cited_claim_ids"]


def test_claims_index_only_contains_referenced_claims(run_dir):
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), None), model="m")
    # b1 and y1 are referenced by dossiers; both should resolve
    assert set(res.strategy["claims_index"]) <= {"b1", "y1"}
    assert "b1" in res.strategy["claims_index"]


def test_editing_soft_steer_reruns_synthesis(run_dir):
    prov = SynthProvider(_synth_out(), None)
    run_synthesis(run_dir, provider=prov, model="m")
    first = prov.calls
    profile = json.loads((run_dir / "profile.json").read_text())
    profile["soft_steer"] = "now speed matters most"
    (run_dir / "profile.json").write_text(json.dumps(profile))
    res = run_synthesis(run_dir, provider=prov, model="m")
    assert not res.skipped and prov.calls > first  # soft_steer is in synthesis' hash
