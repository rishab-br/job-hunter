from typing import Any, Optional
from typing_extensions import TypedDict
from enum import Enum


class SystemPhase(str, Enum):
    IDLE = "idle"
    GITHUB_ANALYSIS = "github_analysis"
    RESUME_REVIEW = "resume_review"
    JOB_DISCOVERY = "job_discovery"
    APPLYING = "applying"
    TRACKING = "tracking"
    OFFER_EVALUATION = "offer_evaluation"
    INTERVIEW_PREP = "interview_prep"


class GlobalState(TypedDict):
    # ── User config ────────────────────────────────────────────────────────────
    github_username: str
    target_role: str
    target_market: str
    target_niche: str

    # ── System bookkeeping ─────────────────────────────────────────────────────
    current_phase: SystemPhase
    active_lead: Optional[str]
    errors: list[str]
    logs: list[str]
    github_token: Optional[str]       # OAuth token for this user (not committed)

    # ── GitHub Intelligence ────────────────────────────────────────────────────
    github_profile: Optional[dict[str, Any]]
    github_repos: Optional[list[dict[str, Any]]]
    github_audit: Optional[dict[str, Any]]
    repo_depth_reports: Optional[list[dict[str, Any]]]
    trend_data: Optional[dict[str, Any]]
    gap_analysis: Optional[dict[str, Any]]
    improvement_plan: Optional[list[dict[str, Any]]]

    # ── Resume Reviewer ────────────────────────────────────────────────────────
    resume_text: Optional[str]             # raw text extracted from uploaded resume
    resume_review: Optional[dict[str, Any]]  # structured LLM review output

    # ── Job Discovery ──────────────────────────────────────────────────────────
    # LLM-expanded search titles — e.g. ["AI Engineer", "AI Developer", "GenAI Engineer"]
    # Populated by role_expander; scrapers iterate over all of them.
    search_roles: Optional[list[str]]

    # discovery_filters keys:
    #   max_seniority: "fresher"|"junior"|"mid"|"senior"|"lead"  (default "lead" = no cap)
    #   locations: list[str]   e.g. ["Bangalore", "Hyderabad", "Remote"]  ([] = no filter)
    #   remote_ok: bool        include remote jobs regardless of location filter
    #   min_score: int         drop scored jobs below this threshold (0-100, default 0)
    discovery_filters: Optional[dict[str, Any]]
    discovered_jobs: Optional[list[dict[str, Any]]]
    analyzed_jds: Optional[list[dict[str, Any]]]
    scored_jobs: Optional[list[dict[str, Any]]]

    # ── Application Engine ─────────────────────────────────────────────────────
    applications: Optional[list[dict[str, Any]]]
    pending_approvals: Optional[list[dict[str, Any]]]

    # ── Status Tracker ─────────────────────────────────────────────────────────
    application_statuses: Optional[dict[str, str]]
    followup_queue: Optional[list[dict[str, Any]]]
    ghosted_applications: Optional[list[str]]
    pipeline_report: Optional[dict[str, Any]]

    # ── Offer Intelligence ─────────────────────────────────────────────────────
    active_offers: Optional[list[dict[str, Any]]]
    offer_evaluations: Optional[list[dict[str, Any]]]
    negotiation_scripts: Optional[list[dict[str, Any]]]
    response_coaching: Optional[list[dict[str, Any]]]

    # ── Interview Prep ─────────────────────────────────────────────────────────
    interview_prep_target: Optional[dict[str, Any]]   # job being prepped for
    interview_prep_sessions: Optional[list[dict[str, Any]]]  # completed sessions


def initial_state(
    github_username: str,
    target_role: str,
    target_market: str,
    target_niche: str,
) -> GlobalState:
    return GlobalState(
        github_username=github_username,
        target_role=target_role,
        target_market=target_market,
        target_niche=target_niche,
        current_phase=SystemPhase.IDLE,
        active_lead=None,
        errors=[],
        logs=[],
        github_token=None,
        github_profile=None,
        github_repos=None,
        github_audit=None,
        repo_depth_reports=None,
        trend_data=None,
        gap_analysis=None,
        improvement_plan=None,
        resume_text=None,
        resume_review=None,
        search_roles=None,
        discovery_filters=None,
        discovered_jobs=None,
        analyzed_jds=None,
        scored_jobs=None,
        applications=None,
        pending_approvals=None,
        application_statuses=None,
        followup_queue=None,
        ghosted_applications=None,
        pipeline_report=None,
        active_offers=None,
        offer_evaluations=None,
        negotiation_scripts=None,
        response_coaching=None,
        interview_prep_target=None,
        interview_prep_sessions=None,
    )
