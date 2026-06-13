"""RunStore manifest and artifact helpers."""

from __future__ import annotations

from engine.runstore import RunStore


def test_new_store_creates_manifest_with_metadata(tmp_path):
    store = RunStore.new(
        tmp_path,
        run_id="run-1",
        model_id="model-x",
        engine_version="v1",
    )

    manifest = store.load()

    assert manifest.run_id == "run-1"
    assert manifest.model_id == "model-x"
    assert manifest.engine_version == "v1"
    assert store.manifest_path.exists()


def test_set_stage_updates_manifest_record(tmp_path):
    store = RunStore.new(tmp_path, run_id="run-1")

    store.set_stage("demo", status="done", recorded_hash="abc", artifacts=["demo.json"])
    record = store.get_stage("demo")

    assert record.status == "done"
    assert record.recorded_hash == "abc"
    assert record.artifacts == ["demo.json"]
    assert record.updated_at is not None


def test_write_text_returns_artifact_path(tmp_path):
    store = RunStore(tmp_path)

    path = store.write_text("artifact.md", "# hello")

    assert path == store.artifact_path("artifact.md")
    assert path.read_text(encoding="utf-8") == "# hello"
