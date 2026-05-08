"""
SSE (Server-Sent Events) endpoint for real-time agent log streaming.

Connect before triggering a module run:
  const es = new EventSource('/api/stream/<thread_id>');
  es.onmessage = e => console.log(e.data);

Special sentinel messages:
  __DONE__<job_id>   — pipeline finished successfully
  __ERROR__<job_id>  — pipeline failed
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend import runner

router = APIRouter(tags=["stream"])


@router.get("/api/stream/{thread_id}")
async def stream_logs(thread_id: str):
    """
    SSE endpoint. Stays open, yields log lines as they arrive from the
    background worker thread. Closes on __DONE__ or __ERROR__ sentinel.
    """
    async def _generate():
        # Send a keep-alive comment so the browser doesn't time out immediately
        yield ": connected\n\n"
        async for chunk in runner.log_stream(thread_id):
            yield chunk

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",     # disable nginx buffering
            "Connection": "keep-alive",
        },
    )
