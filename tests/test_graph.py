"""CHECKPOINT 2 (part 2): the graph parks at each gate and resumes."""

from __future__ import annotations

from langgraph.types import Command

from graph import _EDGES, _NODES, build_graph


def test_graph_declares_expected_topology():
    assert [name for name, _ in _NODES] == [
        "intake",
        "gate1",
        "research_build",
        "research_buy",
        "research_join",
        "gate2",
        "synthesis",
        "gate3",
        "report",
    ]
    assert ("gate1", "research_build") in _EDGES
    assert ("gate1", "research_buy") in _EDGES
    assert (["research_build", "research_buy"], "research_join") in _EDGES


def _config(thread="t1"):
    return {"configurable": {"thread_id": thread}}


def test_graph_parks_at_gate1_and_resumes_through_all_gates():
    app = build_graph()  # in-memory checkpointer
    config = _config()

    # First invoke runs intake (stub) then parks at gate 1.
    result = app.invoke({"run_id": "r1", "run_dir": "/tmp/r1"}, config)
    assert result.get("__interrupt__"), "expected to park at gate 1"

    # Resume past each gate; the graph parks at the next one.
    result = app.invoke(Command(resume="approve"), config)
    assert result.get("__interrupt__"), "expected to park at gate 2"
    result = app.invoke(Command(resume="approve"), config)
    assert result.get("__interrupt__"), "expected to park at gate 3"

    # Final resume runs report and reaches END.
    result = app.invoke(Command(resume="approve"), config)
    assert not result.get("__interrupt__"), "expected to finish"
    assert app.get_state(config).next == ()


def test_gate_decisions_are_recorded_in_state():
    app = build_graph()
    config = _config("t2")
    app.invoke({"run_id": "r2", "run_dir": "/tmp/r2"}, config)
    app.invoke(Command(resume="approve"), config)
    app.invoke(Command(resume="edit"), config)
    app.invoke(Command(resume="approve"), config)
    values = app.get_state(config).values
    assert values["gate1"] == "approve"
    assert values["gate2"] == "edit"
    assert values["gate3"] == "approve"


def test_editing_at_gate3_loops_back_to_synthesis_then_reparks():
    app = build_graph()
    config = _config("t3")
    app.invoke({"run_id": "r3", "run_dir": "/tmp/r3"}, config)
    app.invoke(Command(resume="approve"), config)  # past gate 1
    app.invoke(Command(resume="approve"), config)  # past gate 2, through synthesis, parks at gate 3

    result = app.invoke(Command(resume="edit"), config)  # loops back through synthesis
    assert result.get("__interrupt__"), "expected to re-park at gate 3 after re-synthesis"
    assert app.get_state(config).values["gate3"] == "edit"

    result = app.invoke(Command(resume="approve"), config)  # this time proceed to report
    assert not result.get("__interrupt__"), "expected to finish"
    assert app.get_state(config).next == ()


def test_resume_does_not_replay_gate_decision_already_made():
    # Two independent threads keep independent checkpoints.
    app = build_graph()
    app.invoke({"run_id": "a", "run_dir": "/tmp/a"}, _config("A"))
    app.invoke({"run_id": "b", "run_dir": "/tmp/b"}, _config("B"))
    app.invoke(Command(resume="approve"), _config("A"))
    assert app.get_state(_config("A")).values["gate1"] == "approve"
    assert "gate1" not in app.get_state(_config("B")).values  # B still parked at gate 1
