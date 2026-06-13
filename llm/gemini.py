"""Gemini implementation of :class:`LLMProvider` (the MVP default).

Uses the unified ``google-genai`` SDK. Structured output is requested via
``response_schema`` (a Pydantic model) + ``response_mime_type`` and read back
from ``response.parsed`` (with a ``response.text`` fallback).
"""

from __future__ import annotations

import os

from google import genai
from google.genai import types
from pydantic import BaseModel

from .provider import LLMProvider, T


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
        response = self._client.models.generate_content(
            model=model or self._default_model,
            contents=prompt,
            config=config,
        )
        if response_schema is None:
            return response.text or ""
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, BaseModel):
            return parsed  # type: ignore[return-value]
        # Fallback: some model/SDK combinations leave .parsed empty.
        return response_schema.model_validate_json(response.text or "")
