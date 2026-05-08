from typing import Any, Optional
from typing_extensions import TypedDict
from enum import Enum


class SystemPhase(str, Enum):
    IDLE = "idle"
    GITHUB_ANALYSIS = "github_analysis"
    JOB_DISCOVERY = "job_discovery"
    APPLYING = "applying"
    TRACKING = "tracking"
    OFFER_EVALUATION = "offer_evaluation"


class GlobalState(TypedDict):
    # ── User config ────────────────────────────────────────────────────────────
    github_username: str
    target_role: str
    target_market: str       # e.g. "India", "US", "Remote"
    target_niche: str        # e.g. "MLOps", "Backend", "Full Stack"

    # ── System bookkeeping ─────────────────────────────────────────────────────
    current_phase: SystemPhase
    active_lead: Optional[str]
    errors: list[str]
    logs: list[str]

    # ── GitHub Intelligence ────────────────────────────────────────────────────
    github_profile: Optional[dict[str, Any]]          # raw profile snapshot
    github_repos: Optional[list[dict[str, Any]]]      # per-repo raw data
    github_audit: Optional[dict[str, Any]]            # Profile Auditor output
    repo_depth_reports: Optional[list[dict[str, Any]]] # Project Depth Analyzer output
    trend_data: Optional[dict[str, Any]]              # Trend Scout output
    gap_analysis: Optional[dict[str, Any]]            # Gap Analyzer output
    improvement_plan: Optional[list[dict[str, Any]]]  # Improvement Planner output

    # ── Job Discovery ──────────────────────────────────────────────────────────
    discovered_jobs: Optional[list[dict[str, Any]]]   # raw listings from scrapers
    analyzed_jds: Optional[list[dict[str, Any]]]      # JD Analyzer output
    scored_jobs: Optional[list[dict[str, Any]]]       # Relevance Scorer output

    # ── Application Engine ─────────────────────────────────────────────────────
    applications: Optional[list[dict[str, Any]]]      # submitted applications
    pending_approvals: Optional[list[dict[str, Any]]] # awaiting human confirm

    # ── Status Tracker ─────────────────────────────────────────────────────────
    application_statuses: Optional[dict[str, str]]    # app_id → status
    followup_queue: Optional[list[dict[str, Any]]]
    ghosted_applications: Optional[list[str]]         # app_ids gone cold
    pipeline_report: Optional[dict[str, Any]]

    # ── Offer Intelligence ─────────────────────────────────────────────────────
    active_offers: Optional[list[dict[str, Any]]]
    offer_evaluations: Optional[list[dict[str, Any]]]
    negotiation_scripts: Optional[list[dict[str, Any]]]
    response_coaching: Optional[list[dict[str, Any]]]


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
        github_profile=None,
        github_repos=None,
        github_audit=None,
        repo_depth_reports=None,
        trend_data=None,
        gap_analysis=None,
        improvement_plan=None,
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
    )
