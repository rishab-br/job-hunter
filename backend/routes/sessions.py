from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.models import NewSessionRequest
from backend import runner
from state import initial_state
import uuid

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(user_id: Optional[str] = Query(None)):
    """List sessions for a user (filtered by user_id when provided)."""
    return runner.list_sessions(user_id=user_id)


@router.post("")
async def create_session(req: NewSessionRequest):
    """Create a blank session. Resolves github_username from user_id when OAuth is active."""
    github_username = req.github_username
    github_token = None

    if req.user_id:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb is not None:
            result = (
                sb.table("users")
                .select("github_username, github_token")
                .eq("id", req.user_id)
                .execute()
            )
            if result.data:
                github_username = result.data[0]["github_username"]
                github_token = result.data[0]["github_token"]

    if not github_username:
        raise HTTPException(400, "github_username required (or connect GitHub via OAuth)")

    thread_id = str(uuid.uuid4())
    state = dict(initial_state(
        github_username=github_username,
        target_role=req.target_role,
        target_market=req.target_market,
        target_niche=req.target_niche,
    ))
    state["github_token"] = github_token
    runner.save_session(thread_id, state, user_id=req.user_id)
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
    apps   = state.get("applications") or []

    audit = state.get("github_audit") or {}
    repos = state.get("repo_depth_reports") or []

    return {
        "thread_id":       thread_id,
        "github_username": state.get("github_username", ""),
        "target_role":     state.get("target_role", ""),
        "current_phase":   state.get("current_phase", "idle"),
        "logs":            (state.get("logs") or [])[-50:],

        # GitHub Intel
        "github_score":    audit.get("overall_score"),
        "repos_analyzed":  audit.get("repos_analyzed") or len(repos) or None,

        # Job Discovery
        "jobs_found":      len(state.get("discovered_jobs") or []),
        "jobs_high_fit":   sum(1 for j in scored if j.get("relevance_score", 0) >= 75),

        # Application Engine
        "apps_submitted":  len(apps),

        # Status Tracker
        "ghosted":         len(state.get("ghosted_applications") or []),

        # Offer Intelligence
        "offers_received": len(state.get("active_offers") or []),

        # Interview Prep
        "prep_sessions":   len(state.get("interview_prep_sessions") or []),

        # Phase completion flags
        "has_github_analysis":  bool(audit),
        "has_job_discovery":    bool(state.get("discovered_jobs")),
        "has_applying":         bool(apps),
        "has_tracking":         bool(state.get("application_statuses")),
        "has_offer_evaluation": bool(state.get("active_offers")),
        "has_interview_prep":   bool(state.get("interview_prep_sessions")),
    }
