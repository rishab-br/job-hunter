from fastapi import APIRouter, HTTPException
from backend.models import (
    RunGithubRequest,
    RunModuleRequest,
    RunDiscoveryRequest,
    RunPrepRequest,
    InjectOfferRequest,
    ResumeRequest,
    JobStatusResponse,
)
from backend import runner
from state import initial_state
from config.settings import settings
import uuid

router = APIRouter(tags=["modules"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_or_404(thread_id: str) -> dict:
    state = runner.load_session(thread_id)
    if not state:
        raise HTTPException(404, f"Session '{thread_id}' not found")
    return state


def _bare_state(username: str, role: str, market: str, niche: str) -> tuple[dict, str]:
    tid = str(uuid.uuid4())
    state = initial_state(
        github_username=username,
        target_role=role,
        target_market=market,
        target_niche=niche,
    )
    return dict(state), tid


def _resolve_user(user_id: str | None) -> tuple[str, str | None]:
    """
    Given a user_id (from OAuth), return (github_username, github_token).
    Falls back to settings when user_id is absent or Supabase is not configured.
    """
    if user_id:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb is not None:
            result = (
                sb.table("users")
                .select("github_username, github_token")
                .eq("id", user_id)
                .execute()
            )
            if result.data:
                row = result.data[0]
                return row["github_username"], row["github_token"]
    return settings.github_username, settings.github_token or None


# ── Module endpoints ──────────────────────────────────────────────────────────

@router.post("/api/modules/github")
async def run_github(req: RunGithubRequest):
    """Run GitHub Intelligence. Uses OAuth token when user_id provided."""
    github_username, github_token = _resolve_user(req.user_id)
    if not github_username:
        github_username = req.github_username
    if not github_username:
        raise HTTPException(400, "github_username required (or connect GitHub via OAuth)")

    if req.thread_id:
        state = _load_or_404(req.thread_id)
        thread_id = req.thread_id
    else:
        state, thread_id = _bare_state(
            github_username, req.target_role, req.target_market, req.target_niche,
        )

    state.update(
        github_username=github_username,
        github_token=github_token,
        target_role=req.target_role or state.get("target_role", ""),
    )
    job_id = runner.submit_job(thread_id, "github", state, user_id=req.user_id)
    return {"job_id": job_id, "thread_id": thread_id}


@router.post("/api/modules/discovery")
async def run_discovery(req: RunDiscoveryRequest):
    state = _load_or_404(req.thread_id)
    if req.target_role:   state["target_role"]   = req.target_role
    if req.target_market: state["target_market"] = req.target_market
    if req.target_niche:  state["target_niche"]  = req.target_niche
    job_id = runner.submit_job(req.thread_id, "job_discovery", state, user_id=req.user_id)
    return {"job_id": job_id, "thread_id": req.thread_id}


@router.post("/api/modules/application")
async def run_application(req: RunModuleRequest):
    state = _load_or_404(req.thread_id)
    job_id = runner.submit_job(req.thread_id, "application", state, user_id=req.user_id)
    return {"job_id": job_id, "thread_id": req.thread_id}


@router.post("/api/modules/status")
async def run_status(req: RunModuleRequest):
    state = _load_or_404(req.thread_id)
    job_id = runner.submit_job(req.thread_id, "status", state, user_id=req.user_id)
    return {"job_id": job_id, "thread_id": req.thread_id}


@router.post("/api/modules/offer")
async def run_offer(req: InjectOfferRequest):
    github_username, github_token = _resolve_user(req.user_id)
    if not github_username:
        github_username = req.github_username

    if req.thread_id:
        state = _load_or_404(req.thread_id)
        thread_id = req.thread_id
    else:
        state, thread_id = _bare_state(
            github_username, req.target_role, req.target_market, req.target_niche
        )
    state.update(github_token=github_token)

    extra = {
        "company":           req.company,
        "job_title":         req.job_title,
        "offer_letter_text": req.offer_letter_text,
        "deadline_date":     req.deadline_date,
    }
    job_id = runner.submit_job(thread_id, "offer", state, extra, user_id=req.user_id)
    return {"job_id": job_id, "thread_id": thread_id}


@router.post("/api/modules/prep")
async def run_prep(req: RunPrepRequest):
    github_username, github_token = _resolve_user(req.user_id)
    if not github_username:
        github_username = req.github_username

    if req.thread_id:
        state = _load_or_404(req.thread_id)
        thread_id = req.thread_id
    else:
        state, thread_id = _bare_state(
            github_username, req.target_role, req.target_market, req.target_niche
        )
    state.update(github_token=github_token)

    extra = {
        "company":     req.company,
        "role":        req.role,
        "jd_text":     req.jd_text,
        "company_url": req.company_url,
        "job_id":      req.job_id,
    }
    job_id = runner.submit_job(thread_id, "interview_prep", state, extra, user_id=req.user_id)
    return {"job_id": job_id, "thread_id": thread_id}


@router.post("/api/resume")
async def resume_pipeline(req: ResumeRequest):
    from orchestrator import resume_after_approval
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: resume_after_approval(approved=req.approved, thread_id=req.thread_id),
    )
    runner.save_session(req.thread_id, result)
    return {"status": "resumed", "thread_id": req.thread_id, "approved": req.approved}


# ── Job status ────────────────────────────────────────────────────────────────

@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        thread_id=job["thread_id"],
        error=job.get("error"),
    )
