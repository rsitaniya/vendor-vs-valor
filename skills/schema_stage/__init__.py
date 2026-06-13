"""schema_stage — the stage lifecycle wrapper (spec §3.2).

Every stage repeats the same four steps; this skill does them once:
load inputs -> call LLM with prompt -> validate against the output_contract ->
persist (.json + generated .md) + update run.json. Layered on top is the
input-hash skip guard (engine.hashing), which makes every node body idempotent.

`output_contract` validates *structural presence + grounding*, not numbers
(the qualitative world): required fields present/non-empty + an optional custom
check. Render direction differs by stage (json-truth vs md-truth) and is the
caller's `render`/`response_schema` choice.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from engine.hashing import stage_input_hash
from engine.runstore import RunStore
from llm import flash_model, get_provider
from llm.provider import LLMProvider


class ContractError(ValueError):
    """Raised when a stage's output fails its output_contract (fail loudly)."""


@dataclass
class OutputContract:
    #: Pydantic model for structured output. None => prose stage (md is truth).
    response_schema: type[BaseModel] | None = None
    #: Fields that must be present and non-empty in the produced data.
    required_fields: tuple[str, ...] = ()
    #: Optional extra check; should raise ContractError on failure.
    validate: Callable[[dict], None] | None = None


@dataclass
class StageResult:
    name: str
    skipped: bool
    data: dict
    json_path: Path
    md_path: Path
    input_hash: str


def _assemble_context(prompt: str, input_paths: list[Path]) -> str:
    parts = [prompt]
    for path in input_paths:
        parts.append(f"\n\n--- input: {path.name} ---\n{path.read_text(encoding='utf-8')}")
    return "".join(parts)


def _check_contract(data: dict, contract: OutputContract) -> None:
    errors = [
        f"missing/empty required field: {name}"
        for name in contract.required_fields
        if data.get(name) in (None, "", [], {})
    ]
    if errors:
        raise ContractError("; ".join(errors))
    if contract.validate is not None:
        contract.validate(data)


def run(
    stage_name: str,
    *,
    run_dir: str | Path,
    prompt: str,
    output_contract: OutputContract,
    render: Callable[[dict], str],
    inputs: tuple[str, ...] = (),
    name: str | None = None,
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> StageResult:
    """Run one stage (or skip it if its inputs are unchanged)."""
    name = name or stage_name
    store = RunStore(run_dir)
    model = model or flash_model()
    engine_version = os.environ.get("ENGINE_VERSION", "0")

    input_paths = [store.artifact_path(f) for f in inputs]
    current_hash = stage_input_hash(
        input_paths=input_paths, prompt=prompt, model_id=model, engine_version=engine_version
    )
    json_path = store.artifact_path(f"{name}.json")
    md_path = store.artifact_path(f"{name}.md")

    # --- skip guard: reuse the artifact iff done + hash matches (spec §4) ---
    record = store.get_stage(name)
    if record and record.status == "done" and record.recorded_hash == current_hash and json_path.exists():
        return StageResult(
            name=name, skipped=True, input_hash=current_hash,
            data=json.loads(json_path.read_text(encoding="utf-8")),
            json_path=json_path, md_path=md_path,
        )

    # --- run: load -> LLM -> validate -> persist ---
    provider = provider or get_provider()
    context = _assemble_context(prompt, input_paths)
    if output_contract.response_schema is not None:
        parsed = provider.complete(context, response_schema=output_contract.response_schema, model=model)
        data = parsed.model_dump()
    else:
        data = {"text": provider.complete(context, model=model)}

    _check_contract(data, output_contract)

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render(data), encoding="utf-8")
    store.set_stage(name, status="done", recorded_hash=current_hash,
                    artifacts=[json_path.name, md_path.name])

    return StageResult(
        name=name, skipped=False, input_hash=current_hash, data=data,
        json_path=json_path, md_path=md_path,
    )
