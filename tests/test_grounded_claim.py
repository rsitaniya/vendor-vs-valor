"""CHECKPOINT 1: grounded_claim tested in isolation (no network, fake provider)."""

from __future__ import annotations

import pytest

from skills.grounded_claim import (
    PARTIAL_EVIDENCE,
    STALE_COST,
    UNDATED_COST,
    Claim,
    ClaimStatus,
    FilterPolicy,
    GroundingError,
    Locator,
    Source,
    SourceCache,
    SourceDraft,
    VerificationJudgment,
    assert_claim,
    compute_claim_id,
    filter_claims,
    locate,
    verify,
)

CONTENT = (
    "Vendor X is a commercial platform. It exposes a documented REST API for "
    "custom extensions and integrations. Pricing starts at about $2,000 per month."
)
URL = "https://example.com/vendor-x"
COST_URL = "https://example.com/vendor-x-pricing"


class FakeProvider:
    """Returns scripted verdicts; records prompts so we can assert independence."""

    def __init__(self, *verdicts: str):
        self._verdicts = list(verdicts)
        self.prompts: list[str] = []

    def complete(self, prompt, *, response_schema=None, model=None):
        self.prompts.append(prompt)
        return VerificationJudgment(verdict=self._verdicts.pop(0), reason="fake")


@pytest.fixture
def cache(tmp_path):
    c = SourceCache(tmp_path)
    c.add(URL, CONTENT, title="Vendor X", source_date="2025-11-02", accessed_date="2026-06-13")
    return c


def _draft(url=URL, quote="documented REST API"):
    return SourceDraft(url=url, display_quote=quote)


# --- assert_claim: construction + rejection rules ---

def test_assert_creates_unverified_claim_with_computed_locator(cache):
    claim = assert_claim("Vendor X exposes a REST API.", [_draft()], "m10", "BUY", cache)
    assert claim.status == ClaimStatus.UNVERIFIED
    assert claim.sources[0].locator.start == CONTENT.index("documented REST API")
    assert claim.sources[0].source_date == "2025-11-02"
    assert claim.id == compute_claim_id("Vendor X exposes a REST API.", [URL])


def test_assert_rejects_empty_sources(cache):
    with pytest.raises(GroundingError, match="no source"):
        assert_claim("x", [], "m10", "BUY", cache)


def test_assert_rejects_url_not_in_cache(cache):
    with pytest.raises(GroundingError, match="not in cache"):
        assert_claim("x", [_draft(url="https://nope.com")], "m10", "BUY", cache)


def test_assert_rejects_unlocatable_quote(cache):
    with pytest.raises(GroundingError, match="not locatable"):
        assert_claim("x", [_draft(quote="this phrase is absent")], "m10", "BUY", cache)


def test_assert_rejects_unknown_dimension_and_track(cache):
    with pytest.raises(GroundingError, match="dimension"):
        assert_claim("x", [_draft()], "m99", "BUY", cache)
    with pytest.raises(GroundingError, match="track"):
        assert_claim("x", [_draft()], "m10", "SIDEWAYS", cache)


def test_cost_tagged_undated_source_kept_and_flagged_not_rejected(tmp_path):
    # PR-001 F3: vendor/OSS pricing pages are often JS-rendered with no
    # extractable publication date. assert_claim no longer hard-rejects these;
    # they're kept and flagged `undated_cost` at filter time instead.
    c = SourceCache(tmp_path)
    c.add(COST_URL, CONTENT, source_date=None)  # undated
    claim = assert_claim("Pricing ~$2k/mo.", [_draft(url=COST_URL, quote="$2,000 per month")],
                         "m5", "BUY", c)
    assert claim.cost_tagged is True
    assert claim.sources[0].source_date is None

    verified = claim.model_copy(update={"status": ClaimStatus.SUPPORTED})
    assert UNDATED_COST in filter_claims([verified]).kept[0].flags


def test_cost_tagged_inferred_from_dimension(cache):
    cache.add(COST_URL, CONTENT, source_date="2025-11-02")
    claim = assert_claim("Pricing ~$2k/mo.", [_draft(url=COST_URL, quote="$2,000 per month")],
                         "m5", "BUY", cache)
    assert claim.cost_tagged is True


def test_author_cannot_set_status_only_unverified_comes_out(cache):
    # There is no parameter to set status; assert always yields UNVERIFIED.
    claim = assert_claim("Vendor X exposes a REST API.", [_draft()], "m10", "BUY", cache)
    assert claim.status == ClaimStatus.UNVERIFIED


# --- verify: independent judging, status precedence ---

def test_verify_sets_supported(cache):
    claim = assert_claim("Vendor X exposes a REST API.", [_draft()], "m10", "BUY", cache)
    out = verify(claim, cache, provider=FakeProvider("SUPPORTED"))
    assert out.status == ClaimStatus.SUPPORTED


def test_verify_reads_cached_bytes_not_display_quote(cache):
    claim = assert_claim("Vendor X exposes a REST API.", [_draft()], "m10", "BUY", cache)
    fake = FakeProvider("SUPPORTED")
    verify(claim, cache, provider=fake)
    # The verifier is shown cached content around the span, never trusting the quote.
    assert "REST API for custom extensions" in fake.prompts[0]


def test_verify_takes_strongest_source(tmp_path):
    c = SourceCache(tmp_path)
    c.add(URL, CONTENT, source_date="2025-11-02")
    c.add("https://example.com/two", CONTENT, source_date="2025-11-02")
    claim = assert_claim(
        "Vendor X exposes a REST API.",
        [_draft(), SourceDraft(url="https://example.com/two", display_quote="REST API")],
        "m10", "BUY", c,
    )
    out = verify(claim, c, provider=FakeProvider("UNSUPPORTED", "PARTIAL"))
    assert out.status == ClaimStatus.PARTIAL  # strongest of the two


# --- filter: drop / flag policy ---

def _claim(status, *, cost_tagged=False, source_date="2025-11-02", accessed="2026-06-13"):
    return Claim(
        id="abc123", text="t", dimension="m5" if cost_tagged else "m10", track="BUY",
        cost_tagged=cost_tagged, status=status,
        sources=[Source(url=URL, accessed_date=accessed, source_date=source_date,
                        locator=Locator(start=0, end=3), display_quote="Ven")],
    )


def test_filter_drops_unsupported_keeps_supported():
    res = filter_claims([_claim(ClaimStatus.SUPPORTED), _claim(ClaimStatus.UNSUPPORTED)])
    assert len(res.kept) == 1 and len(res.dropped) == 1
    assert res.dropped[0].status == ClaimStatus.UNSUPPORTED


def test_filter_flags_partial():
    res = filter_claims([_claim(ClaimStatus.PARTIAL)])
    assert PARTIAL_EVIDENCE in res.kept[0].flags


def test_filter_flags_stale_cost_over_12_months():
    stale = _claim(ClaimStatus.SUPPORTED, cost_tagged=True,
                   source_date="2024-01-01", accessed="2026-06-13")
    fresh = _claim(ClaimStatus.SUPPORTED, cost_tagged=True,
                   source_date="2026-01-01", accessed="2026-06-13")
    assert STALE_COST in filter_claims([stale]).kept[0].flags
    assert STALE_COST not in filter_claims([fresh]).kept[0].flags


def test_filter_does_not_flag_stale_on_noncost_claim():
    old_noncost = _claim(ClaimStatus.SUPPORTED, cost_tagged=False, source_date="2020-01-01")
    assert STALE_COST not in filter_claims([old_noncost]).kept[0].flags


# --- content-addressing + locator ---

def test_claim_id_is_deterministic_and_order_independent():
    a = compute_claim_id("same text", ["https://a", "https://b"])
    b = compute_claim_id("same text", ["https://b", "https://a"])
    assert a == b
    assert a != compute_claim_id("other text", ["https://a", "https://b"])


def test_locate_exact_whitespace_and_fuzzy():
    assert locate("REST API", CONTENT) is not None
    assert locate("documented   REST\nAPI", CONTENT) is not None  # whitespace tolerant
    assert locate("absent phrase entirely", "totally different text") is None
