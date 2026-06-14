"""The trust layer's three operations (spec §3.1).

``assert_claim`` (author) -> UNVERIFIED claims, structurally constrained to the
cache. ``verify`` (independent judge) -> the only thing that may set a status,
by re-reading cached bytes. ``filter`` -> policy: drop UNSUPPORTED, flag the
rest. The author can never bless its own claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from engine.constants import STALE_DAYS as _STALE_DAYS, VERIFY_CONTEXT_CHARS as _CONTEXT_CHARS
from llm import flash_model, get_provider
from llm.provider import LLMProvider
from rubric import VALID_POOLS, cost_tagged_dimensions, dimension_ids

from .cache import SourceCache
from .locate import locate
from .models import (
    PARTIAL_EVIDENCE,
    STALE_COST,
    UNDATED_COST,
    Claim,
    ClaimStatus,
    Locator,
    Source,
    SourceDraft,
    VerificationJudgment,
    compute_claim_id,
)

# verdict precedence: a claim is as strong as its strongest supporting source.
_RANK = {ClaimStatus.SUPPORTED: 3, ClaimStatus.PARTIAL: 2, ClaimStatus.UNSUPPORTED: 1}


class GroundingError(ValueError):
    """Raised when a claim violates a structural grounding rule."""


def assert_claim(
    text: str,
    sources: list[SourceDraft],
    dimension: str,
    track: str,
    cache: SourceCache,
    *,
    cost_tagged: bool | None = None,
) -> Claim:
    """Create an UNVERIFIED claim, or reject it. Never sets a verified status."""
    if not text or not text.strip():
        raise GroundingError("claim text is empty")
    if not sources:
        raise GroundingError("a claim with no source is unconstructable (spec §3.1)")
    if dimension not in dimension_ids():
        raise GroundingError(f"unknown dimension {dimension!r}")
    if track not in VALID_POOLS:
        raise GroundingError(f"unknown track {track!r}")

    is_cost = cost_tagged if cost_tagged is not None else (dimension in cost_tagged_dimensions())

    built: list[Source] = []
    urls: list[str] = []
    for draft in sources:
        url, quote = draft.url, draft.display_quote
        if not cache.has(url):
            raise GroundingError(f"url not in cache (outside the closed pool): {url}")

        content = cache.get_content(url)
        span = locate(quote, content)
        if span is None:
            raise GroundingError(f"display_quote not locatable in cached content: {quote!r}")

        meta = cache.get_meta(url)
        source_date = meta.get("source_date")
        if is_cost and not source_date:
            raise GroundingError(
                f"cost-tagged claim needs a dated source (spec §3.1.3): {url}"
            )

        built.append(Source(
            url=url,
            title=meta.get("title"),
            accessed_date=meta["accessed_date"],
            source_date=source_date,
            locator=Locator(start=span[0], end=span[1]),
            display_quote=quote,
        ))
        urls.append(url)

    return Claim(
        id=compute_claim_id(text, urls),
        text=text,
        sources=built,
        dimension=dimension,
        track=track,
        cost_tagged=is_cost,
        status=ClaimStatus.UNVERIFIED,  # only verify() may change this
    )


def _verify_prompt(claim_text: str, snippet: str) -> str:
    return (
        "You independently check whether a SOURCE EXCERPT supports a CLAIM.\n"
        "Judge ONLY from the excerpt. Do not use outside knowledge.\n"
        "- SUPPORTED: the excerpt clearly supports the claim.\n"
        "- PARTIAL: related but incomplete, or weaker than the claim asserts.\n"
        "- UNSUPPORTED: the excerpt does not support the claim.\n\n"
        f"CLAIM:\n{claim_text}\n\nSOURCE EXCERPT:\n{snippet}\n"
    )


def verify(claim: Claim, cache: SourceCache, provider: LLMProvider | None = None) -> Claim:
    """Independently label the claim by re-reading cached content via the locator.

    Reads the cached bytes itself; never trusts the author's display_quote.
    Returns a copy with ``status`` set — the sole place status is assigned.
    """
    provider = provider or get_provider()
    verdicts: list[ClaimStatus] = []
    for src in claim.sources:
        content = cache.get_content(src.url)
        start = max(0, src.locator.start - _CONTEXT_CHARS)
        end = min(len(content), src.locator.end + _CONTEXT_CHARS)
        snippet = content[start:end]
        judgment = provider.complete(
            _verify_prompt(claim.text, snippet),
            response_schema=VerificationJudgment,
            model=flash_model(),
        )
        verdicts.append(ClaimStatus(judgment.verdict))

    status = max(verdicts, key=_RANK.get) if verdicts else ClaimStatus.UNSUPPORTED
    return claim.model_copy(update={"status": status})


@dataclass
class FilterPolicy:
    staleness_days: int = _STALE_DAYS


@dataclass
class FilterResult:
    kept: list[Claim] = field(default_factory=list)
    dropped: list[Claim] = field(default_factory=list)


def _is_stale_cost(claim: Claim, policy: FilterPolicy) -> bool:
    if not claim.cost_tagged:
        return False
    for src in claim.sources:
        if not src.source_date:
            continue
        try:
            age = (date.fromisoformat(src.accessed_date) - date.fromisoformat(src.source_date)).days
        except ValueError:
            continue
        if age > policy.staleness_days:
            return True
    return False


def filter_claims(claims: list[Claim], policy: FilterPolicy | None = None) -> FilterResult:
    """Drop UNSUPPORTED; keep + flag the rest (spec §3.1 filter)."""
    policy = policy or FilterPolicy()
    result = FilterResult()
    for claim in claims:
        if claim.status == ClaimStatus.UNSUPPORTED:
            result.dropped.append(claim)
            continue
        flags = list(claim.flags)
        if claim.status == ClaimStatus.PARTIAL and PARTIAL_EVIDENCE not in flags:
            flags.append(PARTIAL_EVIDENCE)
        if _is_stale_cost(claim, policy) and STALE_COST not in flags:
            flags.append(STALE_COST)
        result.kept.append(claim.model_copy(update={"flags": flags}))
    return result
