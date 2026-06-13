"""CHECKPOINT 2 (part 1): the schema_stage hash guard skips/re-runs correctly."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

import skills.schema_stage as schema_stage
from engine.runstore import RunStore
from skills.schema_stage import ContractError, OutputContract


class Out(BaseModel):
    value: str


class CountingProvider:
    """Counts LLM calls so we can prove a skipped stage makes none."""

    def __init__(self, value: str = "out"):
        self.calls = 0
        self.value = value

    def complete(self, prompt, *, response_schema=None, model=None):
        self.calls += 1
        return response_schema(value=self.value)


def _run(tmp_path, provider, *, prompt="P", model="m1"):
    return schema_stage.run(
        "demo",
        run_dir=tmp_path,
        prompt=prompt,
        output_contract=OutputContract(response_schema=Out, required_fields=("value",)),
        render=lambda d: f"# {d['value']}",
        inputs=("in.txt",),
        provider=provider,
        model=model,
    )


def test_first_run_calls_llm_and_persists_artifacts(tmp_path):
    RunStore(tmp_path).write_text("in.txt", "hello")
    prov = CountingProvider()
    result = _run(tmp_path, prov)
    assert not result.skipped and prov.calls == 1
    assert result.json_path.exists() and result.md_path.exists()
    assert result.md_path.read_text() == "# out"
    # manifest recorded the stage as done with the input hash
    rec = RunStore(tmp_path).get_stage("demo")
    assert rec.status == "done" and rec.recorded_hash == result.input_hash


def test_unchanged_inputs_skip_without_calling_llm(tmp_path):
    RunStore(tmp_path).write_text("in.txt", "hello")
    prov = CountingProvider()
    _run(tmp_path, prov)
    second = _run(tmp_path, prov)
    assert second.skipped and prov.calls == 1  # no second LLM call


def test_changing_an_input_invalidates_and_reruns(tmp_path):
    store = RunStore(tmp_path)
    store.write_text("in.txt", "hello")
    prov = CountingProvider()
    _run(tmp_path, prov)
    store.write_text("in.txt", "world")  # edit upstream artifact
    third = _run(tmp_path, prov)
    assert not third.skipped and prov.calls == 2


def test_changing_prompt_or_model_invalidates(tmp_path):
    RunStore(tmp_path).write_text("in.txt", "hello")
    prov = CountingProvider()
    _run(tmp_path, prov)
    _run(tmp_path, prov, prompt="DIFFERENT")  # prompt is part of the hash
    assert prov.calls == 2
    _run(tmp_path, prov, model="m2")  # model is part of the hash
    assert prov.calls == 3


def test_contract_violation_fails_loudly(tmp_path):
    RunStore(tmp_path).write_text("in.txt", "hello")

    class Empty(BaseModel):
        value: str = ""

    class EmptyProvider:
        def complete(self, prompt, *, response_schema=None, model=None):
            return Empty()

    with pytest.raises(ContractError, match="value"):
        schema_stage.run(
            "demo", run_dir=tmp_path, prompt="P",
            output_contract=OutputContract(response_schema=Empty, required_fields=("value",)),
            render=lambda d: "x", provider=EmptyProvider(), model="m1",
        )
