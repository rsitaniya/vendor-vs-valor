"""The per-run source cache — the closed evidence pool (spec §3.1.1).

Each source is fetched **once**; its extracted main-text *content* is cached at
``sources/<sha256(url)>.content`` with a ``.meta`` sidecar. ``verify`` re-reads
these cached bytes, never the live web. ``assert_claim`` may only cite URLs that
already live here. Tests seed the cache with :meth:`add` (no network).
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from engine.constants import MIN_CONTENT_CHARS

# Many sites (e.g. Wikipedia) reject non-descriptive bot agents with 403.
# A standard browser UA is the pragmatic choice for research fetching.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_MAX_REDIRECTS = 5


class CacheError(RuntimeError):
    """Raised when cached content is requested for an un-cached URL."""


class FetchError(RuntimeError):
    """Raised when a URL is refused before fetching: unsupported scheme,
    unresolvable host, or a host that resolves to a private/internal address
    (SSRF guard — search results are untrusted third-party content)."""


def _reject_private_targets(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError(f"unsupported URL scheme: {url}")
    host = parsed.hostname
    if not host:
        raise FetchError(f"no host in URL: {url}")
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise FetchError(f"could not resolve host: {host} ({exc})") from exc
    for addr in addrs:
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise FetchError(f"refusing to fetch private/internal host: {host} ({addr})")


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

    def _get_validated(self, url: str, *, timeout: float) -> httpx.Response:
        """GET with scheme/private-host checks re-applied at every redirect hop
        (search results are untrusted; a hop could point at an internal
        service). ``httpx``'s own ``follow_redirects`` only validates the
        first URL, not where 3xx responses lead."""
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            _reject_private_targets(current)
            resp = httpx.get(current, follow_redirects=False, timeout=timeout,
                             headers={"User-Agent": _USER_AGENT})
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    break
                current = urljoin(current, location)
                continue
            resp.raise_for_status()
            return resp
        raise FetchError(f"too many redirects: {url}")

    def fetch(self, url: str, *, timeout: float = 30.0) -> str:
        """Fetch + extract main text once, then cache. Re-reads cache if present.

        Falls back to Jina Reader when trafilatura returns thin content — covers
        JS-rendered vendor pricing pages that return little to no text directly.
        """
        if self.has(url):
            return self.get_content(url)
        resp = self._get_validated(url, timeout=timeout)
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
