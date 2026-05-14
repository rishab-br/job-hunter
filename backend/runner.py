"""
Background job runner with SSE log streaming.

Architecture:
- Sync LangGraph pipelines run in a ThreadPoolExecutor (Playwright requires sync).
- Each thread pushes log lines to asyncio.Queue instances via call_soon_threadsafe().
- SSE endpoints are async generators that consume from those queues.
- One queue per (thread_id, subscriber) — supports multiple browser tabs.
- Sessions persist to Supabase when configured, else falls back to local JSON files.
"""
import asyncio
import json
import uuid
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator

# ── Storage ───────────────────────────────────────────────────────────────────

SESSION_DIR = Path("memory/sessions")

# job_id -> {status, thread_id, error}
_jobs: Dict[str, dict] = {}

# thread_id -> [asyncio.Queue, ...]  (one queue per SSE subscriber)
_subscribers: Dict[str, List[asyncio.Queue]] = {}

# The main event loop — set at FastAPI startup
_main_loop: Optional[asyncio.AbstractEventLoop] = None

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jh-worker")


# ── Loop registration ─────────────────────────────────────────────────────────

def register_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


# ── Session I/O (Supabase primary, file fallback) ─────────────────────────────

def save_session(thread_id: str, state: dict, user_id: str = None) -> None:
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is not None:
        sb.table("job_sessions").upsert({
            "thread_id": thread_id,
            "user_id":   user_id,
            "state":     state,
        }).execute()
        return

    # ── File fallback ──────────────────────────────────────────────────────────
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{thread_id}.json"
    safe = {}
    for k, v in state.items():
        try:
            json.dumps(v, default=str)
            safe[k] = v
        except Exception:
            safe[k] = str(v)
    path.write_text(json.dumps(safe, indent=2, default=str), encoding="utf-8")


def load_session(thread_id: str) -> Optional[dict]:
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is not None:
        result = sb.table("job_sessions").select("state").eq("thread_id", thread_id).execute()
        if result.data:
            return result.data[0]["state"]
        return None

    # ── File fallback ──────────────────────────────────────────────────────────
    path = SESSION_DIR / f"{thread_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_sessions(user_id: str = None) -> List[dict]:
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is not None:
        query = sb.table("job_sessions").select("thread_id, state, updated_at")
        if user_id:
            query = query.eq("user_id", user_id)
        result = query.order("updated_at", desc=True).execute()
        out = []
        for row in result.data:
            d = row.get("state") or {}
            out.append({
                "thread_id":       row["thread_id"],
                "github_username": d.get("github_username", ""),
                "target_role":     d.get("target_role", ""),
                "target_market":   d.get("target_market", ""),
                "current_phase":   d.get("current_phase", "idle"),
                "jobs_found":      len(d.get("discovered_jobs") or []),
                "apps_submitted":  len(d.get("applications") or []),
                "offers":          len(d.get("active_offers") or []),
                "prep_sessions":   len(d.get("interview_prep_sessions") or []),
            })
        return out

    # ── File fallback ──────────────────────────────────────────────────────────
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(SESSION_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
            out.append({
                "thread_id":       p.stem,
                "github_username": d.get("github_username", ""),
                "target_role":     d.get("target_role", ""),
                "target_market":   d.get("target_market", ""),
                "current_phase":   d.get("current_phase", "idle"),
                "jobs_found":      len(d.get("discovered_jobs") or []),
                "apps_submitted":  len(d.get("applications") or []),
                "offers":          len(d.get("active_offers") or []),
                "prep_sessions":   len(d.get("interview_prep_sessions") or []),
            })
        except Exception:
            pass
    return out


# ── SSE pub/sub ───────────────────────────────────────────────────────────────

def _push(thread_id: str, message: str) -> None:
    if _main_loop is None or _main_loop.is_closed():
        return
    for q in _subscribers.get(thread_id, []):
        _main_loop.call_soon_threadsafe(q.put_nowait, message)


def subscribe(thread_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(thread_id, []).append(q)
    return q


def unsubscribe(thread_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(thread_id, [])
    try:
        subs.remove(q)
    except ValueError:
        pass


async def log_stream(thread_id: str) -> AsyncGenerator[str, None]:
    q = subscribe(thread_id)
    try:
        while True:
            msg = await q.get()
            if msg.startswith("__DONE__") or msg.startswith("__ERROR__"):
                yield f"data: {msg}\n\n"
                break
            yield f"data: {msg}\n\n"
    finally:
        unsubscribe(thread_id, q)


# ── Job management ────────────────────────────────────────────────────────────

def get_job(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


def submit_job(
    thread_id: str,
    module: str,
    state: dict,
    extra: dict = None,
    user_id: str = None,
) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "thread_id": thread_id, "error": None}
    _executor.submit(_worker, job_id, thread_id, module, state, extra or {}, user_id)
    return job_id


# ── Worker ────────────────────────────────────────────────────────────────────

def _worker(
    job_id: str,
    thread_id: str,
    module: str,
    state: dict,
    extra: dict,
    user_id: str = None,
) -> None:
    try:
        _jobs[job_id]["status"] = "running"

        from orchestrator.master import compile_graph
        from state import SystemPhase
        from orchestrator import inject_interview_target
        from orchestrator.master import inject_offer as _inject_offer

        phase_map = {
            "github":         SystemPhase.GITHUB_ANALYSIS,
            "job_discovery":  SystemPhase.JOB_DISCOVERY,
            "application":    SystemPhase.APPLYING,
            "status":         SystemPhase.TRACKING,
            "offer":          SystemPhase.OFFER_EVALUATION,
            "interview_prep": SystemPhase.INTERVIEW_PREP,
        }

        if module == "offer":
            state = _inject_offer(
                state,
                company=extra["company"],
                job_title=extra["job_title"],
                offer_letter_text=extra["offer_letter_text"],
                deadline_date=extra.get("deadline_date"),
            )
        elif module == "interview_prep":
            state = inject_interview_target(
                state,
                company=extra["company"],
                role=extra["role"],
                jd_text=extra["jd_text"],
                company_url=extra.get("company_url", ""),
                job_id=extra.get("job_id"),
            )
        else:
            state = {**state, "current_phase": phase_map[module]}

        graph = compile_graph()
        config = {"configurable": {"thread_id": thread_id}}

        prev_log_count = len(state.get("logs") or [])
        final_state = dict(state)

        for chunk in graph.stream(state, config=config, stream_mode="updates"):
            for _node, node_state in chunk.items():
                if not isinstance(node_state, dict):
                    continue
                current_logs = list(node_state.get("logs") or [])
                for log_line in current_logs[prev_log_count:]:
                    _push(thread_id, log_line)
                prev_log_count = len(current_logs)
                final_state.update(node_state)

        save_session(thread_id, final_state, user_id=user_id)
        _push(thread_id, f"__DONE__{job_id}")
        _jobs[job_id]["status"] = "done"

    except Exception as exc:
        _push(thread_id, f"[ERROR] {exc}")
        _push(thread_id, f"__ERROR__{job_id}")
        _jobs[job_id].update({"status": "failed", "error": str(exc)})
        traceback.print_exc()
