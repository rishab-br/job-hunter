"""APScheduler wrapper for autopilot daily discovery.

Config is read from memory/autopilot/config.json on every tick, so edits
via the web UI take effect on the next scheduled run without a server restart.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_CONFIG_PATH   = Path("memory/autopilot/config.json")
_LAST_RUN_PATH = Path("memory/autopilot/last_run.json")

_DEFAULT_CONFIG: dict = {
    "enabled": False,
    "at": "08:00",
    "role": "AI Engineer",
    "niche": "Agentic AI",
    "market": "India",
    "github_username": "",
    "filters": {
        "max_seniority": "junior",
        "locations": [],
        "remote_ok": True,
        "min_score": 0,
    },
}

_scheduler = None


# ── Config I/O ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if _CONFIG_PATH.exists():
        try:
            on_disk = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return {**_DEFAULT_CONFIG, **on_disk}
        except Exception:
            pass
    return dict(_DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def load_last_run() -> dict | None:
    if _LAST_RUN_PATH.exists():
        try:
            return json.loads(_LAST_RUN_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def save_last_run(result: dict) -> None:
    _LAST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LAST_RUN_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def start_scheduler() -> None:
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler(timezone="UTC")
        cfg = load_config()
        _apply_schedule(cfg)
        _scheduler.start()
        log.info("[autopilot] Scheduler started (enabled=%s, at=%s UTC)", cfg["enabled"], cfg["at"])
    except ImportError:
        log.warning("[autopilot] apscheduler not installed — scheduled runs disabled. Run: pip install apscheduler")
    except Exception as exc:
        log.exception("[autopilot] Failed to start scheduler: %s", exc)


def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def reschedule(cfg: dict) -> None:
    """Called by PUT /api/autopilot/config to apply new schedule without a restart."""
    if _scheduler is None or not _scheduler.running:
        return
    _apply_schedule(cfg)


def _apply_schedule(cfg: dict) -> None:
    _scheduler.remove_all_jobs()
    if cfg.get("enabled"):
        try:
            h, m = (cfg.get("at") or "08:00").split(":")
            _scheduler.add_job(_tick, "cron", hour=int(h), minute=int(m), id="autopilot_daily")
            log.info("[autopilot] Daily job scheduled at %s:%s UTC", h, m)
        except Exception as exc:
            log.error("[autopilot] Failed to set schedule: %s", exc)


def get_next_run_time() -> str | None:
    if _scheduler is None:
        return None
    try:
        job = _scheduler.get_job("autopilot_daily")
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
    except Exception:
        pass
    return None


# ── Scheduled tick ────────────────────────────────────────────────────────────

def _tick() -> None:
    """Called by APScheduler on the cron schedule."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return

    from automation.autopilot import run_daily_discovery
    from config.settings import settings

    github_username = cfg.get("github_username") or settings.github_username
    if not github_username:
        log.warning("[autopilot] github_username not configured — skipping scheduled run")
        return

    log.info("[autopilot] Starting scheduled discovery: role=%s market=%s", cfg["role"], cfg["market"])
    try:
        result = run_daily_discovery(
            role=cfg["role"],
            niche=cfg.get("niche", ""),
            market=cfg["market"],
            github_username=github_username,
            filters=cfg.get("filters"),
        )
        save_last_run(result)
        log.info("[autopilot] Scheduled run complete — %d new jobs", result.get("new_jobs", 0))
    except Exception as exc:
        log.exception("[autopilot] Scheduled run failed: %s", exc)
        save_last_run({"error": str(exc), "ran_at": datetime.now(timezone.utc).isoformat()})
