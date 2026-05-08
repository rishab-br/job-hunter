from collections import Counter
from datetime import date, datetime, timezone

from skills import file_tools
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    applications = state.get("applications") or []
    statuses = state.get("application_statuses") or {}
    followup_queue = state.get("followup_queue") or []
    ghosted = state.get("ghosted_applications") or []

    logs.append("[pipeline_reporter] Generating pipeline report...")

    report = _build_report(state, applications, statuses, followup_queue, ghosted)
    filename = f"pipeline_{date.today().isoformat()}.md"
    saved_path = file_tools.save_text(report, "reports", filename)

    logs.append(f"[pipeline_reporter] Report saved → {saved_path}")

    pipeline_summary = {
        "report_path": str(saved_path),
        "total_applications": len(applications),
        "status_breakdown": dict(Counter(statuses.values())),
        "ghosted_count": len(ghosted),
        "followups_pending": sum(1 for f in followup_queue if f.get("approved") is None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        **state,
        "pipeline_report": pipeline_summary,
        "logs": logs,
    }


def _build_report(
    state: GlobalState,
    applications: list[dict],
    statuses: dict[str, str],
    followup_queue: list[dict],
    ghosted: list[str],
) -> str:
    today = date.today().isoformat()
    total = len(applications)

    status_counts = Counter(statuses.get(app.get("job_id"), "applied") for app in applications)

    responded = sum(
        v for k, v in status_counts.items()
        if k in ("viewed", "shortlisted", "interview_scheduled", "rejected")
    )
    response_rate = round((responded / total * 100), 1) if total else 0

    interviews = status_counts.get("interview_scheduled", 0)
    shortlisted = status_counts.get("shortlisted", 0)
    rejected = status_counts.get("rejected", 0)
    viewed = status_counts.get("viewed", 0)
    applied = status_counts.get("applied", 0)

    platform_counts = Counter(app.get("platform", "unknown") for app in applications)
    followups_pending = [f for f in followup_queue if f.get("approved") is None]

    # Top companies by application status quality
    high_value = [
        app for app in applications
        if statuses.get(app.get("job_id")) in ("shortlisted", "interview_scheduled")
    ]

    lines = [
        f"# Job Application Pipeline Report",
        f"**Generated:** {today}  |  **Target Role:** {state['target_role']}  |  **Market:** {state['target_market']}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Applications | {total} |",
        f"| Response Rate | {response_rate}% |",
        f"| Interviews Scheduled | {interviews} |",
        f"| Shortlisted | {shortlisted} |",
        f"| Rejected | {rejected} |",
        f"| Viewed / Under Review | {viewed} |",
        f"| Still Applied (no update) | {applied} |",
        f"| Ghosted (21+ days silent) | {len(ghosted)} |",
        f"",
        f"---",
        f"",
        f"## Applications by Platform",
        f"",
    ]

    for platform, count in platform_counts.most_common():
        lines.append(f"- **{platform.title()}**: {count} application(s)")

    lines += [
        f"",
        f"---",
        f"",
        f"## High-Value Opportunities",
        f"",
    ]

    if high_value:
        for app in high_value:
            status = statuses.get(app.get("job_id"), "applied")
            lines.append(f"- **{app.get('company')}** — {app.get('job_title')} → `{status}`")
    else:
        lines.append("_No shortlisted or interview-scheduled applications yet._")

    lines += [
        f"",
        f"---",
        f"",
        f"## Pending Follow-ups ({len(followups_pending)})",
        f"",
    ]

    if followups_pending:
        for f in followups_pending:
            lines += [
                f"### {f.get('company')} — {f.get('job_title')}",
                f"Days since applying: **{f.get('days_since_application')}** | Status: `{f.get('current_status')}`",
                f"",
                f"**Draft:**",
                f"```",
                f"{f.get('followup_draft', '').strip()}",
                f"```",
                f"",
            ]
    else:
        lines.append("_No follow-ups pending._")

    lines += [
        f"",
        f"---",
        f"",
        f"## Full Application Log",
        f"",
        f"| Company | Role | Platform | Status | Submitted |",
        f"|---------|------|----------|--------|-----------|",
    ]

    for app in sorted(applications, key=lambda a: a.get("submitted_at", ""), reverse=True):
        job_id = app.get("job_id", "")
        status = statuses.get(job_id, "applied")
        submitted = (app.get("submitted_at") or "")[:10]
        lines.append(
            f"| {app.get('company')} | {app.get('job_title')} "
            f"| {app.get('platform')} | `{status}` | {submitted} |"
        )

    return "\n".join(lines)
