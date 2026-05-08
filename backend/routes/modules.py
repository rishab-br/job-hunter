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


# ── Module endpoints ──────────────────────────────────────────────────────────

@router.post("/api/modules/github")
async def run_github(req: RunGithubRequest):
    """Run GitHub Intelligence. Creates a new session if no thread_id given."""
    if req.thread_id:
        state = _load_or_404(req.thread_id)
        thread_id = req.thread_id
    else:
        state, thread_id = _bare_state(
            req.github_username, req.target_role, req.target_market, req.target_niche
        )
    # Patch credentials into state
    state.update(github_username=req.github_username, target_role=req.target_role)
    job_id = runner.submit_job(thread_id, "github", state)
    return {"job_id": job_id, "thread_id": thread_id}


@router.post("/api/modules/discovery")
async def run_discovery(req: RunDiscoveryRequest):
    """Run Job Discovery against an existing session."""
    state = _load_or_404(req.thread_id)
    if req.target_role:
        state["target_role"] = req.target_role
    if req.target_market:
        state["target_market"] = req.target_market
    if req.target_niche:
        state["target_niche"] = req.target_niche
    job_id = runner.submit_job(req.thread_id, "job_discovery", state)
    return {"job_id": job_id, "thread_id": req.thread_id}


@router.post("/api/modules/application")
async def run_application(req: RunModuleRequest):
    state = _load_or_404(req.thread_id)
    job_id = runner.submit_job(req.thread_id, "application", state)
    return {"job_id": job_id, "thread_id": req.thread_id}


@router.post("/api/modules/status")
async def run_status(req: RunModuleRequest):
    state = _load_or_404(req.thread_id)
    job_id = runner.submit_job(req.thread_id, "status", state)
    return {"job_id": job_id, "thread_id": req.thread_id}


@router.post("/api/modules/offer")
async def run_offer(req: InjectOfferRequest):
    """Inject an offer + run Offer Intelligence. Creates session if needed."""
    if req.thread_id:
        state = _load_or_404(req.thread_id)
        thread_id = req.thread_id
    else:
        state, thread_id = _bare_state(
            req.github_username, req.target_role, req.target_market, req.target_niche
        )
    extra = {
        "company":           req.company,
        "job_title":         req.job_title,
        "offer_letter_text": req.offer_letter_text,
        "deadline_date":     req.deadline_date,
    }
    job_id = runner.submit_job(thread_id, "offer", state, extra)
    return {"job_id": job_id, "thread_id": thread_id}


@router.post("/api/modules/prep")
async def run_prep(req: RunPrepRequest):
    """Inject interview prep target + run Interview Prep. Creates session if needed."""
    if req.thread_id:
        state = _load_or_404(req.thread_id)
        thread_id = req.thread_id
    else:
        state, thread_id = _bare_state(
            req.github_username, req.target_role, req.target_market, req.target_niche
        )
    extra = {
        "company":     req.company,
        "role":        req.role,
        "jd_text":     req.jd_text,
        "company_url": req.company_url,
        "job_id":      req.job_id,
    }
    job_id = runner.submit_job(thread_id, "interview_prep", state, extra)
    return {"job_id": job_id, "thread_id": thread_id}


@router.post("/api/resume")
async def resume_pipeline(req: ResumeRequest):
    """Resume a pipeline paused at the human-approval gate."""
    from orchestrator import resume_after_approval
    # Run in thread pool since it's sync
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
