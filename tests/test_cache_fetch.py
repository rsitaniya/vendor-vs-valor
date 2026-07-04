"""SourceCache.fetch()'s scheme/private-host guard (SSRF hardening).

Search results are untrusted third-party content, so both the initial URL and
every redirect hop must be re-checked before we let httpx touch it.
"""

from __future__ import annotations

import pytest

from skills.grounded_claim import FetchError, SourceCache
from skills.grounded_claim.cache import _reject_private_targets


def _resolve_to(monkeypatch, mapping: dict[str, str]) -> None:
    """Fake DNS: map hostname -> IP literal, no real network involved."""
    import socket

    def fake_getaddrinfo(host, *_a, **_kw):
        ip = mapping[host]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "file:///etc/passwd",
    "ftp://example.com/x",
])
def test_rejects_non_http_schemes(url):
    with pytest.raises(FetchError, match="scheme"):
        _reject_private_targets(url)


def test_rejects_loopback_host(monkeypatch):
    _resolve_to(monkeypatch, {"localhost": "127.0.0.1"})
    with pytest.raises(FetchError, match="private/internal"):
        _reject_private_targets("http://localhost/admin")


def test_rejects_private_network_host(monkeypatch):
    _resolve_to(monkeypatch, {"internal.example": "10.0.0.5"})
    with pytest.raises(FetchError, match="private/internal"):
        _reject_private_targets("http://internal.example/x")


def test_rejects_link_local_metadata_host(monkeypatch):
    _resolve_to(monkeypatch, {"metadata.example": "169.254.169.254"})
    with pytest.raises(FetchError, match="private/internal"):
        _reject_private_targets("http://metadata.example/latest/meta-data/")


def test_allows_public_host(monkeypatch):
    _resolve_to(monkeypatch, {"example.com": "93.184.216.34"})
    _reject_private_targets("https://example.com/page")  # does not raise


class _FakeResponse:
    def __init__(self, status_code, *, location=None, text=""):
        self.status_code = status_code
        self.headers = {"location": location} if location else {}
        self.text = text
        self.is_redirect = status_code in (301, 302, 303, 307, 308)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_refuses_to_follow_a_redirect_into_a_private_host(tmp_path, monkeypatch):
    _resolve_to(monkeypatch, {
        "public.example": "93.184.216.34",
        "internal.example": "10.0.0.5",
    })
    responses = {
        "http://public.example/page": _FakeResponse(302, location="http://internal.example/secret"),
    }

    def fake_get(url, *, follow_redirects, timeout, headers):
        assert follow_redirects is False, "must validate each hop manually, not auto-follow"
        return responses[url]

    monkeypatch.setattr("httpx.get", fake_get)

    cache = SourceCache(tmp_path)
    with pytest.raises(FetchError, match="private/internal"):
        cache.fetch("http://public.example/page")


def test_fetch_follows_a_redirect_between_two_public_hosts(tmp_path, monkeypatch):
    _resolve_to(monkeypatch, {
        "public.example": "93.184.216.34",
        "public-2.example": "93.184.216.35",
    })
    page = (
        "Real page content that is long enough to clear the minimum content "
        "threshold used to decide whether a fetched page is worth keeping as "
        "evidence, rather than being treated as thin/low-value content. " * 3
    )
    responses = {
        "http://public.example/page": _FakeResponse(302, location="http://public-2.example/final"),
        "http://public-2.example/final": _FakeResponse(200, text=f"<html><body>{page}</body></html>"),
    }

    def fake_get(url, *, follow_redirects, timeout, headers):
        return responses[url]

    monkeypatch.setattr("httpx.get", fake_get)

    cache = SourceCache(tmp_path)
    content = cache.fetch("http://public.example/page")
    assert "Real page content" in content
