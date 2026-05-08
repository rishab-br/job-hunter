from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import GlobalState, SystemPhase
from .workers.resume_tailor import run as tailor_resume
from .workers.cover_letter_writer import run as write_cover_letter
from .workers.form_filler import run as fill_form
from .workers.human_approval_gate import run as approval_gate
from .workers.submission_executor import run as execute_submission


def build_subgraph() -> StateGraph:
    graph = StateGraph(GlobalState)

    graph.add_node("resume_tailor", tailor_resume)
    graph.add_node("cover_letter_writer", write_cover_letter)
    graph.add_node("form_filler", fill_form)
    graph.add_node("human_approval_gate", approval_gate)
    graph.add_node("submission_executor", execute_submission)
    graph.add_node("finalise", _finalise)

    graph.set_entry_point("resume_tailor")
    graph.add_edge("resume_tailor", "cover_letter_writer")
    graph.add_edge("cover_letter_writer", "form_filler")
    graph.add_edge("form_filler", "human_approval_gate")
    graph.add_edge("human_approval_gate", "submission_executor")
    graph.add_edge("submission_executor", "finalise")
    graph.add_edge("finalise", END)

    return graph


def build_compiled(checkpointer=None):
    """
    Returns a compiled Application Engine graph.
    Pass a checkpointer (e.g. MemorySaver) to enable interrupt/resume
    at the human_approval_gate node.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_subgraph().compile(checkpointer=checkpointer)


def _finalise(state: GlobalState) -> GlobalState:
    return {
        **state,
        "current_phase": SystemPhase.TRACKING,
        "active_lead": None,
    }
