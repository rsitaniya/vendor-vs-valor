"""Slice 1 acceptance: the rubric spine loads, validates, and holds invariants."""

from __future__ import annotations

import pytest

import rubric
from rubric import RubricError


def test_paths_load_and_are_the_four_canonical_paths():
    paths = rubric.load_paths()
    assert set(paths) == set(rubric.CANONICAL_PATHS)
    # Four paths, never five — acquire is gone.
    assert "acquire" not in paths


def test_paths_reference_only_known_pools():
    for name, spec in rubric.load_paths().items():
        assert spec["pools"], f"{name} has no pools"
        assert set(spec["pools"]) <= rubric.VALID_POOLS


def test_buy_then_extend_is_gated_on_api_surface():
    # The gate that makes buy-then-extend real (spec §3.3).
    assert "gate" in rubric.load_paths()["buy_then_extend"]


def test_metrics_load_with_unique_ids_and_14_dimensions():
    dims = rubric.load_metrics()
    ids = [d["id"] for d in dims]
    assert len(ids) == len(set(ids)), "duplicate dimension ids"
    assert len(dims) == 14  # the 14 survive as structure (design v2 §3.3)


def test_cost_dimensions_are_exactly_m3_m4_m5():
    # grounded_claim reads the cost flag from config, not a hardcoded set.
    assert rubric.cost_tagged_dimensions() == {"m3", "m4", "m5"}


def test_portfolio_reuse_is_dormant_in_mvp():
    m12 = next(d for d in rubric.load_metrics() if d["id"] == "m12")
    assert m12["tracks"] == []  # research does not chase reuse in the MVP


def test_validate_all_passes_on_shipped_rubric():
    rubric.validate_all()  # must not raise


# --- the validator must FAIL loudly on bad config (Coding Contract rule 12) ---

def test_loader_rejects_missing_path(monkeypatch, tmp_path):
    monkeypatch.setattr(rubric, "PATHS_PATH", tmp_path / "nope.json")
    with pytest.raises(RubricError):
        rubric.load_paths()


def test_loader_rejects_extra_path(monkeypatch, tmp_path):
    bad = tmp_path / "paths.json"
    bad.write_text('{"paths": {"build": {"pools": ["BUILD"]}, "acquire": {"pools": ["BUY"]}}}')
    monkeypatch.setattr(rubric, "PATHS_PATH", bad)
    with pytest.raises(RubricError):
        rubric.load_paths()


def test_loader_rejects_unknown_pool(monkeypatch, tmp_path):
    bad = tmp_path / "paths.json"
    bad.write_text(
        '{"paths": {"build": {"pools": ["NOPE"]}, "buy": {"pools": ["BUY"]},'
        ' "buy_then_extend": {"pools": ["BUY"]}, "adopt_self_host": {"pools": ["BUILD"]}}}'
    )
    monkeypatch.setattr(rubric, "PATHS_PATH", bad)
    with pytest.raises(RubricError):
        rubric.load_paths()


def test_loader_rejects_duplicate_dimension_id(monkeypatch, tmp_path):
    bad = tmp_path / "metrics.json"
    bad.write_text(
        '{"dimensions": ['
        '{"id": "m1", "name": "a", "question": "q", "cost_tagged": true, "tracks": []},'
        '{"id": "m1", "name": "b", "question": "q", "cost_tagged": false, "tracks": []}]}'
    )
    monkeypatch.setattr(rubric, "METRICS_PATH", bad)
    with pytest.raises(RubricError):
        rubric.load_metrics()


def test_loader_rejects_look_for_not_matching_tracks(monkeypatch, tmp_path):
    bad = tmp_path / "metrics.json"
    bad.write_text(
        '{"dimensions": [{"id": "m3", "name": "cost", "question": "q",'
        ' "cost_tagged": true, "tracks": ["BUILD"], "look_for": {"BUY": ["x"]}}]}'
    )
    monkeypatch.setattr(rubric, "METRICS_PATH", bad)
    with pytest.raises(RubricError):
        rubric.load_metrics()
