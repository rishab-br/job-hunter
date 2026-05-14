"""
JobHunter — FastAPI backend.

Start with:
    uvicorn backend.main:app --reload --port 8000

The frontend HTML is served at http://localhost:8000/
All API routes are under /api/...
SSE log stream at /api/stream/<thread_id>
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend import runner
from backend.routes import sessions, modules, data, stream, auth


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Give the runner a reference to the running event loop so background
    # threads can safely push to asyncio queues.
    runner.register_loop(asyncio.get_event_loop())
    yield
    # Graceful shutdown — nothing to clean up explicitly (executor daemon threads)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="JobHunter API",
    version="1.0.0",
    description="AI-powered autonomous job hunting system",
    lifespan=lifespan,
)

# Allow the HTML file to call the API when opened directly from disk
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(modules.router)
app.include_router(data.router)
app.include_router(stream.router)


# ── Frontend ──────────────────────────────────────────────────────────────────

FRONTEND = Path(__file__).parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML at the root URL."""
    html_path = FRONTEND / "jobhunter_dashboard.html"
    if not html_path.exists():
        return HTMLResponse("<h1>frontend/jobhunter_dashboard.html not found</h1>", 404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    # Inline 1x1 transparent ICO — no file needed
    return Response(content=b"", media_type="image/x-icon")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "jobhunter-api"}
