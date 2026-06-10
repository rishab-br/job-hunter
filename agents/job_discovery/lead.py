from langgraph.graph import StateGraph, END

from state import GlobalState, SystemPhase
from .workers.platform_scrapers.linkedin import run as scrape_linkedin
from .workers.platform_scrapers.indeed import run as scrape_indeed
from .workers.platform_scrapers.naukri import run as scrape_naukri
from .workers.platform_scrapers.ats_boards import run as scrape_ats_boards
from .workers.job_enricher import run as enrich_jobs
from .workers.jd_analyzer import run as analyze_jds
from .workers.relevance_scorer import run as score_relevance


def build_subgraph() -> StateGraph:
    graph = StateGraph(GlobalState)

    graph.add_node("scrape_linkedin", scrape_linkedin)
    graph.add_node("scrape_indeed", scrape_indeed)
    graph.add_node("scrape_naukri", scrape_naukri)
    graph.add_node("scrape_ats_boards", scrape_ats_boards)  # Greenhouse + Lever JSON APIs
    graph.add_node("job_enricher", enrich_jobs)             # description + company context
    graph.add_node("jd_analyzer", analyze_jds)
    graph.add_node("relevance_scorer", score_relevance)
    graph.add_node("finalise", _finalise)

    graph.set_entry_point("scrape_linkedin")
    graph.add_edge("scrape_linkedin", "scrape_indeed")
    graph.add_edge("scrape_indeed", "scrape_naukri")
    graph.add_edge("scrape_naukri", "scrape_ats_boards")
    graph.add_edge("scrape_ats_boards", "job_enricher")     # ATS jobs arrive with full JDs — enricher skips them
    graph.add_edge("job_enricher", "jd_analyzer")
    graph.add_edge("jd_analyzer", "relevance_scorer")
    graph.add_edge("relevance_scorer", "finalise")
    graph.add_edge("finalise", END)

    return graph


def _finalise(state: GlobalState) -> GlobalState:
    return {
        **state,
        "current_phase": SystemPhase.APPLYING,
        "active_lead": None,
    }
