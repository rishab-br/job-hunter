from langgraph.graph import StateGraph, END
from state import GlobalState
from .workers.ats_modifier import run as _run


def build_subgraph() -> StateGraph:
    graph = StateGraph(GlobalState)
    graph.add_node("ats_modifier", _run)
    graph.set_entry_point("ats_modifier")
    graph.add_edge("ats_modifier", END)
    return graph
