"""
Read-only data endpoints — extract structured slices of GlobalState
for each frontend screen.
"""
from fastapi import APIRouter, HTTPException
from backend import runner

router = APIRouter(prefix="/api/sessions", tags=["data"])


def _load(thread_id: str) -> dict:
    state = runner.load_session(thread_id)
    if not state:
        raise HTTPException(404, f"Session '{thread_id}' not found")
    return state


# ── GitHub Intel ──────────────────────────────────────────────────────────────

@router.get("/{thread_id}/audit")
async def get_audit(thread_id: str):
    state = _load(thread_id)
    return {
        "github_audit":      state.get("github_audit"),
        "repo_depth_reports": state.get("repo_depth_reports"),
        "trend_data":        state.get("trend_data"),
        "gap_analysis":      state.get("gap_analysis"),
        "improvement_plan":  state.get("improvement_plan"),
        "github_username":   state.get("github_username"),
    }


# ── Job Discovery ─────────────────────────────────────────────────────────────

@router.get("/{thread_id}/jobs")
async def get_jobs(thread_id: str):
    state = _load(thread_id)
    scored = state.get("scored_jobs") or []
    # Merge analyzed JD data for richer display
    analyzed = {j.get("job_id"): j for j in (state.get("analyzed_jds") or [])}
    jobs = []
    for j in scored:
        jid = j.get("job_id", "")
        jd  = analyzed.get(jid, {})
        # LLM returns "title" not "job_title" — normalise here
        title = j.get("title") or j.get("job_title") or ""
        jobs.append({
            "job_id":          jid,
            "company":         j.get("company", ""),
            "job_title":       title,
            "location":        j.get("location", ""),
            "platform":        j.get("platform", ""),
            "url":             j.get("url", ""),
            "relevance_score": j.get("relevance_score", 0),
            "priority":        j.get("priority", "low"),
            "recommended":     j.get("recommended", False),
            "seniority_level": j.get("seniority_level") or jd.get("seniority_level", ""),
            "role_summary":    j.get("role_summary")    or jd.get("role_summary", ""),
            "red_flags":       j.get("red_flags")       or jd.get("red_flags", []),
        })
    return {"jobs": jobs, "total": len(jobs)}


# ── Applications ──────────────────────────────────────────────────────────────

@router.get("/{thread_id}/applications")
async def get_applications(thread_id: str):
    state = _load(thread_id)
    apps = state.get("applications") or []
    statuses = state.get("application_statuses") or {}
    enriched = [
        {**a, "status": statuses.get(a.get("job_id"), "applied")}
        for a in apps
    ]
    return {"applications": enriched, "total": len(enriched)}


# ── Offers ────────────────────────────────────────────────────────────────────

@router.get("/{thread_id}/offers")
async def get_offers(thread_id: str):
    state = _load(thread_id)
    offers = state.get("active_offers") or []
    evals = {e.get("offer_id"): e for e in (state.get("offer_evaluations") or [])}
    scripts = {s.get("offer_id"): s for s in (state.get("negotiation_scripts") or [])}
    coaching = {c.get("offer_id"): c for c in (state.get("response_coaching") or [])}

    enriched = []
    for o in offers:
        oid = o.get("offer_id", "")
        ev = evals.get(oid, {})
        sc = scripts.get(oid, {})
        co = coaching.get(oid, {})
        parsed = ev.get("parsed_offer") or {}
        bench = ev.get("market_benchmark") or {}
        risk = ev.get("risk_assessment") or {}
        counter = ev.get("counter_recommendation") or {}
        enriched.append({
            "offer_id":          oid,
            "company":           o.get("company", ""),
            "job_title":         o.get("job_title", ""),
            "received_date":     o.get("received_date", ""),
            "deadline_date":     o.get("deadline_date"),
            "total_ctc":         parsed.get("total_ctc_annual", ""),
            "fair_value_range":  bench.get("fair_value_range", ""),
            "offer_percentile":  bench.get("offer_percentile", ""),
            "risk_level":        risk.get("overall_risk_level", ""),
            "counter_ask":       counter.get("counter_ask", ""),
            "walk_away_floor":   counter.get("walk_away_floor", ""),
            "script_path":       sc.get("script_path", ""),
            "coaching_move":     co.get("recommended_move", ""),
        })
    return {"offers": enriched, "total": len(enriched)}


# ── Interview Prep ────────────────────────────────────────────────────────────

@router.get("/{thread_id}/prep")
async def get_prep(thread_id: str):
    state = _load(thread_id)
    sessions = state.get("interview_prep_sessions") or []
    return {"sessions": sessions, "total": len(sessions)}
