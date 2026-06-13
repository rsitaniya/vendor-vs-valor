"""Slice 5: research wires grounded_claim end-to-end (mocked search + provider)."""

from __future__ import annotations

import json

import pytest

from engine.runstore import RunStore
from skills.grounded_claim import ClaimDraft, SourceCache, SourceDraft, VerificationJudgment
from stages.research import (
    PlannedQuery,
    QueryPlan,
    ResearchClaims,
    merge_verify_reports,
    run_research,
)

URL_A = "https://ex.com/a"
URL_B = "https://ex.com/b"
CONTENT_A = "An open source option exists and is widely adopted for this capability."
CONTENT_B = "Commercial pricing starts at $500 per month for the starter tier."


@pytest.fixture
def run_dir(tmp_path):
    # seed a minimal profile.json
    RunStore(tmp_path).write_text("profile.json", json.dumps({
        "need": {"capability": "widget engine", "business_context": "x", "problem": "y"},
        "soft_steer": "cost matters", "customization_need": "low",
    }))
    # seed the cache so fetch is a no-op (no network)
    cache = SourceCache(tmp_path)
    cache.add(URL_A, CONTENT_A, source_date="2025-10-01")
    cache.add(URL_B, CONTENT_B, source_date="2025-10-01")
    return tmp_path


def fake_searcher(urls):
    def search(query, max_results):
        return urls
    return search


class FakeProvider:
    """Serves the planner call, the authoring call, and the per-claim verify calls."""

    def __init__(self, drafts, verdict="SUPPORTED", priority=("m1",)):
        self.drafts = drafts
        self.verdict = verdict
        self.priority = priority
        self.author_calls = 0
        self.plan_calls = 0

    def complete(self, prompt, *, response_schema=None, model=None):
        if response_schema is QueryPlan:
            self.plan_calls += 1
            return QueryPlan(
                priority_dimensions=[{"id": d, "why": "fake"} for d in self.priority],
                queries=[PlannedQuery(query="q", dimension="m1")],
            )
        if response_schema is ResearchClaims:
            self.author_calls += 1
            return ResearchClaims(claims=self.drafts)
        if response_schema is VerificationJudgment:
            return VerificationJudgment(verdict=self.verdict, reason="fake")
        raise AssertionError(f"unexpected schema {response_schema}")


def _draft(url, quote, dim="m1"):
    return ClaimDraft(text=f"claim about {url}", dimension=dim,
                      sources=[SourceDraft(url=url, display_quote=quote)])


def test_research_produces_verified_cited_claims(run_dir):
    prov = FakeProvider([_draft(URL_A, "open source option"),
                         _draft(URL_B, "$500 per month", dim="m5")])
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A, URL_B]))
    assert not res.skipped
    assert len(res.kept) == 2
    data = json.loads((run_dir / "build-research.json").read_text())
    assert data["kept_count"] == 2
    # every kept claim resolves to a cached source with a computed locator
    for claim in data["claims"]:
        assert claim["sources"][0]["url"] in (URL_A, URL_B)
        assert claim["sources"][0]["locator"]["end"] > 0
    assert (run_dir / "build-research.md").exists()
    assert (run_dir / "build-verify-report.json").exists()


def test_unsupported_claims_are_dropped(run_dir):
    prov = FakeProvider([_draft(URL_A, "open source option")], verdict="UNSUPPORTED")
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert res.kept == [] and len(res.dropped) == 1


def test_ungrounded_drafts_are_rejected_by_assert(run_dir):
    # quote not present in the cached content -> assert_claim rejects it
    prov = FakeProvider([_draft(URL_A, "this phrase is not in the source")])
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert res.kept == []
    assert res.assert_rejected and "not locatable" in res.assert_rejected[0]["reason"]


def test_no_fetchable_sources_is_a_gap_not_a_crash(run_dir):
    prov = FakeProvider([])
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([]))
    assert res.kept == []
    assert any("no fetchable sources" in g for g in res.coverage_gaps)


def test_research_is_idempotent_and_skips_reauthoring(run_dir):
    prov = FakeProvider([_draft(URL_A, "open source option")])
    run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert prov.author_calls == 1
    second = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert second.skipped and prov.author_calls == 1  # no re-authoring


def test_editing_soft_steer_does_not_rerun_research(run_dir):
    # Gate-3 behavior (spec §4): soft_steer is synthesis-only; research skips.
    prov = FakeProvider([_draft(URL_A, "open source option")])
    run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    profile = json.loads((run_dir / "profile.json").read_text())
    profile["soft_steer"] = "completely different steer"
    (run_dir / "profile.json").write_text(json.dumps(profile))
    second = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert second.skipped and prov.author_calls == 1


def test_planner_runs_once_and_is_skipped_on_idempotent_rerun(run_dir):
    prov = FakeProvider([_draft(URL_A, "open source option")])
    run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert prov.plan_calls == 1
    second = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert second.skipped and prov.plan_calls == 1  # no re-planning on cache hit


def test_per_dimension_coverage_flags_empty_priority_dimension(run_dir):
    # claim lands on m1; planner marked m3 (a BUILD dim) a priority but no claim
    # covers it -> m3 surfaces as a gap.
    prov = FakeProvider([_draft(URL_A, "open source option", dim="m1")], priority=("m1", "m3"))
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    covered = {r["id"]: r for r in res.coverage}
    assert covered["m1"]["covered"] and covered["m1"]["claim_count"] == 1
    assert any("priority dimension m3" in g for g in res.coverage_gaps)
    data = json.loads((run_dir / "build-research.json").read_text())
    assert data["priority_dimensions"] and data["coverage"]


def test_merge_verify_reports_combines_per_track_outputs(run_dir):
    build_provider = FakeProvider([_draft(URL_A, "open source option")])
    buy_provider = FakeProvider([_draft(URL_B, "$500 per month", dim="m5")])
    run_research("BUILD", run_dir, provider=build_provider, searcher=fake_searcher([URL_A]))
    run_research("BUY", run_dir, provider=buy_provider, searcher=fake_searcher([URL_B]))
    report = merge_verify_reports(run_dir)
    assert set(report) == {"BUILD", "BUY"}
    assert (run_dir / "verify-report.json").exists()
