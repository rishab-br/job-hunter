"""
Master Orchestrator — wires all Lead Agent subgraphs into a single
stateful LangGraph pipeline. Supports full-pipeline runs, module-specific
runs, interrupt/resume at the human approval gate, and offer injection.
"""
import uuid
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from state import GlobalState, SystemPhase, initial_state
from agents.github_intelligence import build_subgraph as _github_sg
from agents.job_discovery import build_subgraph as _job_discovery_sg
from agents.application_engine import build_subgraph as _application_engine_sg
from agents.status_tracker import build_subgraph as _status_tracker_sg
from agents.offer_intelligence import build_subgraph as _offer_intelligence_sg


# ── Routing ────────────────────────────────────────────────────────────────────

def _route(state: GlobalState) -> str:
    """Maps current_phase → next node name (or END)."""
    phase = state.get("current_phase", SystemPhase.IDLE)
    return {
        SystemPhase.GITHUB_ANALYSIS:  "github_intelligence",
        SystemPhase.JOB_DISCOVERY:    "job_discovery",
        SystemPhase.APPLYING:         "application_engine",
        SystemPhase.TRACKING:         "status_tracker",
        SystemPhase.OFFER_EVALUATION: "offer_intelligence",
        SystemPhase.IDLE:             END,
    }.get(phase, END)


# ── Graph construction ─────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Builds the Master StateGraph. Each Lead Agent's subgraph is compiled
    and added as a node. A pass-through "router" entry node reads
    current_phase to determine where to start — enabling mid-pipeline entry.
    """
    graph = StateGraph(GlobalState)

    # Entry router — lets the pipeline start from any phase
    graph.add_node("router", lambda s: s)

    # Lead Agent nodes (compiled subgraphs)
    graph.add_node("github_intelligence",  _github_sg().compile())
    graph.add_node("job_discovery",        _job_discovery_sg().compile())
    graph.add_node("application_engine",   _application_engine_sg().compile())
    graph.add_node("status_tracker",       _status_tracker_sg().compile())
    graph.add_node("offer_intelligence",   _offer_intelligence_sg().compile())

    # Wiring
    graph.set_entry_point("router")
    graph.add_conditional_edges("router",              _route)
    graph.add_conditional_edges("github_intelligence", _route)
    graph.add_conditional_edges("job_discovery",       _route)
    graph.add_conditional_edges("application_engine",  _route)
    graph.add_conditional_edges("status_tracker",      _route)
    graph.add_edge("offer_intelligence", END)

    return graph


def compile_graph(checkpointer=None):
    """Returns a compiled Master graph with checkpointing enabled."""
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_graph().compile(checkpointer=checkpointer)


# ── Public run functions ───────────────────────────────────────────────────────

def run_full_pipeline(
    github_username: str,
    target_role: str,
    target_market: str,
    target_niche: str,
    thread_id: str | None = None,
    checkpointer=None,
) -> tuple[GlobalState, str]:
    """
    Runs the complete pipeline: GitHub Intelligence → Job Discovery →
    Application Engine (with human-approval interrupt) → Status Tracker →
    Offer Intelligence (if offers present).

    Returns (final_state, thread_id). Keep thread_id to resume after
    human_approval_gate interrupts.
    """
    thread_id = thread_id or str(uuid.uuid4())
    state = initial_state(github_username, target_role, target_market, target_niche)
    state["current_phase"] = SystemPhase.GITHUB_ANALYSIS

    graph = compile_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(state, config=config)
    return result, thread_id


def run_module(
    module: str,
    state: GlobalState,
    thread_id: str | None = None,
    checkpointer=None,
) -> tuple[GlobalState, str]:
    """
    Runs a single module standalone.
    module: "github" | "job_discovery" | "application" | "status" | "offer"
    """
    phase_map = {
        "github":        SystemPhase.GITHUB_ANALYSIS,
        "job_discovery": SystemPhase.JOB_DISCOVERY,
        "application":   SystemPhase.APPLYING,
        "status":        SystemPhase.TRACKING,
        "offer":         SystemPhase.OFFER_EVALUATION,
    }
    if module not in phase_map:
        raise ValueError(f"Unknown module '{module}'. Choose from: {list(phase_map)}")

    thread_id = thread_id or str(uuid.uuid4())
    state = {**state, "current_phase": phase_map[module]}

    graph = compile_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(state, config=config)
    return result, thread_id


def resume_after_approval(
    approved: bool,
    thread_id: str,
    checkpointer=None,
) -> GlobalState:
    """
    Resumes a graph paused at human_approval_gate.
    Call with approved=True to submit, approved=False to skip.
    """
    graph = compile_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(Command(resume={"approved": approved}), config=config)


def inject_offer(
    state: GlobalState,
    company: str,
    job_title: str,
    offer_letter_text: str,
    deadline_date: str | None = None,
) -> GlobalState:
    """
    Injects an offer into state so the Offer Intelligence Lead can process it.
    Call this when you receive an offer, then run_module("offer", state).
    """
    from datetime import datetime, timezone
    offer = {
        "offer_id": f"offer_{uuid.uuid4().hex[:8]}",
        "company": company,
        "job_title": job_title,
        "offer_letter_text": offer_letter_text,
        "received_date": datetime.now(timezone.utc).isoformat(),
        "deadline_date": deadline_date,
        "employer_response": None,
    }
    active_offers = list(state.get("active_offers") or [])
    active_offers.append(offer)
    return {**state, "active_offers": active_offers, "current_phase": SystemPhase.OFFER_EVALUATION}


def inject_employer_response(
    state: GlobalState,
    offer_id: str,
    response_text: str,
) -> GlobalState:
    """
    Adds the employer's counter-offer response to an existing offer.
    Then re-run offer module to get response coaching.
    """
    active_offers = list(state.get("active_offers") or [])
    for offer in active_offers:
        if offer.get("offer_id") == offer_id:
            offer["employer_response"] = response_text
            # Reset coaching so it gets re-generated
            offer["response_coaching"] = None
            break
    return {**state, "active_offers": active_offers, "current_phase": SystemPhase.OFFER_EVALUATION}
