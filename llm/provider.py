"""The model provider interface.

A node never imports a concrete provider — it depends on this interface and
gets the configured implementation from :func:`llm.get_provider`. Swapping
Gemini for Claude/GPT is therefore a config change (env var), not a refactor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Minimal contract every provider implements.

    One method: turn a prompt into either free text or a validated instance of
    a Pydantic ``response_schema`` (structured output).
    """

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        response_schema: type[T] | None = None,
        model: str | None = None,
    ) -> T | str:
        """Return ``response_schema`` instance if given, else the raw text."""
        raise NotImplementedError
