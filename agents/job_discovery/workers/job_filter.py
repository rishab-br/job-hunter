"""Post-analysis filter — runs after jd_analyzer, before relevance_scorer.

Drops jobs the user has explicitly ruled out before spending LLM tokens
scoring them. Three independent axes:

  seniority  — "fresher" sees only junior/unknown; "mid" sees up to mid; etc.
  location   — keeps jobs in the user's preferred cities + remote if remote_ok
  min_score  — applied AFTER relevance_scorer; the scorer reads this from state
               and the CLI summary omits sub-threshold jobs (handled in scorer)

Filtering is lenient by design: when a field is missing or "unknown" the job
passes, so genuine unknowns never disappear silently.
"""
from state import GlobalState

# Seniority hierarchy — a job at level N is shown to users who accept up to N.
_SENIORITY_RANK = {
    "fresher": 0,
    "junior":  1,
    "mid":     2,
    "senior":  3,
    "lead":    4,
    "unknown": -1,   # unknown always passes
}

_MAX_SENIORITY_DEFAULT = "lead"    # no cap when unset
_REMOTE_KEYWORDS = {"remote", "work from home", "wfh", "anywhere", "hybrid"}


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    filters = state.get("discovery_filters") or {}

    if not filters:
        logs.append("[job_filter] No filters configured — passing all jobs.")
        return {**state, "logs": logs}

    analyzed   = list(state.get("analyzed_jds") or [])
    discovered = {j["id"]: j for j in (state.get("discovered_jobs") or [])}

    before = len(analyzed)
    kept_analyses, drop_log = [], []

    for jd in analyzed:
        job_meta = discovered.get(jd.get("job_id"), {})
        reason = _should_drop(jd, job_meta, filters)
        if reason:
            drop_log.append(f"  drop [{reason}] {job_meta.get('title', '?')} — {job_meta.get('company', '?')}")
        else:
            kept_analyses.append(jd)

    kept_ids = {j["job_id"] for j in kept_analyses}
    kept_jobs = [j for j in (state.get("discovered_jobs") or []) if j["id"] in kept_ids]

    after = len(kept_analyses)
    logs.append(
        f"[job_filter] {before - after} job(s) filtered out, {after} remain. "
        f"Filters: {_describe(filters)}"
    )
    if drop_log:
        logs.extend(drop_log[:10])    # cap noise at 10 lines
        if len(drop_log) > 10:
            logs.append(f"  … and {len(drop_log) - 10} more dropped.")

    return {
        **state,
        "analyzed_jds":   kept_analyses,
        "discovered_jobs": kept_jobs,
        "logs": logs,
    }


# ── Per-job predicate ──────────────────────────────────────────────────────────

def _should_drop(jd: dict, meta: dict, filters: dict) -> str | None:
    """Return a short reason string to drop, or None to keep."""

    # ── Seniority ──────────────────────────────────────────────────────────────
    max_sen = filters.get("max_seniority", _MAX_SENIORITY_DEFAULT)
    job_sen = (jd.get("seniority_level") or "unknown").lower()
    if job_sen != "unknown":
        max_rank = _SENIORITY_RANK.get(max_sen.lower(), 4)
        job_rank = _SENIORITY_RANK.get(job_sen, -1)
        if job_rank > max_rank:
            return f"seniority={job_sen} > max={max_sen}"

    # ── Location ───────────────────────────────────────────────────────────────
    allowed_locations: list[str] = filters.get("locations") or []
    remote_ok: bool = filters.get("remote_ok", True)

    if allowed_locations:
        location_str = (meta.get("location") or "").lower()
        is_remote = (
            jd.get("remote_friendly") is True
            or any(kw in location_str for kw in _REMOTE_KEYWORDS)
        )
        if remote_ok and is_remote:
            pass    # remote always passes when remote_ok
        elif not location_str:
            pass    # unknown location passes (lenient)
        elif not any(loc.lower() in location_str for loc in allowed_locations):
            return f"location='{meta.get('location')}' not in {allowed_locations}"

    return None


# ── Filter description for logs ────────────────────────────────────────────────

def _describe(filters: dict) -> str:
    parts = []
    if filters.get("max_seniority"):
        parts.append(f"max_seniority={filters['max_seniority']}")
    if filters.get("locations"):
        locs = ", ".join(filters["locations"])
        remote = "remote_ok" if filters.get("remote_ok", True) else "no_remote"
        parts.append(f"locations=[{locs}] ({remote})")
    if filters.get("min_score"):
        parts.append(f"min_score={filters['min_score']}")
    return ", ".join(parts) or "none"
