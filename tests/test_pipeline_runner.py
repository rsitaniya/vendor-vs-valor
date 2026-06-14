from pathlib import Path

from graph import graph_flow_lines
from run.pipeline import read_input_file, refresh_latest_run


def test_graph_flow_is_sourced_from_graph_edges():
    lines = graph_flow_lines()

    assert "START -> intake" in lines
    assert "gate1 -> research_build" in lines
    assert "gate1 -> research_buy" in lines
    assert "research_build + research_buy -> research_join" in lines
    assert "report -> END" in lines


def test_refresh_latest_run_replaces_previous_output(tmp_path: Path):
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "strategy.md").write_text("new strategy", encoding="utf-8")
    (run_dir / "nested").mkdir()
    (run_dir / "nested" / "report.html").write_text("<html></html>", encoding="utf-8")

    latest = tmp_path / "latest_run"
    latest.mkdir()
    (latest / "stale.txt").write_text("stale", encoding="utf-8")

    refresh_latest_run(run_dir, latest)

    assert not (latest / "stale.txt").exists()
    assert (latest / "strategy.md").read_text(encoding="utf-8") == "new strategy"
    assert (latest / "nested" / "report.html").exists()


def test_read_input_file_rejects_empty_input(tmp_path: Path):
    input_file = tmp_path / "input.md"
    input_file.write_text("  \n", encoding="utf-8")

    try:
        read_input_file(input_file)
    except ValueError as exc:
        assert "input file is empty" in str(exc)
    else:
        raise AssertionError("empty input file should fail")
