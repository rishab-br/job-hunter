from langgraph.graph import StateGraph, END

from state import GlobalState, SystemPhase
from .workers.offer_parser import run as parse_offer
from .workers.market_benchmarker import run as benchmark_market
from .workers.clause_risk_analyzer import run as analyze_clauses
from .workers.counteroffer_calculator import run as calculate_counter
from .workers.negotiation_script_gen import run as generate_script
from .workers.response_coach import run as coach_response


def build_subgraph() -> StateGraph:
    """
    Offer Intelligence activates as an event-triggered subgraph
    when an offer arrives (active_offers is non-empty).
    """
    graph = StateGraph(GlobalState)

    graph.add_node("offer_parser", parse_offer)
    graph.add_node("market_benchmarker", benchmark_market)
    graph.add_node("clause_risk_analyzer", analyze_clauses)
    graph.add_node("counteroffer_calculator", calculate_counter)
    graph.add_node("negotiation_script_gen", generate_script)
    graph.add_node("response_coach", coach_response)
    graph.add_node("finalise", _finalise)

    graph.set_entry_point("offer_parser")
    graph.add_edge("offer_parser", "market_benchmarker")
    graph.add_edge("market_benchmarker", "clause_risk_analyzer")
    graph.add_edge("clause_risk_analyzer", "counteroffer_calculator")
    graph.add_edge("counteroffer_calculator", "negotiation_script_gen")
    graph.add_edge("negotiation_script_gen", "response_coach")
    graph.add_edge("response_coach", "finalise")
    graph.add_edge("finalise", END)

    return graph


def _finalise(state: GlobalState) -> GlobalState:
    return {
        **state,
        "current_phase": SystemPhase.IDLE,
        "active_lead": None,
    }
