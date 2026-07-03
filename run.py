"""Full pipeline runner — reads need from input.md and drives the graph end-to-end.

Usage:
    uv run python run.py [path/to/input.md]   # defaults to ./input.md

Mirrors cp5_demo.py but parameterised: reads the need from a markdown file
(everything after the first # heading is the raw need text), auto-approves all
three human gates, and opens the HTML report on completion.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from langgraph.types import Command

from engine.runstore import RunStore
from graph import RunDeps, build_graph
from llm import get_provider, pro_model

_STAGE_AFTER_GATE = {1: "research", 2: "synthesis", 3: "report"}


def _load_need(path: Path) -> str:
    """Read the markdown file and return the full text as the need string."""
    text = path.read_text(encoding="utf-8").strip()
    # Strip a leading H1 title line (e.g. "# Capability need — …") if present
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def main() -> int:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("input.md")
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
    print(f"model:   flash (research) / pro (synthesis)\n")
    print("driving graph end-to-end (auto-approving gates)...\n")

    result = app.invoke(
        {"run_id": store.dir.name, "run_dir": str(store.dir), "need": need},
        config,
    )
    while result.get("__interrupt__"):
        gate = result["__interrupt__"][0].value
        stage_next = _STAGE_AFTER_GATE.get(gate["gate"], "END")
        print(f"  parked at gate {gate['gate']} ({gate['stage']}) "
              f"-> approve -> {stage_next}")
        result = app.invoke(Command(resume="approve"), config)

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
