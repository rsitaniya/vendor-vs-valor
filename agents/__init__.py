"""Agent prompts (the IP) live here as .md files; code loads them by name."""

from __future__ import annotations

from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Load the prompt text for an agent (e.g. 'intake', 'research_build')."""
    path = AGENTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"agent prompt not found: {path}")
    return path.read_text(encoding="utf-8")
