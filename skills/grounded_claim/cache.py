"""The per-run source cache — the closed evidence pool (spec §3.1.1).

Each source is fetched **once**; its extracted main-text *content* is cached at
``sources/<sha256(url)>.content`` with a ``.meta`` sidecar. ``verify`` re-reads
these cached bytes, never the live web. ``assert_claim`` may only cite URLs that
already live here. Tests seed the cache with :meth:`add` (no network).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import trafilatura

from engine.constants import MIN_CONTENT_CHARS

# Many sites (e.g. Wikipedia) reject non-descriptive bot agents with 403.
# A standard browser UA is the pragmatic choice for research fetching.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class CacheError(RuntimeError):
    """Raised when cached content is requested for an un-cached URL."""


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class SourceCache:
    def __init__(self, run_dir: str | Path):
        self.dir = Path(run_dir) / "sources"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _content_path(self, url: str) -> Path:
        return self.dir / f"{_key(url)}.content"

    def _meta_path(self, url: str) -> Path:
        return self.dir / f"{_key(url)}.meta"

    def has(self, url: str) -> bool:
        return self._content_path(url).exists()

    def get_content(self, url: str) -> str:
        if not self.has(url):
            raise CacheError(f"url not in cache: {url}")
        return self._content_path(url).read_text(encoding="utf-8")

    def get_meta(self, url: str) -> dict:
        if not self._meta_path(url).exists():
            raise CacheError(f"url not in cache: {url}")
        return json.loads(self._meta_path(url).read_text(encoding="utf-8"))

    def add(self, url: str, content: str, *, title: str | None = None,
            source_date: str | None = None, accessed_date: str | None = None) -> str:
        """Write content + meta directly (used by fetch and by tests)."""
        meta = {
            "url": url,
            "title": title,
            "accessed_date": accessed_date or date.today().isoformat(),
            "source_date": source_date,
            "content_chars": len(content),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        self._content_path(url).write_text(content, encoding="utf-8")
        self._meta_path(url).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return content

    def fetch(self, url: str, *, timeout: float = 30.0) -> str:
        """Fetch + extract main text once, then cache. Re-reads cache if present.

        Falls back to Jina Reader when trafilatura returns thin content — covers
        JS-rendered vendor pricing pages that return little to no text directly.
        """
        if self.has(url):
            return self.get_content(url)
        resp = httpx.get(url, follow_redirects=True, timeout=timeout,
                         headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        html = resp.text
        content = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
        title, source_date = None, None
        meta = trafilatura.extract_metadata(html)
        if meta is not None:
            title = meta.title
            source_date = meta.date  # 'YYYY-MM-DD' or None

        if len(content.strip()) < MIN_CONTENT_CHARS:
            # Thin content — likely a JS-rendered page. Try Jina Reader which
            # returns a pre-rendered version; run trafilatura on its output.
            jina_url = f"https://r.jina.ai/{url}"
            try:
                resp2 = httpx.get(jina_url, follow_redirects=True, timeout=timeout,
                                  headers={"User-Agent": _USER_AGENT})
                resp2.raise_for_status()
                jina_content = trafilatura.extract(
                    resp2.text, include_comments=False, include_tables=True
                ) or ""
                if len(jina_content.strip()) > len(content.strip()):
                    content = jina_content
                    jina_meta = trafilatura.extract_metadata(resp2.text)
                    if jina_meta is not None:
                        title = title or jina_meta.title
                        source_date = source_date or jina_meta.date
            except Exception:  # noqa: BLE001 — fallback; original content used if Jina fails
                pass

        return self.add(url, content, title=title, source_date=source_date)
