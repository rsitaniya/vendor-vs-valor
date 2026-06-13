"""grounded_claim — the trust layer (spec §3.1).

Public API: the Claim object, the author-facing draft shapes, the three
operations (assert/verify/filter), and the per-run source cache.
"""

from .cache import CacheError, SourceCache
from .claim import (
    FilterPolicy,
    FilterResult,
    GroundingError,
    assert_claim,
    filter_claims,
    verify,
)
from .locate import locate
from .models import (
    PARTIAL_EVIDENCE,
    PRICE_CONFLICT,
    STALE_COST,
    Claim,
    ClaimDraft,
    ClaimStatus,
    Locator,
    Source,
    SourceDraft,
    VerificationJudgment,
    compute_claim_id,
)

__all__ = [
    "assert_claim",
    "verify",
    "filter_claims",
    "FilterPolicy",
    "FilterResult",
    "GroundingError",
    "SourceCache",
    "CacheError",
    "locate",
    "Claim",
    "ClaimDraft",
    "ClaimStatus",
    "Locator",
    "Source",
    "SourceDraft",
    "VerificationJudgment",
    "compute_claim_id",
    "PARTIAL_EVIDENCE",
    "STALE_COST",
    "PRICE_CONFLICT",
]
