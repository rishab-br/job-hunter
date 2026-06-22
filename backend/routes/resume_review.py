"""Resume Reviewer route — accepts a file upload, extracts text, runs the LLM review."""
from __future__ import annotations

import io

from fastapi import APIRouter, Form, HTTPException, UploadFile

from backend import runner

router = APIRouter(tags=["resume-review"])


def _extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from PDF, TXT, or MD uploads."""
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except Exception as exc:
            raise HTTPException(422, f"Could not parse PDF: {exc}")
    # Plain text / markdown
    try:
        return content.decode("utf-8").strip()
    except UnicodeDecodeError:
        return content.decode("latin-1").strip()


@router.post("/api/resume-review/run")
async def run_resume_review(
    file: UploadFile,
    thread_id: str = Form(...),
):
    """
    Accept a resume file (PDF, TXT, MD), extract its text, store it in the session
    state, and kick off the resume_review subgraph. Returns job_id + thread_id for
    the frontend to subscribe via SSE.
    """
    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty")

    resume_text = _extract_text(file.filename or "", content)
    if not resume_text:
        raise HTTPException(422, "Could not extract any text from the uploaded file")

    state = runner.load_session(thread_id)
    if not state:
        raise HTTPException(404, f"Session '{thread_id}' not found")

    state["resume_text"] = resume_text
    job_id = runner.submit_job(thread_id, "resume_review", state)
    return {"job_id": job_id, "thread_id": thread_id}
