"""run.py's pure gate-editing logic: profile validation and soft-steer edits."""

from __future__ import annotations

import json

from graph import build_graph
from engine.runstore import RunStore
from run import (
    _MAX_CLARIFICATIONS,
    _open_in_browser,
    _run_gates,
    apply_clarifications,
    apply_soft_steer,
    clarify_profile,
    find_profile_gaps,
    load_and_validate_profile,
)

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


def test_find_profile_gaps_detects_placeholders_and_empty_lists():
    data = {
        "constraints": {"compliance": [], "data_sensitivity": "not specified",
                        "data_residency": "must stay in India", "timeline_hard_stop": "Q3 2026"},
        "resources": {"budget_note": "none", "expected_scale": "10k users/day"},
    }
    fields = [(section, field) for section, field, _ in find_profile_gaps(data)]
    assert ("constraints", "compliance") in fields
    assert ("constraints", "data_sensitivity") in fields
    assert ("resources", "budget_note") in fields
    assert ("constraints", "data_residency") not in fields
    assert ("resources", "expected_scale") not in fields
    assert ("constraints", "timeline_hard_stop") not in fields


def test_find_profile_gaps_returns_empty_for_a_complete_profile():
    data = {
        "constraints": {"compliance": ["none"], "data_sensitivity": "internal only",
                        "data_residency": "must stay in India", "timeline_hard_stop": "no hard stop"},
        "resources": {"budget_note": "$2k/mo", "expected_scale": "5k requests/day"},
    }
    assert find_profile_gaps(data) == []


def test_find_profile_gaps_caps_at_max_clarifications():
    assert len(find_profile_gaps({"constraints": {}, "resources": {}})) == _MAX_CLARIFICATIONS


def test_apply_clarifications_updates_string_and_list_fields(tmp_path):
    store = RunStore(tmp_path)
    _write_profile(store, _VALID_PROFILE)
    apply_clarifications(store, {
        ("constraints", "compliance"): "GDPR, SOC2",
        ("resources", "budget_note"): "$500/mo",
    })
    data = json.loads(store.artifact_path("profile.json").read_text())
    assert data["constraints"]["compliance"] == ["GDPR", "SOC2"]
    assert data["resources"]["budget_note"] == "$500/mo"
    assert "$500/mo" in store.artifact_path("profile.md").read_text()


def test_clarify_profile_prompts_only_for_gaps_and_applies_answers(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    gappy = {**_VALID_PROFILE,
             "constraints": {**_VALID_PROFILE["constraints"], "compliance": [],
                             "data_sensitivity": "not specified"}}
    _write_profile(store, gappy)
    answers = iter(["GDPR", "internal only, contains PII"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    clarify_profile(store)
    data = json.loads(store.artifact_path("profile.json").read_text())
    assert data["constraints"]["compliance"] == ["GDPR"]
    assert data["constraints"]["data_sensitivity"] == "internal only, contains PII"


def test_clarify_profile_is_a_no_op_when_profile_is_complete(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    _write_profile(store, {**_VALID_PROFILE,
                           "constraints": {**_VALID_PROFILE["constraints"], "compliance": ["none"]}})
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(
        AssertionError("should not prompt when there are no gaps")))
    clarify_profile(store)  # would raise if it prompted


def test_run_gates_auto_approve_drives_graph_to_completion(tmp_path):
    app = build_graph()  # in-memory checkpointer
    store = RunStore(tmp_path)
    config = {"configurable": {"thread_id": "t1"}}
    app.invoke({"run_id": "t1", "run_dir": str(tmp_path)}, config)

    _run_gates(app, config, store, auto_approve=True)

    assert app.get_state(config).next == ()


def test_run_gates_resumes_from_a_fresh_app_instance_via_sqlite(tmp_path):
    # Simulates a process restart: a brand-new build_graph()/checkpointer pair
    # backed by the same sqlite file must pick up the parked interrupt.
    from graph import sqlite_checkpointer

    db_path = tmp_path / "checkpoint.db"
    store = RunStore(tmp_path)
    config = {"configurable": {"thread_id": "t1"}}

    app_before_restart = build_graph(sqlite_checkpointer(db_path))
    app_before_restart.invoke({"run_id": "t1", "run_dir": str(tmp_path)}, config)
    assert app_before_restart.get_state(config).interrupts, "expected to park at gate 1"

    app_after_restart = build_graph(sqlite_checkpointer(db_path))
    _run_gates(app_after_restart, config, store, auto_approve=True)

    assert app_after_restart.get_state(config).next == ()


def test_open_in_browser_uses_open_on_macos(tmp_path, monkeypatch):
    monkeypatch.setattr("run.sys.platform", "darwin")
    calls = []
    monkeypatch.setattr("run.subprocess.run", lambda args, **kw: calls.append(args))
    _open_in_browser(tmp_path / "report.html")
    assert calls == [["open", str(tmp_path / "report.html")]]


def test_open_in_browser_uses_xdg_open_on_linux(tmp_path, monkeypatch):
    monkeypatch.setattr("run.sys.platform", "linux")
    calls = []
    monkeypatch.setattr("run.subprocess.run", lambda args, **kw: calls.append(args))
    _open_in_browser(tmp_path / "report.html")
    assert calls == [["xdg-open", str(tmp_path / "report.html")]]


def test_open_in_browser_notes_unknown_platform_without_crashing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("run.sys.platform", "win32")
    monkeypatch.setattr("run.subprocess.run", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("should not attempt to launch a subprocess")))
    _open_in_browser(tmp_path / "report.html")
    assert "manually" in capsys.readouterr().out


def test_open_in_browser_survives_a_missing_opener_binary(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("run.sys.platform", "linux")

    def raise_not_found(*_a, **_kw):
        raise FileNotFoundError("xdg-open not found")

    monkeypatch.setattr("run.subprocess.run", raise_not_found)
    _open_in_browser(tmp_path / "report.html")  # would raise if uncaught
    assert "manually" in capsys.readouterr().out
