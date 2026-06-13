"""Rubric: the engine's spine (config, not a skill).

Two files validated here:
- ``metrics.json`` — the 14 research dimensions (checklist + dossier structure).
- ``paths.json``   — the path -> evidence-pool mapping (spec §3.3).

Validation is strict and fails loudly: a malformed rubric is a build-time bug,
not something to smooth over (Coding Contract rule 12). Loaders return plain
data; callers (grounded_claim, synthesis) consume it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RUBRIC_DIR = Path(__file__).resolve().parent
METRICS_PATH = RUBRIC_DIR / "metrics.json"
PATHS_PATH = RUBRIC_DIR / "paths.json"

#: The only evidence pools that exist (research tracks).
VALID_POOLS = frozenset({"BUILD", "BUY"})

#: The four paths — and only four. Acquire does not exist anywhere (design v2 §3.1).
CANONICAL_PATHS = frozenset({"build", "buy", "buy_then_extend", "adopt_self_host"})

#: The 14 dimensions survive as fixed structure (design v2 §3.3).
CANONICAL_DIMENSION_IDS = frozenset(f"m{i}" for i in range(1, 15))

#: Cost dimensions drive stricter grounded_claim source-date/staleness rules.
COST_TAGGED_DIMENSION_IDS = frozenset({"m3", "m4", "m5"})

#: Gates synthesis must respect before presenting conditional paths.
REQUIRED_PATH_GATES = {
    "buy_then_extend": "buy.api_surface present",
}

_ID_RE = re.compile(r"^m\d+$")


class RubricError(ValueError):
    """Raised when a rubric file is structurally invalid."""


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise RubricError(f"rubric file missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RubricError(f"{path.name} is not valid JSON: {exc}") from exc


def load_paths() -> dict[str, dict]:
    """Load + validate ``paths.json``; return the ``path_name -> spec`` mapping."""
    raw = _read_json(PATHS_PATH)
    paths = raw.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise RubricError("paths.json: 'paths' must be a non-empty object")

    names = set(paths)
    if names != set(CANONICAL_PATHS):
        missing = CANONICAL_PATHS - names
        extra = names - CANONICAL_PATHS
        raise RubricError(
            f"paths.json must define exactly the four canonical paths. "
            f"missing={sorted(missing)} unexpected={sorted(extra)}"
        )
    # Belt-and-suspenders: the dropped path must never reappear, by any spelling.
    if any("acquire" in name.lower() for name in names):
        raise RubricError("paths.json: 'acquire' is not a valid path (dropped everywhere)")

    for name, spec in paths.items():
        pools = spec.get("pools")
        if not isinstance(pools, list) or not pools:
            raise RubricError(f"paths.json: path '{name}' needs a non-empty 'pools' list")
        bad = set(pools) - VALID_POOLS
        if bad:
            raise RubricError(f"paths.json: path '{name}' has unknown pools {sorted(bad)}")

        expected_gate = REQUIRED_PATH_GATES.get(name)
        if expected_gate is not None and spec.get("gate") != expected_gate:
            raise RubricError(
                f"paths.json: path '{name}' must define gate {expected_gate!r}"
            )
    return paths


def load_metrics() -> list[dict]:
    """Load + validate ``metrics.json``; return the list of dimension objects."""
    raw = _read_json(METRICS_PATH)
    dims = raw.get("dimensions")
    if not isinstance(dims, list) or not dims:
        raise RubricError("metrics.json: 'dimensions' must be a non-empty list")

    seen: set[str] = set()
    for dim in dims:
        dim_id = dim.get("id")
        if not isinstance(dim_id, str) or not _ID_RE.match(dim_id):
            raise RubricError(f"metrics.json: bad dimension id {dim_id!r} (expected 'm<number>')")
        if dim_id in seen:
            raise RubricError(f"metrics.json: duplicate dimension id {dim_id!r}")
        seen.add(dim_id)

        if not dim.get("name") or not dim.get("question"):
            raise RubricError(f"metrics.json: {dim_id} needs non-empty 'name' and 'question'")
        if not isinstance(dim.get("cost_tagged"), bool):
            raise RubricError(f"metrics.json: {dim_id} 'cost_tagged' must be a bool")

        tracks = dim.get("tracks", [])
        if not isinstance(tracks, list):
            raise RubricError(f"metrics.json: {dim_id} 'tracks' must be a list")
        bad = set(tracks) - VALID_POOLS
        if bad:
            raise RubricError(f"metrics.json: {dim_id} has unknown tracks {sorted(bad)}")

        # If a dimension is researched, every track it claims must have scoping hints.
        if tracks:
            look_for = dim.get("look_for")
            if not isinstance(look_for, dict) or set(look_for) != set(tracks):
                raise RubricError(
                    f"metrics.json: {dim_id} 'look_for' keys must match tracks {sorted(tracks)}"
                )
            for track, hints in look_for.items():
                if not isinstance(hints, list) or not hints:
                    raise RubricError(f"metrics.json: {dim_id} look_for[{track}] must be non-empty")

    if seen != CANONICAL_DIMENSION_IDS:
        missing = CANONICAL_DIMENSION_IDS - seen
        extra = seen - CANONICAL_DIMENSION_IDS
        raise RubricError(
            f"metrics.json must define exactly the 14 canonical dimensions. "
            f"missing={sorted(missing)} unexpected={sorted(extra)}"
        )

    cost_tagged = {dim["id"] for dim in dims if dim["cost_tagged"]}
    if cost_tagged != COST_TAGGED_DIMENSION_IDS:
        missing = COST_TAGGED_DIMENSION_IDS - cost_tagged
        extra = cost_tagged - COST_TAGGED_DIMENSION_IDS
        raise RubricError(
            f"metrics.json must tag exactly the canonical cost dimensions. "
            f"missing={sorted(missing)} unexpected={sorted(extra)}"
        )
    return dims


def cost_tagged_dimensions() -> set[str]:
    """Dimension ids whose claims carry the stricter cost rules (spec §3.1.3)."""
    return {dim["id"] for dim in load_metrics() if dim["cost_tagged"]}


def dimension_ids() -> set[str]:
    """All valid dimension ids (used to validate a Claim's ``dimension`` tag)."""
    return {dim["id"] for dim in load_metrics()}


def validate_all() -> None:
    """Load + validate both rubric files; raise :class:`RubricError` on any problem."""
    load_paths()
    load_metrics()
