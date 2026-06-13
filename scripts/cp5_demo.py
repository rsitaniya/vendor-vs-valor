"""CHECKPOINT 5: a full end-to-end run THROUGH THE GRAPH (intake -> gate1 ->
research -> gate2 -> synthesis+challenger -> gate3 -> report -> END), auto-
approving each human gate, producing the first strategy.md.

Run: uv run python scripts/cp5_demo.py
"""

from __future__ import annotations

import subprocess
import sys

from langgraph.types import Command

from engine.runstore import RunStore
from graph import RunDeps, build_graph
from llm import get_provider, pro_model

NEED = (
    "i need a data to power anomaly detection in indian capital markets. "
    "High quality reliable data tracing over time"
    "Small team (1 cto, 1 CEO/CFO ), cost-conscious - bootstrap, data needs to be complete, reliable and clean at minimal cost "
    "time is of essence, but lesser priority than cost. data quality is unarguably most important"
    "data is not the moat of the project but garabge in garbage out"
)
_STAGE_AFTER_GATE = {1: "research", 2: "synthesis", 3: "report"}


def main() -> int:
    app = build_graph()  # in-memory checkpointer; one process drives to completion
    store = RunStore.new("runs", model_id=pro_model())
    deps = RunDeps(provider=get_provider())  # flash for research, pro for synthesis
    config = {"configurable": {"thread_id": store.dir.name, "deps": deps}}
    print(f"run dir: {store.dir}\ndriving the graph end-to-end (auto-approving gates)...\n")

    result = app.invoke({"run_id": store.dir.name, "run_dir": str(store.dir), "need": NEED}, config)
    while result.get("__interrupt__"):
        gate = result["__interrupt__"][0].value
        print(f"  parked at gate {gate['gate']} ({gate['stage']}) -> approve -> "
              f"{_STAGE_AFTER_GATE.get(gate['gate'], 'END')}")
        result = app.invoke(Command(resume="approve"), config)

    strategy_md = store.artifact_path("strategy.md")
    if not strategy_md.exists():
        print("FAIL: no strategy.md produced")
        return 1

    report_html = store.artifact_path("report.html")

    print("\n" + "=" * 72)
    print(strategy_md.read_text())
    print("=" * 72)
    print(f"\nCP5 PASS: end-to-end run produced {strategy_md}")
    print(f"artifacts: {store.dir}/  (profile, *-research, verify-report, strategy, sources/)")

    if report_html.exists():
        print(f"report:    {report_html}")
        subprocess.run(["open", str(report_html)], check=False)
    else:
        print("note: report.html not produced (report stage may have been skipped)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
