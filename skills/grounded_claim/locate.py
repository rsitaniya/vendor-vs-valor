"""Resolve a verbatim quote to a char span in cached content.

The author (LLM) supplies a ``display_quote``; code computes the locator rather
than trusting the LLM to count characters. Three escalating strategies:
exact substring, whitespace-tolerant regex, then fuzzy block match. If none
clears the bar the quote is unlocatable and the claim is rejected upstream.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_FUZZY_THRESHOLD = 0.8


def locate(quote: str, content: str) -> tuple[int, int] | None:
    """Return ``(start, end)`` char offsets into ``content`` or ``None``."""
    quote = quote.strip()
    if not quote or not content:
        return None

    # 1) exact substring
    idx = content.find(quote)
    if idx != -1:
        return idx, idx + len(quote)

    # 2) whitespace-tolerant: tokens of the quote separated by any whitespace
    tokens = [re.escape(tok) for tok in quote.split()]
    if tokens:
        pattern = re.compile(r"\s+".join(tokens))
        match = pattern.search(content)
        if match:
            return match.start(), match.end()

    # 3) fuzzy: longest matching block; accept only if it covers most of the quote
    matcher = SequenceMatcher(None, quote, content, autojunk=False)
    block = matcher.find_longest_match(0, len(quote), 0, len(content))
    if block.size and (block.size / len(quote)) >= _FUZZY_THRESHOLD:
        return block.b, block.b + block.size

    return None
