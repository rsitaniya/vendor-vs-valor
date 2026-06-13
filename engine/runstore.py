"""The run directory + artifact manifest (spec §4).

The run dir holds the durable, human-inspectable artifacts (md + json sidecars +
the source cache). ``run.json`` is the artifact-level manifest: per-stage status
+ the recorded input-hash that the skip guard reads. (LangGraph's checkpointer
stores *graph* execution state separately — see graph.py.)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


class StageRecord(BaseModel):
    status: str = "pending"  # pending | done | error
    recorded_hash: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class RunManifest(BaseModel):
    run_id: str
    created_at: str
    model_id: str | None = None
    engine_version: str | None = None
    stages: dict[str, StageRecord] = Field(default_factory=dict)


class RunStore:
    """Bound to one ``runs/<run-id>/`` directory."""

    def __init__(self, run_dir: str | Path):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.dir / "run.json"

    @classmethod
    def new(
        cls,
        runs_root: str | Path = "runs",
        *,
        run_id: str | None = None,
        model_id: str | None = None,
        engine_version: str | None = None,
    ) -> "RunStore":
        run_id = run_id or new_run_id()
        store = cls(Path(runs_root) / run_id)
        if not store.manifest_path.exists():
            store.save(
                RunManifest(
                    run_id=run_id,
                    created_at=_now_iso(),
                    model_id=model_id,
                    engine_version=engine_version,
                )
            )
        return store

    def load(self) -> RunManifest:
        if self.manifest_path.exists():
            return RunManifest.model_validate_json(
                self.manifest_path.read_text(encoding="utf-8")
            )
        return RunManifest(run_id=self.dir.name, created_at=_now_iso())

    def save(self, manifest: RunManifest) -> None:
        self.manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    def get_stage(self, name: str) -> StageRecord | None:
        return self.load().stages.get(name)

    def set_stage(self, name: str, **fields) -> None:
        manifest = self.load()
        record = manifest.stages.get(name) or StageRecord()
        for key, value in fields.items():
            setattr(record, key, value)
        record.updated_at = _now_iso()
        manifest.stages[name] = record
        self.save(manifest)

    # --- artifact helpers ---
    def artifact_path(self, filename: str) -> Path:
        return self.dir / filename

    def write_text(self, filename: str, text: str) -> Path:
        path = self.artifact_path(filename)
        path.write_text(text, encoding="utf-8")
        return path
