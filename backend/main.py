"""
JobHunter — FastAPI backend.

Start with:
    uvicorn backend.main:app --reload --port 8000

React SPA served from frontend/dist/ (build first: cd frontend && npm run build)
Falls back to legacy jobhunter_dashboard.html if dist/ doesn't exist.
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

from backend import runner, autopilot_scheduler
from backend.routes import sessions, modules, data, stream, auth, autopilot as autopilot_routes, resume_review as resume_review_routes, ats_modifier as ats_modifier_routes


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    runner.register_loop(asyncio.get_event_loop())
    autopilot_scheduler.start_scheduler()
    yield
    autopilot_scheduler.stop_scheduler()


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
app.include_router(autopilot_routes.router)
app.include_router(resume_review_routes.router)
app.include_router(ats_modifier_routes.router)


# ── Frontend ──────────────────────────────────────────────────────────────────

FRONTEND     = Path(__file__).parent.parent / "frontend"
FRONTEND_DIST = FRONTEND / "dist"

# Mount built React assets (JS/CSS chunks) if the dist folder exists
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve React SPA (dist/index.html) or legacy HTML fallback."""
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return HTMLResponse(dist_index.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>Frontend not built.</h1><p>Run: <code>cd frontend && npm install && npm run build</code></p>",
        status_code=503,
    )


@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_spa(full_path: str):
    """Catch-all for React Router — return index.html for all non-API paths."""
    if full_path.startswith("api/") or full_path.startswith("auth/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return HTMLResponse(dist_index.read_text(encoding="utf-8"))
    from fastapi import HTTPException
    raise HTTPException(status_code=404)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    # Inline 1x1 transparent ICO — no file needed
    return Response(content=b"", media_type="image/x-icon")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "jobhunter-api"}
