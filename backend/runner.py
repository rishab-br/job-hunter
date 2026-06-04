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

def _file_save(thread_id: str, state: dict) -> None:
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


def save_session(thread_id: str, state: dict, user_id: str = None) -> None:
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is not None:
        try:
            sb.table("job_sessions").upsert({
                "thread_id": thread_id,
                "user_id":   user_id,
                "state":     state,
            }).execute()
            return
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase save failed, using file fallback: {e}")

    _file_save(thread_id, state)


def load_session(thread_id: str) -> Optional[dict]:
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is not None:
        try:
            result = sb.table("job_sessions").select("state").eq("thread_id", thread_id).execute()
            if result.data:
                return result.data[0]["state"]
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase load failed, using file fallback: {e}")

    # ── File fallback ──────────────────────────────────────────────────────────
    path = SESSION_DIR / f"{thread_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_sessions(user_id: str = None) -> List[dict]:
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is not None:
        try:
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
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase list failed, using file fallback: {e}")

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

# ── Subgraph registry — single-module runs bypass the master orchestrator ─────
# This prevents github → job_discovery → application → ... cascade.
_STANDALONE_SUBGRAPHS = {
    "github":        "agents.github_intelligence",
    "job_discovery": "agents.job_discovery",
    "status":        "agents.status_tracker",
}


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

        from state import SystemPhase
        from orchestrator import inject_interview_target
        from orchestrator.master import inject_offer as _inject_offer

        config = {"configurable": {"thread_id": thread_id}}
        uses_checkpointer = False

        # ── Offer / Interview Prep: need injection + master graph ──────────────
        if module == "offer":
            from orchestrator.master import compile_graph
            state = _inject_offer(
                state,
                company=extra["company"],
                job_title=extra["job_title"],
                offer_letter_text=extra["offer_letter_text"],
                deadline_date=extra.get("deadline_date"),
            )
            graph = compile_graph()
            uses_checkpointer = True

        elif module == "interview_prep":
            from orchestrator.master import compile_graph
            state = inject_interview_target(
                state,
                company=extra["company"],
                role=extra["role"],
                jd_text=extra["jd_text"],
                company_url=extra.get("company_url", ""),
                job_id=extra.get("job_id"),
            )
            graph = compile_graph()
            uses_checkpointer = True

        elif module == "application":
            # Application engine needs the master graph + shared checkpointer for
            # interrupt/resume at the human approval gate.
            from orchestrator.master import compile_graph
            state = {**state, "current_phase": SystemPhase.APPLYING}
            graph = compile_graph()
            uses_checkpointer = True

        elif module in _STANDALONE_SUBGRAPHS:
            # Run the subgraph directly — avoids cascading to next pipeline phase
            import importlib
            pkg = importlib.import_module(_STANDALONE_SUBGRAPHS[module])
            phase_map = {
                "github":        SystemPhase.GITHUB_ANALYSIS,
                "job_discovery": SystemPhase.JOB_DISCOVERY,
                "status":        SystemPhase.TRACKING,
            }
            state = {**state, "current_phase": phase_map[module]}
            graph = pkg.build_subgraph().compile()

        else:
            from orchestrator.master import compile_graph
            graph = compile_graph()
            uses_checkpointer = True

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

        # ── Interrupt detection (human approval gate) ──────────────────────────
        if uses_checkpointer:
            snap = graph.get_state(config)
            interrupts = _extract_interrupts(snap)
            if snap.next and interrupts:
                # Graph paused awaiting human approval — persist and signal the UI
                final_state = dict(snap.values or final_state)
                save_session(thread_id, final_state, user_id=user_id)
                _push(thread_id, "[human_approval_gate] ⏸ Awaiting your approval — review the application.")
                _push(thread_id, f"__INTERRUPT__{job_id}")
                _jobs[job_id]["status"] = "awaiting_approval"
                return
            final_state = dict(snap.values or final_state)

        save_session(thread_id, final_state, user_id=user_id)
        _push(thread_id, f"__DONE__{job_id}")
        _jobs[job_id]["status"] = "done"

    except Exception as exc:
        _push(thread_id, f"[ERROR] {exc}")
        _push(thread_id, f"__ERROR__{job_id}")
        _jobs[job_id].update({"status": "failed", "error": str(exc)})
        traceback.print_exc()


# ── Human Approval Gate — interrupt inspection & resume ───────────────────────

def _extract_interrupts(snapshot) -> List[dict]:
    """Pull interrupt payloads (the dicts passed to interrupt(...)) from a state snapshot."""
    out: List[dict] = []
    for task in getattr(snapshot, "tasks", ()) or ():
        for intr in (getattr(task, "interrupts", ()) or ()):
            val = getattr(intr, "value", None)
            if isinstance(val, dict):
                out.append(val)
    return out


def get_pending_approval(thread_id: str) -> dict:
    """
    Inspects the checkpointed graph for a pending human-approval interrupt.
    Returns the current application under review, or {"awaiting": False}.
    """
    from orchestrator.master import compile_graph
    graph = compile_graph()  # shared checkpointer
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snap = graph.get_state(config)
    except Exception:
        return {"awaiting": False}

    interrupts = _extract_interrupts(snap)
    if not snap.next or not interrupts:
        return {"awaiting": False}

    current = interrupts[0]
    job = current.get("job", {}) if isinstance(current, dict) else {}

    # Count how many applications still need review (queued, not yet decided)
    values = snap.values or {}
    total_queued = len(values.get("pending_approvals") or [])

    return {
        "awaiting":  True,
        "message":   current.get("message", ""),
        "job":       job,
        "remaining": total_queued,
    }


def resume_application(thread_id: str, approved: bool, user_id: str = None) -> str:
    """Resume a graph paused at the human approval gate, in the background."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "thread_id": thread_id, "error": None}
    _executor.submit(_resume_worker, job_id, thread_id, approved, user_id)
    return job_id


def _resume_worker(job_id: str, thread_id: str, approved: bool, user_id: str = None) -> None:
    try:
        _jobs[job_id]["status"] = "running"
        from orchestrator.master import compile_graph
        from langgraph.types import Command

        graph  = compile_graph()  # shared checkpointer
        config = {"configurable": {"thread_id": thread_id}}

        decision = "APPROVED ✓" if approved else "SKIPPED"
        _push(thread_id, f"[human_approval_gate] {decision} — resuming pipeline...")

        prev = graph.get_state(config).values or {}
        prev_log_count = len(prev.get("logs") or [])

        for chunk in graph.stream(Command(resume={"approved": approved}), config=config, stream_mode="updates"):
            for _node, node_state in chunk.items():
                if not isinstance(node_state, dict):
                    continue
                logs = list(node_state.get("logs") or [])
                for line in logs[prev_log_count:]:
                    _push(thread_id, line)
                prev_log_count = len(logs)

        snap = graph.get_state(config)
        interrupts = _extract_interrupts(snap)
        final_state = dict(snap.values or {})
        save_session(thread_id, final_state, user_id=user_id)

        if snap.next and interrupts:
            # Another application is queued for review
            _push(thread_id, "[human_approval_gate] ⏸ Next application awaiting approval.")
            _push(thread_id, f"__INTERRUPT__{job_id}")
            _jobs[job_id]["status"] = "awaiting_approval"
        else:
            _push(thread_id, f"__DONE__{job_id}")
            _jobs[job_id]["status"] = "done"

    except Exception as exc:
        _push(thread_id, f"[ERROR] resume failed: {exc}")
        _push(thread_id, f"__ERROR__{job_id}")
        _jobs[job_id].update({"status": "failed", "error": str(exc)})
        traceback.print_exc()
