import json
from datetime import datetime, timezone

from skills import llm
from state import GlobalState

FOLLOWUP_THRESHOLD_DAYS = 7   # draft follow-up after this many days with no response
FOLLOWUP_STATUSES = {"applied", "viewed"}  # statuses that warrant a follow-up


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    applications = state.get("applications") or []
    statuses = state.get("application_statuses") or {}
    followup_queue = list(state.get("followup_queue") or [])

    now = datetime.now(timezone.utc)
    existing_followup_ids = {f["job_id"] for f in followup_queue}

    candidates = []
    for app in applications:
        job_id = app.get("job_id")
        if job_id in existing_followup_ids:
            continue

        status = statuses.get(job_id, "applied")
        if status not in FOLLOWUP_STATUSES:
            continue

        submitted_at = app.get("submitted_at")
        if not submitted_at:
            continue

        submitted_dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        days_elapsed = (now - submitted_dt).days

        if days_elapsed >= FOLLOWUP_THRESHOLD_DAYS:
            candidates.append({**app, "days_elapsed": days_elapsed, "current_status": status})

    if not candidates:
        logs.append("[followup_scheduler] No applications due for follow-up.")
        return {**state, "followup_queue": followup_queue, "logs": logs}

    logs.append(f"[followup_scheduler] Drafting follow-ups for {len(candidates)} application(s)...")

    for app in candidates:
        draft = _draft_followup(app, state)
        followup_queue.append({
            "job_id": app.get("job_id"),
            "company": app.get("company"),
            "job_title": app.get("job_title"),
            "platform": app.get("platform"),
            "days_since_application": app["days_elapsed"],
            "current_status": app["current_status"],
            "followup_draft": draft,
            "approved": None,
            "created_at": now.isoformat(),
        })
        logs.append(f"[followup_scheduler] Follow-up drafted for {app.get('company')} — {app.get('job_title')}")

    return {
        **state,
        "followup_queue": followup_queue,
        "logs": logs,
    }


def _draft_followup(app: dict, state: GlobalState) -> str:
    system = (
        "You are a professional career coach helping a developer write a polite, "
        "brief follow-up email after submitting a job application. "
        "The tone must be confident but not pushy."
    )
    user = f"""Write a follow-up email for this application.

Application details:
{json.dumps({
    "company": app.get("company"),
    "job_title": app.get("job_title"),
    "days_since_applying": app["days_elapsed"],
    "current_status": app["current_status"],
}, indent=2)}

Candidate: {state["github_username"]} applying for {state["target_role"]}

Instructions:
1. Subject line first (prefix with "Subject: ")
2. 3-4 sentences max — reiterate interest, reference specific role, politely ask for status update
3. Mention one concrete achievement or skill relevant to the role
4. Professional closing
5. Do not grovel or apologise for following up

Return ONLY the email (subject + body). No meta-commentary."""

    return llm.call(system, user, max_tokens=500)
