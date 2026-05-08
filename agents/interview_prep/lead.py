from langgraph.graph import StateGraph, END

from state import GlobalState, SystemPhase
from .workers.jd_decoder import run as decode_jd
from .workers.company_researcher import run as research_company
from .workers.question_generator import run as generate_questions
from .workers.answer_crafter import run as craft_answers
from .workers.cheat_sheet_builder import run as build_cheat_sheet


def build_subgraph() -> StateGraph:
    """
    Interview Prep Lead Agent subgraph.

    Pipeline:
        jd_decoder → company_researcher → question_generator
            → answer_crafter → cheat_sheet_builder → finalise → END

    Entry: interview_prep_target must be set on state with at least:
        { "company": "...", "role": "...", "jd_text": "..." }
    Optional: "company_url" for richer company research.
    """
    graph = StateGraph(GlobalState)

    graph.add_node("jd_decoder",          decode_jd)
    graph.add_node("company_researcher",   research_company)
    graph.add_node("question_generator",   generate_questions)
    graph.add_node("answer_crafter",       craft_answers)
    graph.add_node("cheat_sheet_builder",  build_cheat_sheet)
    graph.add_node("finalise",             _finalise)

    graph.set_entry_point("jd_decoder")
    graph.add_edge("jd_decoder",         "company_researcher")
    graph.add_edge("company_researcher",  "question_generator")
    graph.add_edge("question_generator",  "answer_crafter")
    graph.add_edge("answer_crafter",      "cheat_sheet_builder")
    graph.add_edge("cheat_sheet_builder", "finalise")
    graph.add_edge("finalise",            END)

    return graph


def _finalise(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    sessions = state.get("interview_prep_sessions") or []
    logs.append(
        f"[interview_prep] Done. {len(sessions)} prep session(s) on record. "
        f"Phase → IDLE."
    )
    return {
        **state,
        "current_phase": SystemPhase.IDLE,
        "active_lead": None,
        "logs": logs,
    }
