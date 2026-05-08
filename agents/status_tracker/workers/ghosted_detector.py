from datetime import datetime, timezone

from state import GlobalState

GHOST_THRESHOLD_DAYS = 21
ACTIVE_STATUSES = {"shortlisted", "interview_scheduled"}


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    applications = state.get("applications") or []
    statuses = state.get("application_statuses") or {}
    ghosted = list(state.get("ghosted_applications") or [])

    now = datetime.now(timezone.utc)
    existing_ghosted = set(ghosted)
    newly_ghosted: list[str] = []

    for app in applications:
        job_id = app.get("job_id")
        if not job_id or job_id in existing_ghosted:
            continue

        # Skip anything with a positive status update
        current_status = statuses.get(job_id, "applied")
        if current_status in ACTIVE_STATUSES:
            continue

        submitted_at = app.get("submitted_at")
        if not submitted_at:
            continue

        submitted_dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        days_elapsed = (now - submitted_dt).days

        if days_elapsed >= GHOST_THRESHOLD_DAYS:
            newly_ghosted.append(job_id)
            ghosted.append(job_id)
            logs.append(
                f"[ghosted_detector] GHOSTED: {app.get('company')} — {app.get('job_title')} "
                f"({days_elapsed} days, status: {current_status})"
            )

    if not newly_ghosted:
        logs.append("[ghosted_detector] No newly ghosted applications detected.")
    else:
        logs.append(
            f"[ghosted_detector] {len(newly_ghosted)} application(s) flagged as ghosted. "
            f"Total ghosted: {len(ghosted)}"
        )

    return {
        **state,
        "ghosted_applications": ghosted,
        "logs": logs,
    }
