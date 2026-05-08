from fastapi import APIRouter, HTTPException
from backend.models import NewSessionRequest
from backend import runner
from state import initial_state
import uuid

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions():
    """List all saved sessions (most-recent first)."""
    return runner.list_sessions()


@router.post("")
async def create_session(req: NewSessionRequest):
    """Create a blank session and return the thread_id."""
    thread_id = str(uuid.uuid4())
    state = initial_state(
        github_username=req.github_username,
        target_role=req.target_role,
        target_market=req.target_market,
        target_niche=req.target_niche,
    )
    runner.save_session(thread_id, state)
    return {"thread_id": thread_id, **state}


@router.get("/{thread_id}")
async def get_session(thread_id: str):
    """Return full state for a session."""
    state = runner.load_session(thread_id)
    if not state:
        raise HTTPException(404, f"Session '{thread_id}' not found")
    return state


@router.get("/{thread_id}/summary")
async def get_summary(thread_id: str):
    """Dashboard-ready summary stats for a session."""
    state = runner.load_session(thread_id)
    if not state:
        raise HTTPException(404, f"Session '{thread_id}' not found")

    scored = state.get("scored_jobs") or []
    apps = state.get("applications") or []
    statuses = state.get("application_statuses") or {}

    return {
        "thread_id":       thread_id,
        "github_username": state.get("github_username", ""),
        "target_role":     state.get("target_role", ""),
        "current_phase":   state.get("current_phase", "idle"),
        "logs":            (state.get("logs") or [])[-50:],

        # Quick stats
        "jobs_found":      len(state.get("discovered_jobs") or []),
        "jobs_high_fit":   sum(1 for j in scored if j.get("relevance_score", 0) >= 75),
        "apps_submitted":  len(apps),
        "offers_received": len(state.get("active_offers") or []),
        "prep_sessions":   len(state.get("interview_prep_sessions") or []),
        "ghosted":         len(state.get("ghosted_applications") or []),

        # Module last-run signals
        "has_audit":       bool(state.get("github_audit")),
        "has_jobs":        bool(state.get("discovered_jobs")),
        "has_apps":        bool(apps),
        "has_offers":      bool(state.get("active_offers")),
        "has_prep":        bool(state.get("interview_prep_sessions")),
    }
