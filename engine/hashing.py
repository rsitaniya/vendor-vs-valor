"""The input-hash guard (spec §4) — the idempotency core.

A stage skips its body and reuses its artifact if its recorded hash matches the
current one. The hash folds in everything that should invalidate the artifact:
upstream inputs, the prompt (the IP), the rubric, the model id, and a manual
engine_version. This is also what defuses LangGraph's "re-enter from the top on
resume" footgun — a re-run stage recomputes the same hash and no-ops.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from rubric import METRICS_PATH, PATHS_PATH

_RUBRIC_PATHS = (METRICS_PATH, PATHS_PATH)


def _update_section(digest, name: bytes, payload: bytes) -> None:
    digest.update(b"\x00")
    digest.update(name)
    digest.update(b"\x00")
    digest.update(payload)


def stage_input_hash(
    *,
    input_paths: list[Path],
    prompt: str,
    model_id: str,
    engine_version: str,
    extra: bytes = b"",
) -> str:
    digest = hashlib.sha256()
    # upstream artifacts this stage reads (sorted -> deterministic)
    for path in sorted(input_paths, key=str):
        _update_section(digest, b"input", Path(path).read_bytes())
    # a derived projection of inputs (e.g. research hashes only the profile
    # fields it uses, so editing the synthesis-only soft_steer does not
    # invalidate research — spec §4 gate-3 behavior)
    if extra:
        _update_section(digest, b"extra", extra)
    # the prompt is the IP: editing it must invalidate the stage
    _update_section(digest, b"prompt", prompt.encode("utf-8"))
    # rubric: metrics + paths feed every reasoning stage
    for rubric_path in _RUBRIC_PATHS:
        _update_section(digest, b"rubric", rubric_path.read_bytes())
    # same inputs, different model => different output
    _update_section(digest, b"model", model_id.encode("utf-8"))
    # manual bump on logic changes (MVP limitation; -> Target code-hash)
    _update_section(digest, b"engine", engine_version.encode("utf-8"))
    return digest.hexdigest()
