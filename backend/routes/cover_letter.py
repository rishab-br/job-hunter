"""Cover Letter route — generates a tailored cover letter for a specific JD."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend import runner

router = APIRouter(tags=["cover-letter"])


class CoverLetterRequest(BaseModel):
    thread_id: str
    company: str = ""
    job_title: str = ""
    jd_text: str = ""
    tone: str = "professional"   # professional | conversational | enthusiastic


@router.post("/api/cover-letter/run")
async def run_cover_letter(body: CoverLetterRequest):
    if body.tone not in ("professional", "conversational", "enthusiastic"):
        raise HTTPException(400, "tone must be professional, conversational, or enthusiastic")

    state = runner.load_session(body.thread_id)
    if not state:
        raise HTTPException(404, f"Session '{body.thread_id}' not found")

    if not state.get("resume_text"):
        raise HTTPException(
            422,
            "No resume uploaded yet — run Resume Review first to upload your resume.",
        )

    state["_cl_company"]   = body.company
    state["_cl_job_title"] = body.job_title
    state["_cl_jd_text"]   = body.jd_text
    state["_cl_tone"]      = body.tone

    job_id = runner.submit_job(body.thread_id, "cover_letter", state)
    return {"job_id": job_id, "thread_id": body.thread_id}
