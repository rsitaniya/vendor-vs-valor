"""The LangGraph pipeline skeleton (spec §2).

Four work nodes + three human gates. The gates are *isolated in their own nodes*
that do nothing but ``interrupt()`` — so on resume only the cheap gate node
re-enters, never the expensive work node (the §2 footgun). Work-node bodies are
additionally idempotent via the schema_stage hash guard.

Work-node bodies are stubs here; slices 4–7 fill them with schema_stage calls.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from llm.provider import LLMProvider


class GraphState(TypedDict, total=False):
    run_id: str
    run_dir: str
    need: str
    context: str
    gate1: str  # the operator's decision at each gate (recorded for audit)
    gate2: str
    gate3: str


@dataclass
class RunDeps:
    """Runtime dependencies injected via config['configurable']['deps'].

    Absent => nodes no-op (topology/skeleton mode, used by graph tests).
    """
    provider: LLMProvider | None = None
    model: str | None = None


def _deps(config) -> RunDeps | None:
    return (config or {}).get("configurable", {}).get("deps")


# --- work nodes (idempotent via schema_stage; no-op without deps) ---

def intake_node(state: GraphState, config) -> dict:
    deps = _deps(config)
    if deps is None:
        return {}
    from stages.intake import run_intake

    run_intake(state["need"], state["run_dir"], run_id=state.get("run_id"),
               context=state.get("context", ""), provider=deps.provider, model=deps.model)
    return {}


def research_node(state: GraphState, config) -> dict:
    return {}  # TODO slice 5: research BUILD then BUY -> *-research.{md,json}


def synthesis_node(state: GraphState, config) -> dict:
    return {}  # TODO slice 6: synthesize + challenger -> strategy.{md,json}


def report_node(state: GraphState, config) -> dict:
    return {}  # TODO slice 7: render report.html


# --- gate nodes (isolated interrupts; only these re-enter on resume) ---

def _gate(number: int, stage: str, artifact: str, message: str):
    def gate_node(state: GraphState) -> dict:
        decision = interrupt({"gate": number, "stage": stage, "artifact": artifact,
                              "message": message})
        return {f"gate{number}": decision}
    return gate_node


gate1_node = _gate(1, "intake", "profile.md", "Review the profile; approve or edit.")
gate2_node = _gate(2, "research", "build-research.md / buy-research.md",
                   "Review the research + verify report; approve to synthesize.")
gate3_node = _gate(3, "synthesis", "strategy.md",
                   "Review the strategy; edit the soft steer to re-synthesize, or approve.")

_TOPOLOGY = [
    ("intake", intake_node),
    ("gate1", gate1_node),
    ("research", research_node),
    ("gate2", gate2_node),
    ("synthesis", synthesis_node),
    ("gate3", gate3_node),
    ("report", report_node),
]


def build_graph(checkpointer=None):
    """Compile the pipeline. Defaults to an in-memory checkpointer (tests)."""
    graph = StateGraph(GraphState)
    for node_name, fn in _TOPOLOGY:
        graph.add_node(node_name, fn)
    graph.add_edge(START, _TOPOLOGY[0][0])
    for (a, _), (b, _) in zip(_TOPOLOGY, _TOPOLOGY[1:]):
        graph.add_edge(a, b)
    graph.add_edge(_TOPOLOGY[-1][0], END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def sqlite_checkpointer(db_path: str | Path) -> SqliteSaver:
    """A file-backed checkpointer for cross-process resume (the CLI uses this)."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)
