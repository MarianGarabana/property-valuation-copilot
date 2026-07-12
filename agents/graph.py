import operator
import sys
from pathlib import Path
from typing import Annotated, Optional, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from langgraph.graph import END, START, StateGraph

from agents import comparables_agent, energy_agent, narrative_agent, valuation_agent
from agents.data import get_subject


class CopilotState(TypedDict, total=False):
    subject: dict
    comps: Optional[dict]
    valuation: Optional[dict]
    energy: Optional[dict]
    narrative: Optional[str]
    narrative_source: Optional[str]
    narrative_facts: Optional[str]
    errors: Annotated[list, operator.add]


def _tool_node(name, agent_run, key):
    def node(state):
        try:
            return {key: agent_run(state["subject"])}
        except Exception as exc:
            return {key: None, "errors": [f"{name}: {exc}"]}

    return node


def _narrative_node(state):
    text, source, notes, facts_text = narrative_agent.write_narrative(
        state["subject"],
        state.get("valuation"),
        state.get("comps"),
        state.get("energy"),
    )
    out = {
        "narrative": text,
        "narrative_source": source,
        "narrative_facts": facts_text,
    }
    if notes:
        out["errors"] = notes
    return out


def build_graph():
    graph = StateGraph(CopilotState)
    graph.add_node("comparables", _tool_node("comparables_agent", comparables_agent.run, "comps"))
    graph.add_node("valuation", _tool_node("valuation_agent", valuation_agent.run, "valuation"))
    graph.add_node("energy", _tool_node("energy_agent", energy_agent.run, "energy"))
    graph.add_node("narrative", _narrative_node)
    for name in ("comparables", "valuation", "energy"):
        graph.add_edge(START, name)
        graph.add_edge(name, "narrative")
    graph.add_edge("narrative", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_copilot(subject):
    if isinstance(subject, str):
        subject = get_subject(subject)
    return get_graph().invoke({"subject": subject, "errors": []})
