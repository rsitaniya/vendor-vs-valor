"""GeminiProvider's retry/backoff wrapper around transient API errors."""

from __future__ import annotations

from google.genai import errors as genai_errors

from llm.gemini import _MAX_ATTEMPTS, _call_with_retry


def _api_error(code: int) -> genai_errors.APIError:
    return genai_errors.APIError(code, {"message": "boom"})


def test_returns_result_on_first_success():
    assert _call_with_retry(lambda: "ok") == "ok"


def test_retries_a_rate_limit_error_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise _api_error(429)
        return "ok"

    assert _call_with_retry(fn) == "ok"
    assert calls["n"] == 2


def test_exhausts_retries_on_persistent_server_error(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise _api_error(503)

    try:
        _call_with_retry(fn)
        assert False, "expected APIError to propagate"
    except genai_errors.APIError:
        pass
    assert calls["n"] == _MAX_ATTEMPTS


def test_does_not_retry_a_non_retryable_client_error(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: (_ for _ in ()).throw(
        AssertionError("should not sleep/retry a 400")))
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise _api_error(400)

    try:
        _call_with_retry(fn)
        assert False, "expected APIError to propagate"
    except genai_errors.APIError:
        pass
    assert calls["n"] == 1
