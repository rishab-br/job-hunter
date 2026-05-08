from langgraph.graph import StateGraph, END

from state import GlobalState, SystemPhase
from .workers.application_monitor import run as monitor_applications
from .workers.followup_scheduler import run as schedule_followups
from .workers.ghosted_detector import run as detect_ghosted
from .workers.pipeline_reporter import run as report_pipeline


def build_subgraph() -> StateGraph:
    """
    Status Tracker runs as a subgraph in the main pipeline (once after applications
    are submitted) and can also be invoked standalone for periodic status checks.
    """
    graph = StateGraph(GlobalState)

    graph.add_node("application_monitor", monitor_applications)
    graph.add_node("followup_scheduler", schedule_followups)
    graph.add_node("ghosted_detector", detect_ghosted)
    graph.add_node("pipeline_reporter", report_pipeline)
    graph.add_node("finalise", _finalise)

    graph.set_entry_point("application_monitor")
    graph.add_edge("application_monitor", "followup_scheduler")
    graph.add_edge("followup_scheduler", "ghosted_detector")
    graph.add_edge("ghosted_detector", "pipeline_reporter")
    graph.add_edge("pipeline_reporter", "finalise")
    graph.add_edge("finalise", END)

    return graph


def _finalise(state: GlobalState) -> GlobalState:
    # Only advance to Offer Evaluation if there are unprocessed active offers
    active_offers = state.get("active_offers") or []
    existing_evals = state.get("offer_evaluations") or []
    evaluated_ids = {e["offer_id"] for e in existing_evals}
    has_new_offers = any(
        o.get("offer_id") not in evaluated_ids for o in active_offers
    )

    next_phase = SystemPhase.OFFER_EVALUATION if has_new_offers else SystemPhase.IDLE

    return {
        **state,
        "current_phase": next_phase,
        "active_lead": None,
    }
