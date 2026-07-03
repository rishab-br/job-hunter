from langgraph.graph import StateGraph, END
from state import GlobalState
from .workers.cover_letter import run as _run


def build_subgraph() -> StateGraph:
    graph = StateGraph(GlobalState)
    graph.add_node("cover_letter", _run)
    graph.set_entry_point("cover_letter")
    graph.add_edge("cover_letter", END)
    return graph
