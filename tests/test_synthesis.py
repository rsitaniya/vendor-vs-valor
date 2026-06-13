"""Slice 6: synthesis (four-path) + challenger -> strategy.{md,json}."""

from __future__ import annotations

import json

import pytest

from engine.runstore import RunStore
from skills.grounded_claim import Claim, ClaimStatus, Locator, Source
from skills.schema_stage import ContractError
from stages.synthesis import (
    ChallengerOutput,
    CitedBullet,
    DecisiveFactor,
    PathDossier,
    SynthesisOutput,
    run_synthesis,
)


def _claim(cid, track, dim, text, *, url=None, cost_tagged=False, quote="quote"):
    return Claim(
        id=cid, text=text, dimension=dim, track=track, status=ClaimStatus.SUPPORTED,
        cost_tagged=cost_tagged,
        sources=[Source(url=url or f"https://ex.com/{cid}", title="T", accessed_date="2026-06-13",
                        source_date="2025-10-01", locator=Locator(start=0, end=4),
                        display_quote=quote)],
    )


def _dossier(path, ids):
    cited = [CitedBullet(text="p", cited_claim_ids=list(ids))]
    return PathDossier(path=path, pros=cited,
                       cons=[CitedBullet(text="c", cited_claim_ids=list(ids))],
                       key_risks=[CitedBullet(text="r", cited_claim_ids=list(ids))],
                       reversibility=CitedBullet(text="reversible", cited_claim_ids=list(ids)))


def _synth_out(rec="buy_then_extend", dossier_ids=("yapi",)):
    return SynthesisOutput(
        recommendation_path=rec, thesis="Buy the base, build the edge.",
        dossiers=[_dossier("build", ["b1"]), _dossier("buy", ["y1"]),
                  _dossier("buy_then_extend", list(dossier_ids)), _dossier("adopt_self_host", ["b1"])],
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
        "track": "BUY", "claims": [
            _claim("y1", "BUY", "m5", "vendor priced at $x").model_dump(),
            _claim("yapi", "BUY", "m10", "vendor exposes an API").model_dump(),
        ]}))
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
    assert strat["challenger_status"] == "mounted"
    md = (run_dir / "strategy.md").read_text()
    assert "recommendation: Buy-then-extend" in md
    assert "**Recommendation:** buy_then_extend" in md
    assert "Challenger's counter-recommendation: Adopt & self-host" in md
    assert "Open questions" in md


def test_challenger_degrades_to_synthesis_runner_up(run_dir):
    # challenger raises -> runner-up falls back to synthesis' own second-best
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), challenger=None), model="m")
    assert res.strategy["runner_up"]["path"] == "build"
    assert res.strategy["challenger_ran"] is False
    assert res.strategy["challenger_status"] == "degraded"
    assert "generation failed" in res.strategy["challenger_note"]


def test_challenger_concurrence_is_surfaced(run_dir):
    # returning the recommended path is concurrence, not failure -> visible signal
    concur = ChallengerOutput(runner_up_path="buy_then_extend", wins_when=["n/a"],
                              case="No alternative beats it.", cited_claim_ids=["yapi"])
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), concur), model="m")
    assert res.strategy["challenger_status"] == "concurred"
    assert res.strategy["runner_up"]["path"] == "build"  # falls back to synthesis' own
    assert "Challenger concurred" in (run_dir / "strategy.md").read_text()


def test_challenger_unknown_ids_degrade_visibly_not_silently(run_dir):
    # a hallucinated id must NOT raise (challenger is degradable) but MUST be recorded
    bad = ChallengerOutput(runner_up_path="build", wins_when=["if X"], case="c",
                           cited_claim_ids=["ghost"])
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), bad), model="m")
    assert res.strategy["challenger_status"] == "degraded"
    assert "unknown claim ids" in res.strategy["challenger_note"]
    assert res.strategy["runner_up"]["from_challenger"] is False


def test_challenger_out_of_pool_citation_degrades(run_dir):
    # a build counter resting only on BUY evidence fails pool parity
    bad = ChallengerOutput(runner_up_path="build", wins_when=["if X"], case="c",
                           cited_claim_ids=["y1"])
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), bad), model="m")
    assert res.strategy["challenger_status"] == "degraded"
    assert "outside the build" in res.strategy["challenger_note"]


def test_challenger_buy_then_extend_counter_needs_api_claim(run_dir):
    # recommend build so buy_then_extend is a real (different) counter, then starve the gate
    synth = _synth_out(rec="build")
    synth.runner_up_path = "buy"  # synthesis' own runner-up must differ from recommendation
    bad = ChallengerOutput(runner_up_path="buy_then_extend", wins_when=["if X"], case="c",
                           cited_claim_ids=["b1"])
    res = run_synthesis(run_dir, provider=SynthProvider(synth, bad), model="m")
    assert res.strategy["challenger_status"] == "degraded"
    assert "API-surface" in res.strategy["challenger_note"]


def test_challenger_convergence_with_synthesis_runner_up_is_noted(run_dir):
    # challenger independently lands on synthesis' own second-best ("build")
    same = ChallengerOutput(runner_up_path="build", wins_when=["if differentiation matters"],
                            case="Build wins on differentiation.", cited_claim_ids=["b1"])
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), same), model="m")
    assert res.strategy["challenger_status"] == "mounted"
    assert "converged" in res.strategy["challenger_note"]
    assert "converged" in (run_dir / "strategy.md").read_text()


def test_challenger_disabled_is_single_pass(run_dir):
    prov = SynthProvider(_synth_out())
    res = run_synthesis(run_dir, provider=prov, model="m", run_challenger=False)
    assert prov.calls == 1  # no challenger call
    assert res.strategy["challenger_ran"] is False


def test_unknown_cited_ids_fail_contract(run_dir):
    synth = _synth_out(dossier_ids=("b1", "ghost"))
    with pytest.raises(ContractError, match="unknown claim ids"):
        run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")


def test_missing_path_dossier_fails_contract(run_dir):
    synth = _synth_out()
    synth.dossiers = [d for d in synth.dossiers if d.path != "adopt_self_host"]
    with pytest.raises(ContractError, match="each path exactly once"):
        run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")


def test_runner_up_must_differ_from_recommendation(run_dir):
    synth = _synth_out(rec="build")
    synth.runner_up_path = "build"
    with pytest.raises(ContractError, match="runner_up_path must differ"):
        run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")


def test_empty_dossier_needs_matching_open_question(run_dir):
    synth = _synth_out()
    for dossier in synth.dossiers:
        if dossier.path == "adopt_self_host":
            dossier.pros = []
            dossier.cons = []
            dossier.key_risks = []
            dossier.reversibility = CitedBullet(text="", cited_claim_ids=[])
    with pytest.raises(ContractError, match="no cited claims"):
        run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")
    synth.open_questions.append("adopt_self_host evidence is thin")
    res = run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")
    assert res.strategy["dossiers"][-1]["path"] == "adopt_self_host"


def test_factual_bullet_must_have_citation(run_dir):
    synth = _synth_out()
    synth.dossiers[0].pros[0] = CitedBullet(text="uncited factual claim", cited_claim_ids=[])
    with pytest.raises(ContractError, match="uncited bullet"):
        run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")


def test_buy_then_extend_recommendation_requires_buy_api_claim(run_dir):
    synth = _synth_out(dossier_ids=("b1",))
    with pytest.raises(ContractError, match="BUY m10 API-surface"):
        run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")


def test_claims_index_only_contains_referenced_claims(run_dir):
    res = run_synthesis(run_dir, provider=SynthProvider(_synth_out(), None), model="m")
    # b1 and y1 are referenced by dossiers; both should resolve
    assert set(res.strategy["claims_index"]) <= {"b1", "y1", "yapi"}
    assert "b1" in res.strategy["claims_index"]


def test_conflicting_cost_claims_are_flagged(run_dir):
    buy = {
        "track": "BUY",
        "claims": [
            _claim("y1", "BUY", "m5", "Vendor pricing is $500 per month.",
                   url="https://vendor.example/pricing-a", cost_tagged=True,
                   quote="$500 per month").model_dump(),
            _claim("y2", "BUY", "m5", "Vendor pricing is $900 per month.",
                   url="https://vendor.example/pricing-b", cost_tagged=True,
                   quote="$900 per month").model_dump(),
            _claim("yapi", "BUY", "m10", "vendor exposes an API").model_dump(),
        ],
    }
    (run_dir / "buy-research.json").write_text(json.dumps(buy), encoding="utf-8")
    synth = _synth_out()
    synth.dossiers[1].pros[0] = CitedBullet(text="pricing sources disagree",
                                            cited_claim_ids=["y1", "y2"])
    res = run_synthesis(run_dir, provider=SynthProvider(synth, None), model="m")
    assert "price_conflict" in res.strategy["claims_index"]["y1"]["flags"]
    assert "price_conflict" in res.strategy["claims_index"]["y2"]["flags"]
    assert res.strategy["dossiers"][1]["pros"][0]["cited_claim_ids"] == ["y1", "y2"]
    assert "price_conflict" in (run_dir / "strategy.md").read_text()


def test_editing_soft_steer_reruns_synthesis(run_dir):
    prov = SynthProvider(_synth_out(), None)
    run_synthesis(run_dir, provider=prov, model="m")
    first = prov.calls
    profile = json.loads((run_dir / "profile.json").read_text())
    profile["soft_steer"] = "now speed matters most"
    (run_dir / "profile.json").write_text(json.dumps(profile))
    res = run_synthesis(run_dir, provider=prov, model="m")
    assert not res.skipped and prov.calls > first  # soft_steer is in synthesis' hash
