"""Slice 4: intake structures a need into a validated profile (case-agnostic)."""

from __future__ import annotations

import json

import pytest

from skills.schema_stage import ContractError
from stages.intake import Profile, run_intake, validate_profile

# A profile for an arbitrary, non-hardcoded domain (proves case-agnosticism).
SAMPLE = Profile(
    run_id="r1",
    need={"capability": "internal document parser", "business_context": "ops team",
          "problem": "manual data entry is slow"},
    intent={"core_value_proximity": "enabling", "rationale": "plumbing, not the moat"},
    resources={"eng_headcount": 3, "relevant_skills": ["python"], "budget_note": "modest",
               "runway_note": "not specified", "expected_scale": "not specified",
               "procurement_process": "not specified"},
    constraints={"compliance": [], "data_sensitivity": "internal only",
                 "data_residency": "not specified", "required_certifications": [],
                 "existing_stack": ["postgres"], "integration_requirements": [],
                 "timeline_hard_stop": "not specified"},
    customization_need="medium",
    soft_steer="reliability matters more than upfront cost",
    reversibility_criteria="not specified",
    portfolio_note="not specified",
)


class ProfileProvider:
    def __init__(self, profile=SAMPLE):
        self.profile = profile

    def complete(self, prompt, *, response_schema=None, model=None):
        return self.profile


def test_run_intake_produces_valid_profile_artifacts(tmp_path):
    result = run_intake("Need a document parser", tmp_path, run_id="r1",
                        provider=ProfileProvider(), model="m1")
    assert not result.skipped
    data = json.loads(result.json_path.read_text())
    assert data["need"]["capability"] == "internal document parser"
    assert data["soft_steer"]
    assert "document parser" in result.md_path.read_text()
    # need.md was written as the stage input
    assert (tmp_path / "need.md").exists()


def test_intake_is_idempotent_via_hash_guard(tmp_path):
    prov = ProfileProvider()
    run_intake("x", tmp_path, run_id="r1", provider=prov, model="m1")
    second = run_intake("x", tmp_path, run_id="r1", provider=prov, model="m1")
    assert second.skipped


def test_validate_profile_rejects_empty_need_field():
    bad = SAMPLE.model_dump()
    bad["need"]["capability"] = "  "
    with pytest.raises(ContractError, match="need.capability"):
        validate_profile(bad)


def test_validate_profile_rejects_bad_enum_and_empty_steer():
    bad = SAMPLE.model_dump()
    bad["customization_need"] = "extreme"
    with pytest.raises(ContractError, match="customization_need"):
        validate_profile(bad)
    bad2 = SAMPLE.model_dump()
    bad2["soft_steer"] = ""
    with pytest.raises(ContractError, match="soft_steer"):
        validate_profile(bad2)


def test_validate_profile_rejects_empty_reversibility_and_portfolio_note():
    bad = SAMPLE.model_dump()
    bad["reversibility_criteria"] = ""
    with pytest.raises(ContractError, match="reversibility_criteria"):
        validate_profile(bad)
    bad2 = SAMPLE.model_dump()
    bad2["portfolio_note"] = "  "
    with pytest.raises(ContractError, match="portfolio_note"):
        validate_profile(bad2)


def test_intake_runs_inside_graph_and_parks_at_gate1(tmp_path):
    from graph import RunDeps, build_graph

    app = build_graph()
    config = {"configurable": {"thread_id": "g1", "deps": RunDeps(provider=ProfileProvider(),
                                                                  model="m1")}}
    result = app.invoke({"run_id": "r1", "run_dir": str(tmp_path), "need": "Need a parser"}, config)
    assert result.get("__interrupt__"), "should park at gate 1 after intake"
    assert (tmp_path / "profile.json").exists()  # the node really produced the artifact
    # (resume/gate mechanics are covered in test_graph.py; research needs its own mocks)
