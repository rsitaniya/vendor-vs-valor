"""Full pipeline runner — reads need from a markdown file and drives the graph
end-to-end, pausing for real human review at each gate by default.

Usage:
    uv run python run.py [path/to/need.md]                # interactive (default)
    uv run python run.py [path/to/need.md] --auto-approve  # unattended, old behavior

Gate 1 (profile): one clarification round for fields that still look unfilled
and matter to research quality, then approve, edit profile.json in $EDITOR, or
abort.
Gate 2 (research): approve or abort — no sanctioned edit path (spec §5.2).
Gate 3 (strategy): approve, edit the soft steer (re-runs synthesis), or abort.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from langgraph.types import Command

from engine.runstore import RunStore
from graph import RunDeps, build_graph
from llm import get_provider, pro_model
from skills.schema_stage import ContractError
from stages.intake import render_profile_md, validate_profile

_STAGE_AFTER_GATE = {1: "research", 2: "synthesis", 3: "report"}

# Fields that materially affect research quality but often land on a placeholder
# after intake's single-pass extraction. One round, capped, not an open interview.
_CLARIFY_FIELDS = [
    ("constraints", "compliance", "Compliance regimes that apply (comma-separated, or 'none')"),
    ("constraints", "data_sensitivity", "Data sensitivity"),
    ("constraints", "data_residency", "Data residency requirements"),
    ("resources", "budget_note", "Budget"),
    ("resources", "expected_scale", "Expected scale (users/requests/data volume)"),
    ("constraints", "timeline_hard_stop", "Timeline hard stop"),
]
_MAX_CLARIFICATIONS = 3
_PLACEHOLDER_STRINGS = {"", "not specified", "none", "none stated", "n/a", "unknown"}


def _load_need(path: Path) -> str:
    """Read the markdown file and return the full text as the need string."""
    text = path.read_text(encoding="utf-8").strip()
    # Strip a leading H1 title line (e.g. "# Capability need — …") if present
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def load_and_validate_profile(path: Path) -> dict | None:
    """Read profile.json and validate it. Returns the data, or None on error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_profile(data)
    except (json.JSONDecodeError, ContractError) as exc:
        print(f"  profile.json is invalid: {exc}")
        return None
    return data


def apply_soft_steer(store: RunStore, new_steer: str) -> None:
    """Update profile.json's soft_steer and regenerate profile.md from it."""
    path = store.artifact_path("profile.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["soft_steer"] = new_steer
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    store.artifact_path("profile.md").write_text(render_profile_md(data), encoding="utf-8")


def _is_gap(value: object) -> bool:
    if isinstance(value, list):
        return len(value) == 0
    return str(value).strip().lower() in _PLACEHOLDER_STRINGS


def find_profile_gaps(data: dict) -> list[tuple[str, str, str]]:
    """Up to _MAX_CLARIFICATIONS (section, field, prompt) fields still on a
    placeholder value after intake's first pass."""
    gaps = []
    for section, field, prompt in _CLARIFY_FIELDS:
        if _is_gap(data.get(section, {}).get(field)):
            gaps.append((section, field, prompt))
        if len(gaps) >= _MAX_CLARIFICATIONS:
            break
    return gaps


def apply_clarifications(store: RunStore, answers: dict[tuple[str, str], str]) -> None:
    """Patch profile.json with clarification answers and regenerate profile.md."""
    path = store.artifact_path("profile.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    for (section, field), answer in answers.items():
        target = data.setdefault(section, {})
        if isinstance(target.get(field), list):
            target[field] = [item.strip() for item in answer.split(",") if item.strip()]
        else:
            target[field] = answer
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    store.artifact_path("profile.md").write_text(render_profile_md(data), encoding="utf-8")


def clarify_profile(store: RunStore) -> None:
    """One clarification round: ask about fields find_profile_gaps flags, skip
    if the profile is already complete."""
    data = json.loads(store.artifact_path("profile.json").read_text(encoding="utf-8"))
    gaps = find_profile_gaps(data)
    if not gaps:
        return
    print("\n  a few fields still look unfilled — one quick round before research runs:")
    answers: dict[tuple[str, str], str] = {}
    for section, field, prompt in gaps:
        answer = input(f"  {prompt} (blank to leave as-is): ").strip()
        if answer:
            answers[(section, field)] = answer
    if answers:
        apply_clarifications(store, answers)
        print("  profile updated.")


def _open_editor(path: Path) -> None:
    editor = os.environ.get("EDITOR", "vi")
    subprocess.run([editor, str(path)], check=False)


def _edit_profile(store: RunStore) -> bool:
    """Open profile.json in $EDITOR, validate, regenerate profile.md."""
    path = store.artifact_path("profile.json")
    _open_editor(path)
    data = load_and_validate_profile(path)
    if data is None:
        return False
    store.artifact_path("profile.md").write_text(render_profile_md(data), encoding="utf-8")
    return True


def _edit_soft_steer(store: RunStore) -> None:
    path = store.artifact_path("profile.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"  current soft steer: {data.get('soft_steer', '')}")
    new_steer = input("  new soft steer (blank to keep current): ").strip()
    if new_steer:
        apply_soft_steer(store, new_steer)


def prompt_gate(gate: dict, store: RunStore) -> str:
    """Block for real human review. Returns the resume decision ('approve' or
    'edit'), or exits the process on abort."""
    number, stage, artifact, message = gate["gate"], gate["stage"], gate["artifact"], gate["message"]
    if number == 1:
        clarify_profile(store)
    print(f"\n  gate {number} ({stage}): {message}")
    print(f"  artifact: {store.dir / artifact}")
    can_edit = number in (1, 3)
    while True:
        options = "[a]pprove" + (", [e]dit" if can_edit else "") + ", a[b]ort"
        choice = input(f"  {options}: ").strip().lower()
        if choice in ("a", "approve"):
            return "approve"
        if choice in ("b", "abort"):
            print("  aborted. This run cannot be resumed after this process exits "
                  "(in-memory checkpointer).")
            raise SystemExit(1)
        if can_edit and choice in ("e", "edit"):
            if number == 1:
                if _edit_profile(store):
                    print("  profile.json updated and re-validated.")
            else:  # gate 3
                _edit_soft_steer(store)
            return "edit"
        print("  unrecognized choice.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="input-market-data-india.md")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Skip human review; auto-approve every gate (old unattended behavior).")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 2

    need = _load_need(input_path)
    print(f"input:   {input_path} ({len(need)} chars)")

    app = build_graph()
    store = RunStore.new("runs", model_id=pro_model())
    deps = RunDeps(provider=get_provider())
    config = {"configurable": {"thread_id": store.dir.name, "deps": deps}}
    print(f"run dir: {store.dir}")
    print(f"model:   flash (research) / pro (synthesis)")
    print("auto-approving every gate (unattended)\n" if args.auto_approve
          else "interactive mode: reviewing at each gate\n")

    result = app.invoke(
        {"run_id": store.dir.name, "run_dir": str(store.dir), "need": need},
        config,
    )
    while result.get("__interrupt__"):
        gate = result["__interrupt__"][0].value
        if args.auto_approve:
            decision = "approve"
            stage_next = _STAGE_AFTER_GATE.get(gate["gate"], "END")
            print(f"  parked at gate {gate['gate']} ({gate['stage']}) "
                  f"-> approve -> {stage_next}")
        else:
            decision = prompt_gate(gate, store)
        result = app.invoke(Command(resume=decision), config)

    strategy_md = store.artifact_path("strategy.md")
    if not strategy_md.exists():
        print("\nFAIL: no strategy.md produced — check run artifacts above.")
        return 1

    report_html = store.artifact_path("report.html")

    print("\n" + "=" * 72)
    print(strategy_md.read_text(encoding="utf-8"))
    print("=" * 72)

    print(f"\nPASS: full run complete.")
    print(f"  run dir:  {store.dir}/")
    print(f"  strategy: {strategy_md}")
    if report_html.exists():
        print(f"  report:   {report_html}")
        subprocess.run(["open", str(report_html)], check=False)
    else:
        print("  note: report.html not produced (report stage may have been skipped)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
