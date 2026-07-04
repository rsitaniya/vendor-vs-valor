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
    _discover_entities_via_search,
    merge_verify_reports,
    run_research,
)

URL_A = "https://ex.com/a"
URL_B = "https://ex.com/b"
# Padded past MIN_CONTENT_CHARS (400) — cache hits are now length-checked too,
# so a fixture this short would otherwise be (correctly) treated as thin content.
CONTENT_A = (
    "An open source option exists and is widely adopted for this capability. "
    "It has an active maintainer community, frequent releases, and is used in "
    "production by several well-known companies. Documentation covers setup, "
    "configuration, and common integration patterns for teams evaluating it "
    "as a self-hosted alternative to commercial offerings in this space. The "
    "project accepts external contributions, publishes a public roadmap, and "
    "maintains a changelog going back several major versions, with a security "
    "disclosure policy and a healthy issue-response cadence from maintainers."
)
CONTENT_B = (
    "Commercial pricing starts at $500 per month for the starter tier. "
    "Higher tiers add SSO, dedicated support, and higher usage limits. "
    "The vendor publishes a public pricing page and offers annual billing "
    "with a discount. Enterprise customers can request custom contracts "
    "covering data residency, uptime SLAs, and volume-based pricing. The "
    "vendor also lists supported integrations, a public status page, and "
    "a documented API rate limit for each tier, along with an SLA credit "
    "policy for extended downtime beyond the published availability target."
)


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


class _AlwaysFailingCache:
    """Stands in for SourceCache when every fetch must fail, without touching
    the network."""

    def fetch(self, url):
        raise RuntimeError("network unavailable")

    def get_content(self, url):
        raise AssertionError("should not be reached — nothing was fetched")


def test_entity_discovery_fetch_failure_surfaces_as_a_gap(tmp_path):
    profile = {"need": {"capability": "widget engine", "business_context": "x", "problem": "y"}}
    store = RunStore(tmp_path)
    discovery, gaps = _discover_entities_via_search(
        profile, "BUILD", fake_searcher([URL_A, URL_B]), _AlwaysFailingCache(),
        FakeProvider([]), "m1", store=store,
    )
    assert discovery.selected == []
    assert any("no fetchable sources" in g for g in gaps)


def test_entity_discovery_curation_failure_surfaces_as_a_gap(tmp_path):
    profile = {"need": {"capability": "widget engine", "business_context": "x", "problem": "y"}}
    store = RunStore(tmp_path)
    cache = SourceCache(tmp_path)
    cache.add(URL_A, CONTENT_A, source_date="2025-10-01")
    # FakeProvider raises for any schema it isn't scripted for — both the
    # discovery-query call (harmless: falls back to deterministic queries)
    # and the curation call, which is the failure this test targets.
    discovery, gaps = _discover_entities_via_search(
        profile, "BUILD", fake_searcher([URL_A]), cache, FakeProvider([]), "m1", store=store,
    )
    assert discovery.selected == []
    assert any("entity discovery curation failed" in g for g in gaps)


class RaisingAuthorProvider(FakeProvider):
    """Simulates a provider failure (e.g. exhausted retries) during authoring."""

    def complete(self, prompt, *, response_schema=None, model=None):
        if response_schema is ResearchClaims:
            raise RuntimeError("simulated API failure")
        return super().complete(prompt, response_schema=response_schema, model=model)


def test_authoring_failure_is_a_gap_not_a_crash(run_dir):
    prov = RaisingAuthorProvider([_draft(URL_A, "open source option")])
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert res.kept == []
    assert any("claim authoring failed" in g for g in res.coverage_gaps)


class RaisingVerifyProvider(FakeProvider):
    """Simulates a provider failure (e.g. exhausted retries) during verify."""

    def complete(self, prompt, *, response_schema=None, model=None):
        if response_schema is VerificationJudgment:
            raise RuntimeError("simulated API failure")
        return super().complete(prompt, response_schema=response_schema, model=model)


def test_verify_failure_is_a_gap_not_a_crash(run_dir):
    prov = RaisingVerifyProvider([_draft(URL_A, "open source option")])
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert res.kept == []
    assert any("verification failed" in g for g in res.coverage_gaps)


def test_thin_cached_content_is_not_admitted_on_cache_hit(run_dir):
    # A URL cached with thin content (e.g. by entity discovery sharing this
    # same cache) must not be treated as valid evidence just because it's
    # already present — length is re-checked on cache hits, not just fetches.
    SourceCache(run_dir).add(URL_A, "too short to count as real content", source_date="2025-10-01")
    prov = FakeProvider([_draft(URL_A, "too short to count as real content")])
    res = run_research("BUILD", run_dir, provider=prov, searcher=fake_searcher([URL_A]))
    assert res.kept == []
    assert any("thin content" in g for g in res.coverage_gaps)


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
