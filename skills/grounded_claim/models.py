"""The data contracts of the trust layer (spec §3.1).

Two families of shape, deliberately separate:

* **Author-facing drafts** (``ClaimDraft`` / ``SourceDraft``) — the *minimal*
  thing an LLM emits: claim text + (url, verbatim quote). No id, no status, no
  locator, no defaults. This dodges Gemini's struct-output default-value quirk
  AND enforces the core invariant: an author can never set ``status``.
* **Code-built objects** (``Claim`` / ``Source`` / ``Locator``) — assembled by
  ``assert_claim`` from a draft + the source cache. The locator and dates are
  computed from cached content, never trusted from the author.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# --- flags applied by filter (rendered visually distinct in the report) ---
PARTIAL_EVIDENCE = "partial_evidence"
STALE_COST = "stale_cost"
PRICE_CONFLICT = "price_conflict"  # set later by synthesis (LLM-judged), not filter


class ClaimStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


# --- author-facing drafts (what the LLM returns via structured output) ---

class SourceDraft(BaseModel):
    url: str
    display_quote: str  # verbatim span copied from the source content (<~15 words)


class ClaimDraft(BaseModel):
    text: str
    dimension: str
    sources: list[SourceDraft]


# --- code-built objects (assembled by assert_claim) ---

class Locator(BaseModel):
    type: Literal["char_span"] = "char_span"
    start: int
    end: int


class Source(BaseModel):
    url: str
    title: str | None = None
    accessed_date: str
    source_date: str | None = None
    locator: Locator
    display_quote: str


class Claim(BaseModel):
    id: str
    text: str
    sources: list[Source]
    dimension: str
    track: str
    cost_tagged: bool = False
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    flags: list[str] = Field(default_factory=list)


# --- verifier output (independent judge; never trusts the author) ---

class VerificationJudgment(BaseModel):
    verdict: Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"]
    reason: str


def compute_claim_id(text: str, source_urls: list[str]) -> str:
    """Content-addressed id: ``hash(text + sorted(source_urls))`` (spec §3.1)."""
    payload = "\n".join([text, *sorted(source_urls)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:6]
