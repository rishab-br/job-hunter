"""ATS Modifier route — accepts a JD + session, runs the tailoring subgraph."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend import runner

router = APIRouter(tags=["ats-modifier"])


class ATSModifierRequest(BaseModel):
    thread_id: str
    jd_text: str
    company: str = ""
    job_title: str = ""


@router.post("/api/ats-modifier/run")
async def run_ats_modifier(body: ATSModifierRequest):
    """
    Inject a job description into the session state and kick off the
    ATS modifier subgraph.  Returns job_id + thread_id for SSE.
    """
    if not body.jd_text.strip():
        raise HTTPException(400, "jd_text must not be empty")

    state = runner.load_session(body.thread_id)
    if not state:
        raise HTTPException(404, f"Session '{body.thread_id}' not found")

    if not state.get("resume_text"):
        raise HTTPException(
            422,
            "No resume uploaded yet — run the Resume Review step first to upload your resume.",
        )

    # Temporary per-run fields (underscore-prefixed, not persisted as session schema)
    state["_ats_jd_text"]   = body.jd_text
    state["_ats_company"]   = body.company
    state["_ats_job_title"] = body.job_title

    job_id = runner.submit_job(body.thread_id, "ats_modifier", state)
    return {"job_id": job_id, "thread_id": body.thread_id}
