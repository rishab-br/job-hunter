from langgraph.graph import StateGraph, END

from state import GlobalState, SystemPhase
from .workers.profile_auditor import run as audit_profile
from .workers.project_depth_analyzer import run as analyze_depth
from .workers.trend_scout import run as scout_trends
from .workers.gap_analyzer import run as analyze_gaps
from .workers.improvement_planner import run as plan_improvements


def build_subgraph() -> StateGraph:
    graph = StateGraph(GlobalState)

    graph.add_node("profile_auditor", audit_profile)
    graph.add_node("project_depth_analyzer", analyze_depth)
    graph.add_node("trend_scout", scout_trends)
    graph.add_node("gap_analyzer", analyze_gaps)
    graph.add_node("improvement_planner", plan_improvements)
    graph.add_node("finalise", _finalise)

    graph.set_entry_point("profile_auditor")
    graph.add_edge("profile_auditor", "project_depth_analyzer")
    graph.add_edge("project_depth_analyzer", "trend_scout")
    graph.add_edge("trend_scout", "gap_analyzer")
    graph.add_edge("gap_analyzer", "improvement_planner")
    graph.add_edge("improvement_planner", "finalise")
    graph.add_edge("finalise", END)

    return graph


def _finalise(state: GlobalState) -> GlobalState:
    return {
        **state,
        "current_phase": SystemPhase.JOB_DISCOVERY,
        "active_lead": None,
    }
