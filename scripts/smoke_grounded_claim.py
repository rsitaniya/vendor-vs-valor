"""Load-bearing smoke test (CLAUDE.md): confirm Gemini reliably returns the
structured ClaimDraft shape with a *locatable* verbatim quote, and that the full
assert -> verify pipeline works on REAL model calls — BEFORE the research stage
is built on top of it.

Run: uv run python scripts/smoke_grounded_claim.py
"""

from __future__ import annotations

import sys
import tempfile

from llm import flash_model, get_provider
from skills.grounded_claim import (
    ClaimDraft,
    SourceCache,
    SourceDraft,
    assert_claim,
    verify,
)

URL = "https://en.wikipedia.org/wiki/Vector_database"


def main() -> int:
    provider = get_provider()
    print(f"provider ready; flash model = {flash_model()}")

    with tempfile.TemporaryDirectory() as run_dir:
        cache = SourceCache(run_dir)
        content = cache.fetch(URL)
        print(f"fetched + cached {URL} ({len(content)} chars extracted)")
        if len(content) < 500:
            print("FAIL: extracted content too short to test grounding")
            return 1

        excerpt = content[:6000]
        prompt = (
            "From the SOURCE TEXT below, state ONE atomic, checkable factual claim.\n"
            "Provide a display_quote that is copied VERBATIM from the source text "
            "(an exact substring, <15 words). Use this exact url for the source: "
            f"{URL}\n\nSOURCE TEXT:\n{excerpt}\n"
        )
        draft = provider.complete(prompt, response_schema=ClaimDraft, model=flash_model())
        print("\n--- structured ClaimDraft returned by Gemini ---")
        print(f"  text : {draft.text}")
        print(f"  quote: {draft.sources[0].display_quote!r}")

        # Use the known cached URL + the model's quote; locator is computed by code.
        src = SourceDraft(url=URL, display_quote=draft.sources[0].display_quote)
        try:
            claim = assert_claim(draft.text, [src], "m10", "BUY", cache)
        except Exception as exc:  # noqa: BLE001 — smoke test surfaces the risk plainly
            print(f"\nFAIL: quote not locatable in cached content -> {exc}")
            print("  (this is exactly the load-bearing risk; flag to the user if it recurs)")
            return 1
        print(f"\nassert_claim OK: id={claim.id} locator={claim.sources[0].locator.start}"
              f":{claim.sources[0].locator.end} status={claim.status.value}")

        verified = verify(claim, cache, provider=provider)
        print(f"verify OK: status -> {verified.status.value}")

    print("\nSMOKE PASS: structured output + locator + verify all worked on real Gemini.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
