"""Provider selection + model-tier helpers.

The active provider is chosen by the ``LLM_PROVIDER`` env var; model ids come
from env too, so nothing about the model is hard-coded in a node.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .provider import LLMProvider

load_dotenv()  # make .env values available to os.environ


def flash_model() -> str:
    """The workhorse model id (research, verify)."""
    return os.environ.get("GEMINI_MODEL_FLASH", "gemini-3.5-flash")


def pro_model() -> str:
    """The headroom model id (synthesis)."""
    return os.environ.get("GEMINI_MODEL_PRO", "gemini-3.5-pro")


def get_provider() -> LLMProvider:
    """Return the configured provider instance."""
    name = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if name == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider()
    raise ValueError(f"unknown LLM_PROVIDER {name!r} (MVP ships 'gemini')")


__all__ = ["LLMProvider", "get_provider", "flash_model", "pro_model"]
