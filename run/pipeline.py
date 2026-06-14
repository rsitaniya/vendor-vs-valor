"""File-driven terminal runner for the full Vendor vs Valor pipeline."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from langgraph.types import Command

from engine.runstore import RunStore
from graph import RunDeps, build_graph, graph_flow_text
from llm import get_provider, pro_model

_STAGE_AFTER_GATE = {1: "research", 2: "synthesis", 3: "report"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_root_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return repo_root() / path


def read_input_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"input file does not exist: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"input file is empty: {path}")
    return text


def refresh_latest_run(run_dir: Path, latest_dir: Path) -> None:
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(run_dir, latest_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Vendor vs Valor LangGraph pipeline from a user input file.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the user-authored input file, resolved from repo root when relative.",
    )
    parser.add_argument(
        "--runs-root",
        default="runs",
        help="Archive root for timestamped run directories. Defaults to repo-root runs/.",
    )
    parser.add_argument(
        "--latest-dir",
        default="latest_run",
        help="Stable output directory refreshed after each successful run.",
    )
    return parser


def run_pipeline(args: argparse.Namespace) -> int:
    root = repo_root()
    input_path = resolve_root_path(args.input)
    runs_root = resolve_root_path(args.runs_root)
    latest_dir = resolve_root_path(args.latest_dir)
    input_text = read_input_file(input_path)

    print("LangGraph flow:")
    print(graph_flow_text())
    print()

    app = build_graph()
    store = RunStore.new(runs_root, model_id=pro_model())
    deps = RunDeps(provider=get_provider())
    config = {"configurable": {"thread_id": store.dir.name, "deps": deps}}

    print(f"repo root:  {root}")
    print(f"input:      {input_path}")
    print(f"run dir:    {store.dir}")
    print(f"latest dir: {latest_dir}")
    print("driving the graph end-to-end (auto-approving gates)...\n")

    result = app.invoke(
        {
            "run_id": store.dir.name,
            "run_dir": str(store.dir),
            "input": input_text,
        },
        config,
    )
    while result.get("__interrupt__"):
        gate = result["__interrupt__"][0].value
        print(
            f"  parked at gate {gate['gate']} ({gate['stage']}) -> approve -> "
            f"{_STAGE_AFTER_GATE.get(gate['gate'], 'END')}"
        )
        result = app.invoke(Command(resume="approve"), config)

    strategy_md = store.artifact_path("strategy.md")
    report_html = store.artifact_path("report.html")
    if not strategy_md.exists():
        print("FAIL: no strategy.md produced")
        return 1
    if not report_html.exists():
        print("FAIL: no report.html produced")
        return 1

    refresh_latest_run(store.dir, latest_dir)

    print("\n" + "=" * 72)
    print(strategy_md.read_text(encoding="utf-8"))
    print("=" * 72)
    print(f"\nPASS: archival output saved to {store.dir}")
    print(f"PASS: latest output refreshed at {latest_dir}")
    print(f"report: {latest_dir / 'report.html'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_pipeline(args)
    except Exception as exc:  # noqa: BLE001 - terminal runner should print clean failures
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
