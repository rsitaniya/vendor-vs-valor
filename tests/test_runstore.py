"""RunStore manifest and artifact helpers."""

from __future__ import annotations

import threading

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


def test_set_stage_survives_concurrent_writers(tmp_path, monkeypatch):
    # BUILD/BUY research run as parallel LangGraph branches (separate threads)
    # and both call set_stage() on the same run.json. Widen the read-modify-
    # write window artificially so a missing lock would reliably lose updates.
    store = RunStore.new(tmp_path, run_id="run-1")
    original_load = RunStore.load

    def slow_load(self):
        manifest = original_load(self)
        import time
        time.sleep(0.01)
        return manifest

    monkeypatch.setattr(RunStore, "load", slow_load)

    stage_names = [f"stage-{i}" for i in range(8)]
    threads = [
        threading.Thread(target=store.set_stage, args=(name,), kwargs={"status": "done"})
        for name in stage_names
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    manifest = original_load(store)
    assert set(manifest.stages) == set(stage_names)
