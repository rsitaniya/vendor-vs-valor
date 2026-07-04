"""Gemini implementation of :class:`LLMProvider` (the MVP default).

Uses the unified ``google-genai`` SDK. Structured output is requested via
``response_schema`` (a Pydantic model) + ``response_mime_type`` and read back
from ``response.parsed`` (with a ``response.text`` fallback).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from .provider import LLMProvider, T

# Transient: worth retrying. 429 = rate limit; 5xx = server-side.
# Everything else (400/401/403/404/...) is a config problem retries can't fix.
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4  # 1 initial call + 3 retries
_BASE_DELAY_S = 1.0

_R = TypeVar("_R")


def _is_retryable(exc: genai_errors.APIError) -> bool:
    return exc.code in _RETRYABLE_CODES


def _call_with_retry(fn: Callable[[], _R]) -> _R:
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except genai_errors.APIError as exc:
            if not _is_retryable(exc) or attempt == _MAX_ATTEMPTS - 1:
                raise
            time.sleep(_BASE_DELAY_S * (2**attempt))
    raise AssertionError("unreachable")  # pragma: no cover


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (.env)")
        self._client = genai.Client(api_key=key)
        self._default_model = default_model or os.environ.get(
            "GEMINI_MODEL_FLASH", "gemini-3.5-flash"
        )

    def complete(
        self,
        prompt: str,
        *,
        response_schema: type[T] | None = None,
        model: str | None = None,
    ) -> T | str:
        config = None
        if response_schema is not None:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )
        response = _call_with_retry(lambda: self._client.models.generate_content(
            model=model or self._default_model,
            contents=prompt,
            config=config,
        ))
        if response_schema is None:
            return response.text or ""
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, BaseModel):
            return parsed  # type: ignore[return-value]
        # Fallback: some model/SDK combinations leave .parsed empty.
        return response_schema.model_validate_json(response.text or "")
