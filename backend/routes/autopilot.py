from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend import autopilot_scheduler

router = APIRouter(tags=["autopilot"])


class AutopilotConfigBody(BaseModel):
    enabled: bool = False
    at: str = "08:00"
    role: str = "AI Engineer"
    niche: str = "Agentic AI"
    market: str = "India"
    github_username: str = ""
    filters: dict[str, Any] = {}


@router.get("/api/autopilot/status")
async def autopilot_status():
    return {
        "config":   autopilot_scheduler.load_config(),
        "last_run": autopilot_scheduler.load_last_run(),
        "next_run": autopilot_scheduler.get_next_run_time(),
    }


@router.put("/api/autopilot/config")
async def update_autopilot_config(body: AutopilotConfigBody):
    cfg = body.model_dump()
    autopilot_scheduler.save_config(cfg)
    autopilot_scheduler.reschedule(cfg)
    return {"status": "saved", "config": cfg}


@router.post("/api/autopilot/run")
async def run_autopilot_now():
    """Trigger an immediate discovery + digest + email run. Returns job_id + thread_id for SSE."""
    from backend import runner
    from state import initial_state
    from config.settings import settings

    cfg = autopilot_scheduler.load_config()
    github_username = cfg.get("github_username") or settings.github_username

    thread_id = f"autopilot-{uuid.uuid4().hex[:8]}"
    state = dict(initial_state(
        github_username=github_username or "",
        target_role=cfg["role"],
        target_market=cfg["market"],
        target_niche=cfg.get("niche", ""),
    ))
    # Stash role/market so the runner's post-processing step can read them
    state["_autopilot_role"]   = cfg["role"]
    state["_autopilot_market"] = cfg["market"]
    if cfg.get("filters"):
        state["discovery_filters"] = cfg["filters"]

    job_id = runner.submit_job(thread_id, "autopilot", state)
    return {"job_id": job_id, "thread_id": thread_id}
