"""Autopilot — autonomous daily job discovery with a morning digest.

Runs the Job Discovery subgraph directly (same standalone pattern the
backend uses — no cascade into the apply phase), dedupes against every
job seen on previous runs, and delivers a digest of what's genuinely new.

Discovery only: nothing is ever applied to autonomously. The human
approval gate stays exactly where it is.
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from skills import notify
from state import GlobalState, SystemPhase, initial_state

SEEN_PATH = Path("memory/autopilot/seen_jobs.json")
DIGEST_DIR = Path("outputs/digests")
SESSION_DIR = Path("memory/sessions")

SEEN_RETENTION_DAYS = 60   # forget jobs not re-seen in this window
DIGEST_TOP_N = 200         # effectively unlimited for email; Telegram summary has its own cap


# ── Entry points ───────────────────────────────────────────────────────────────

def run_daily_discovery(
    role: str,
    niche: str = "",
    market: str = "India",
    github_username: str = "",
    filters: dict | None = None,
) -> dict:
    """One-shot autonomous discovery run. Returns a summary dict."""
    from agents.job_discovery import build_subgraph  # deferred: heavy import

    state = initial_state(
        github_username=github_username,
        target_role=role,
        target_market=market,
        target_niche=niche,
    )
    state["current_phase"] = SystemPhase.JOB_DISCOVERY
    if filters:
        state["discovery_filters"] = filters
    _inject_profile_context(state)

    graph = build_subgraph().compile()
    result: GlobalState = graph.invoke(state)

    scored = result.get("scored_jobs") or []
    seen = _load_seen()
    new_jobs, seen = _split_new_jobs(scored, seen)
    _save_seen(seen)

    digest_md = build_digest(new_jobs, total_scored=len(scored), role=role, market=market)
    digest_path = _save_digest(digest_md)

    high_count = sum(1 for j in new_jobs if j.get("priority") == "high")
    delivered = notify.send_digest(
        subject=build_email_subject(len(new_jobs), high_count),
        markdown_body=digest_md,
        compact_text=build_compact_summary(new_jobs, len(scored), role),
    )

    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "total_scored": len(scored),
        "new_jobs": len(new_jobs),
        "high_priority": high_count,
        "digest_path": str(digest_path),
        "delivered": delivered,
    }


def autopilot_loop(role: str, niche: str, market: str, github_username: str, at: str = "08:00", filters: dict | None = None) -> None:
    """Blocking loop: run discovery every day at HH:MM local time.

    Deliberately dependency-free — survives clock drift and long runs by
    recomputing the next fire time after every cycle.
    """
    while True:
        wait_s = seconds_until(at)
        print(f"[autopilot] Next run at {at} ({wait_s / 3600:.1f}h from now). Sleeping.")
        time.sleep(wait_s)
        try:
            summary = run_daily_discovery(role, niche, market, github_username, filters=filters)
            print(f"[autopilot] Run complete: {summary}")
        except Exception as exc:
            print(f"[autopilot] Run failed: {exc}")
            notify.send_alert(f"JobHunter autopilot run failed: {exc}")
        time.sleep(61)   # step past the fire minute before recomputing


def seconds_until(at: str) -> float:
    """Seconds until the next local occurrence of HH:MM."""
    hour, minute = (int(p) for p in at.split(":"))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


# ── Dedupe (seen-jobs store) ───────────────────────────────────────────────────

def _load_seen() -> dict:
    if SEEN_PATH.exists():
        try:
            return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_seen(seen: dict) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)).isoformat()
    pruned = {k: v for k, v in seen.items() if v >= cutoff}
    SEEN_PATH.write_text(json.dumps(pruned, indent=1), encoding="utf-8")


def _split_new_jobs(scored: list[dict], seen: dict) -> tuple[list[dict], dict]:
    """Partition scored jobs into never-seen-before ones; refresh last-seen stamps."""
    now = datetime.now(timezone.utc).isoformat()
    new_jobs = []
    for job in scored:
        job_id = str(job.get("job_id") or job.get("id") or job.get("url") or "")
        if not job_id:
            continue
        if job_id not in seen:
            new_jobs.append(job)
        seen[job_id] = now
    return new_jobs, seen


# ── Digest rendering ───────────────────────────────────────────────────────────

def build_digest(new_jobs: list[dict], total_scored: int, role: str, market: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    high = [j for j in new_jobs if j.get("priority") == "high"]

    lines = [
        f"# JobHunter Daily Digest — {today}",
        "",
        f"**Search:** {role} · {market}",
        f"**Scored today:** {total_scored} | **New since last run:** {len(new_jobs)} | **High priority:** {len(high)}",
        "",
    ]

    if not new_jobs:
        lines.append("No new jobs today — every discovered posting was already seen on a previous run.")
        return "\n".join(lines)

    lines.append("## Top new matches")
    lines.append("")
    for j in new_jobs[:DIGEST_TOP_N]:
        score = j.get("relevance_score", "?")
        flag = "🔥 " if j.get("priority") == "high" else ""
        lines.append(f"### {flag}{j.get('title', 'Unknown role')} — {j.get('company', '?')}")
        lines.append(f"- **Score:** {score}/100 · **Platform:** {j.get('platform', '?')} · **Seniority:** {j.get('seniority_level', '?')}")
        if j.get("match_reasons"):
            lines.append(f"- **Why it fits:** {'; '.join(j['match_reasons'][:2])}")
        if j.get("application_note"):
            lines.append(f"- **Angle:** {j['application_note']}")
        if j.get("url"):
            lines.append(f"- {j['url']}")
        lines.append("")

    if len(new_jobs) > DIGEST_TOP_N:
        lines.append(f"…and {len(new_jobs) - DIGEST_TOP_N} more — check outputs/digests/ for the full list.")

    return "\n".join(lines)


def build_email_subject(new_count: int, high_count: int) -> str:
    today = datetime.now().strftime("%d %b")
    if new_count == 0:
        return f"JobHunter Daily — nothing new ({today})"
    high = f", {high_count} high priority" if high_count else ""
    return f"JobHunter Daily — {new_count} new match{'es' if new_count != 1 else ''}{high} ({today})"


def build_compact_summary(new_jobs: list[dict], total_scored: int, role: str) -> str:
    """Compact plain-text version for the phone notification."""
    high = [j for j in new_jobs if j.get("priority") == "high"]
    head = (
        f"🎯 JobHunter daily — {role}\n"
        f"{total_scored} scored · {len(new_jobs)} new · {len(high)} high priority\n"
    )
    if not new_jobs:
        return head + "\nNothing new today."

    rows = []
    for j in new_jobs[:5]:
        flag = "🔥" if j.get("priority") == "high" else "•"
        rows.append(
            f"{flag} {j.get('relevance_score', '?')}/100 {j.get('title', '?')} — {j.get('company', '?')}\n"
            f"   {j.get('url', '')}"
        )
    return head + "\n" + "\n".join(rows)


def _save_digest(markdown: str) -> Path:
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


# ── Profile context ────────────────────────────────────────────────────────────

def postprocess_run(
    scored: list[dict],
    role: str,
    market: str,
    push_fn=None,
) -> dict:
    """Dedupe → digest → email. Callable from the runner after discovery streaming.

    push_fn: optional callable(str) that routes status lines to SSE.
    Returns the last_run summary dict.
    """
    seen = _load_seen()
    new_jobs, seen = _split_new_jobs(scored, seen)
    _save_seen(seen)

    high_count = sum(1 for j in new_jobs if j.get("priority") == "high")
    if push_fn:
        push_fn(f"[autopilot] {len(new_jobs)} new jobs ({high_count} high priority) — building digest…")

    digest_md = build_digest(new_jobs, total_scored=len(scored), role=role, market=market)
    digest_path = _save_digest(digest_md)

    delivered = notify.send_digest(
        subject=build_email_subject(len(new_jobs), high_count),
        markdown_body=digest_md,
        compact_text=build_compact_summary(new_jobs, len(scored), role),
    )
    if push_fn:
        ok = delivered.get("email", False)
        push_fn(f"[autopilot] Digest {'delivered ✓' if ok else 'email failed ✗'} — "
                f"{len(new_jobs)} new, {high_count} high priority")

    return {
        "ran_at":       datetime.now(timezone.utc).isoformat(),
        "total_scored": len(scored),
        "new_jobs":     len(new_jobs),
        "high_priority": high_count,
        "digest_path":  str(digest_path),
        "delivered":    delivered,
    }


def _inject_profile_context(state: GlobalState) -> None:
    """Reuse the freshest GitHub audit from any saved session so relevance
    scoring stays profile-aware without re-running the audit every morning."""
    if not SESSION_DIR.exists():
        return
    sessions = sorted(SESSION_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in sessions:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("github_audit"):
            state["github_audit"] = data["github_audit"]
            state["repo_depth_reports"] = data.get("repo_depth_reports") or []
            state["gap_analysis"] = data.get("gap_analysis") or {}
            return
