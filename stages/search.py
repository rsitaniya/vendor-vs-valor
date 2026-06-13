"""Search-to-discover via DuckDuckGo (ddgs). Discovery only — full content is
fetched + cached separately so the Claim locator can index into it.

The signature ``search(query, max_results) -> list[url]`` is what run_research
depends on; tests inject a fake with the same shape (no network).
"""

from __future__ import annotations

from ddgs import DDGS


def ddg_search(query: str, max_results: int = 5) -> list[str]:
    urls: list[str] = []
    try:
        for result in DDGS().text(query, max_results=max_results):
            url = result.get("href") or result.get("url")
            if url:
                urls.append(url)
    except Exception:
        # A flaky/blocked search is a coverage gap, not a crash (spec §7).
        return urls
    return urls
