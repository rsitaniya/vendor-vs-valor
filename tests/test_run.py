"""run.py's pure gate-editing logic: profile validation and soft-steer edits."""

from __future__ import annotations

import json

from engine.runstore import RunStore
from run import apply_soft_steer, load_and_validate_profile

_VALID_PROFILE = {
    "run_id": "r1",
    "need": {"capability": "x", "business_context": "y", "problem": "z"},
    "intent": {"core_value_proximity": "core", "rationale": "r"},
    "resources": {"eng_headcount": 1, "relevant_skills": [], "budget_note": "n",
                  "runway_note": "n", "expected_scale": "n", "procurement_process": "n"},
    "constraints": {"compliance": [], "data_sensitivity": "n", "data_residency": "n",
                    "required_certifications": [], "existing_stack": [],
                    "integration_requirements": [], "timeline_hard_stop": "n"},
    "customization_need": "low",
    "soft_steer": "cost matters",
    "reversibility_criteria": "n",
    "portfolio_note": "n",
}


def _write_profile(store: RunStore, data: dict) -> None:
    store.artifact_path("profile.json").write_text(json.dumps(data), encoding="utf-8")


def test_load_and_validate_profile_returns_data_for_valid_profile(tmp_path):
    store = RunStore(tmp_path)
    _write_profile(store, _VALID_PROFILE)
    data = load_and_validate_profile(store.artifact_path("profile.json"))
    assert data == _VALID_PROFILE


def test_load_and_validate_profile_returns_none_for_invalid_json(tmp_path):
    store = RunStore(tmp_path)
    store.artifact_path("profile.json").write_text("not json", encoding="utf-8")
    assert load_and_validate_profile(store.artifact_path("profile.json")) is None


def test_load_and_validate_profile_returns_none_for_failed_contract(tmp_path):
    store = RunStore(tmp_path)
    bad = {**_VALID_PROFILE, "soft_steer": ""}
    _write_profile(store, bad)
    assert load_and_validate_profile(store.artifact_path("profile.json")) is None


def test_apply_soft_steer_updates_json_and_regenerates_md(tmp_path):
    store = RunStore(tmp_path)
    _write_profile(store, _VALID_PROFILE)
    apply_soft_steer(store, "speed matters most")
    data = json.loads(store.artifact_path("profile.json").read_text())
    assert data["soft_steer"] == "speed matters most"
    assert "speed matters most" in store.artifact_path("profile.md").read_text()
