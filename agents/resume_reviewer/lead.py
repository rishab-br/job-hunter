from langgraph.graph import StateGraph, END

from state import GlobalState, SystemPhase
from .workers.resume_reviewer import run as review_resume


def build_subgraph() -> StateGraph:
    graph = StateGraph(GlobalState)

    graph.add_node("resume_reviewer", review_resume)
    graph.add_node("finalise", _finalise)

    graph.set_entry_point("resume_reviewer")
    graph.add_edge("resume_reviewer", "finalise")
    graph.add_edge("finalise", END)

    return graph


def _finalise(state: GlobalState) -> GlobalState:
    return {**state, "current_phase": SystemPhase.RESUME_REVIEW, "active_lead": None}
