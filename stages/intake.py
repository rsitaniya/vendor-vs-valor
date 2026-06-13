"""Stage 1 — intake -> profile.{md,json} (spec §5.1).

Single-pass structuring of a free-text need into a validated Profile. The
LLM-facing schema has no default values (Gemini struct-output is finicky with
defaults) and is required-everywhere; the LLM marks unknowns with explicit
placeholders. A code validator (not the LLM) is the real gate.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

import skills.schema_stage as schema_stage
from agents import load_prompt
from engine.runstore import RunStore
from llm.provider import LLMProvider
from skills.schema_stage import ContractError, OutputContract, StageResult

_INTENT = {"core", "adjacent", "enabling"}
_CUSTOM = {"low", "medium", "high"}


class Need(BaseModel):
    capability: str
    business_context: str
    problem: str


class Intent(BaseModel):
    core_value_proximity: Literal["core", "adjacent", "enabling"]
    rationale: str


class Resources(BaseModel):
    eng_headcount: int
    relevant_skills: list[str]
    budget_note: str
    runway_note: str


class Constraints(BaseModel):
    compliance: list[str]
    data_sensitivity: str
    existing_stack: list[str]
    timeline_hard_stop: str


class Profile(BaseModel):
    run_id: str
    need: Need
    intent: Intent
    resources: Resources
    constraints: Constraints
    customization_need: Literal["low", "medium", "high"]
    soft_steer: str


def validate_profile(data: dict) -> None:
    """Code validation (not the LLM): required need fields, enums, soft steer."""
    need = data.get("need") or {}
    for field in ("capability", "business_context", "problem"):
        if not str(need.get(field, "")).strip():
            raise ContractError(f"profile.need.{field} is empty")
    if (data.get("intent") or {}).get("core_value_proximity") not in _INTENT:
        raise ContractError("profile.intent.core_value_proximity is invalid")
    if data.get("customization_need") not in _CUSTOM:
        raise ContractError("profile.customization_need is invalid")
    if not str(data.get("soft_steer", "")).strip():
        raise ContractError("profile.soft_steer is empty")


def render_profile_md(data: dict) -> str:
    need, intent = data["need"], data["intent"]
    res, con = data["resources"], data["constraints"]
    return "\n".join([
        f"# Need profile — {data.get('run_id', '')}",
        "",
        "## Need",
        f"- **Capability:** {need['capability']}",
        f"- **Business context:** {need['business_context']}",
        f"- **Problem:** {need['problem']}",
        "",
        "## Intent",
        f"- **Core-value proximity:** {intent['core_value_proximity']}",
        f"- **Rationale:** {intent['rationale']}",
        "",
        "## Resources",
        f"- **Eng headcount:** {res['eng_headcount']}",
        f"- **Relevant skills:** {', '.join(res['relevant_skills']) or '(none)'}",
        f"- **Budget:** {res['budget_note']}",
        f"- **Runway:** {res['runway_note']}",
        "",
        "## Constraints",
        f"- **Compliance:** {', '.join(con['compliance']) or '(none stated)'}",
        f"- **Data sensitivity:** {con['data_sensitivity']}",
        f"- **Existing stack:** {', '.join(con['existing_stack']) or '(none stated)'}",
        f"- **Timeline hard stop:** {con['timeline_hard_stop']}",
        "",
        "## Customization & steer",
        f"- **Customization need:** {data['customization_need']}",
        f"- **Soft steer:** {data['soft_steer']}",
        "",
    ])


def run_intake(
    need: str,
    run_dir: str,
    *,
    run_id: str | None = None,
    context: str = "",
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> StageResult:
    """Structure a free-text need into a validated profile.{md,json}."""
    store = RunStore(run_dir)
    run_id = run_id or store.load().run_id
    store.write_text(
        "need.md",
        f"# Capability need\n\n{need}\n\n## Additional context\n"
        f"{context or '(none provided)'}\n\nrun_id: {run_id}\n",
    )
    return schema_stage.run(
        "intake",
        name="profile",
        run_dir=run_dir,
        prompt=load_prompt("intake"),
        output_contract=OutputContract(
            response_schema=Profile,
            required_fields=("need", "intent", "soft_steer"),
            validate=validate_profile,
        ),
        render=render_profile_md,
        inputs=("need.md",),
        provider=provider,
        model=model,
    )
