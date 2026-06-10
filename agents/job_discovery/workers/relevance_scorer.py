import json
from skills import llm
from state import GlobalState

BATCH_SIZE = 10

# Embedding pre-filter: when more than this many jobs survive analysis, rank
# them by embedding similarity to the profile and LLM-score only the top K.
# Cuts scoring tokens ~linearly with the discard rate.
PREFILTER_THRESHOLD = 20
PREFILTER_KEEP      = 20


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    discovered_jobs = state.get("discovered_jobs") or []
    analyzed_jds = state.get("analyzed_jds") or []
    audit = state.get("github_audit") or {}
    depth_reports = state.get("repo_depth_reports") or []
    gap_analysis = state.get("gap_analysis") or {}

    if not analyzed_jds:
        logs.append("[relevance_scorer] No analyzed JDs to score.")
        return {**state, "scored_jobs": [], "logs": logs}

    logs.append(f"[relevance_scorer] Scoring {len(analyzed_jds)} jobs against profile...")

    # Build a compact profile summary to send with each scoring batch
    profile_summary = _build_profile_summary(audit, depth_reports, gap_analysis, state)

    # Merge job metadata with analysis for scoring
    analysis_by_id = {a["job_id"]: a for a in analyzed_jds}
    job_meta_by_id = {j["id"]: j for j in discovered_jobs}

    merged = []
    for analysis in analyzed_jds:
        meta = job_meta_by_id.get(analysis["job_id"], {})
        merged.append({**meta, **analysis})

    # Embedding pre-filter — cheap similarity ranking before expensive LLM scoring
    if len(merged) > PREFILTER_THRESHOLD:
        try:
            merged = _embedding_prefilter(merged, profile_summary, PREFILTER_KEEP)
            logs.append(
                f"[relevance_scorer] Embedding pre-filter kept top {len(merged)} "
                f"of {len(analyzed_jds)} jobs for LLM scoring."
            )
        except Exception as exc:
            logs.append(f"[relevance_scorer] Pre-filter unavailable ({exc}) — scoring all jobs.")

    scored: list[dict] = []
    batches = [merged[i : i + BATCH_SIZE] for i in range(0, len(merged), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        logs.append(f"[relevance_scorer] Scoring batch {i + 1}/{len(batches)}...")
        results = _score_batch(batch, profile_summary, state)
        scored.extend(results)

    # Sort by relevance_score descending
    scored.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    high_priority = sum(1 for s in scored if s.get("priority") == "high")
    logs.append(
        f"[relevance_scorer] Done. {high_priority} high-priority matches out of {len(scored)} total."
    )

    return {
        **state,
        "scored_jobs": scored,
        "logs": logs,
    }


def _embedding_prefilter(jobs: list[dict], profile: dict, keep: int) -> list[dict]:
    """Rank jobs by cosine similarity between profile and job embeddings; keep top K."""
    profile_text = (
        f"{profile.get('target_role', '')} {profile.get('target_niche', '')}. "
        f"Languages: {', '.join(profile.get('top_languages') or [])}. "
        f"Strengths: {', '.join(profile.get('existing_strengths') or [])}."
    )
    job_texts = [
        f"{j.get('title', '')} at {j.get('company', '')}. "
        f"Skills: {', '.join(j.get('must_have_skills') or [])}. "
        f"{j.get('role_summary') or ''}"
        for j in jobs
    ]

    vectors = llm.embed_texts([profile_text] + job_texts)
    profile_vec, job_vecs = vectors[0], vectors[1:]

    ranked = sorted(
        zip(jobs, job_vecs),
        key=lambda pair: llm.cosine_similarity(profile_vec, pair[1]),
        reverse=True,
    )
    return [job for job, _ in ranked[:keep]]


def _build_profile_summary(audit: dict, depth_reports: list, gap: dict, state: GlobalState) -> dict:
    return {
        "target_role": state["target_role"],
        "target_niche": state["target_niche"],
        "target_market": state["target_market"],
        "overall_github_score": audit.get("overall_score"),
        "top_languages": audit.get("top_languages", []),
        "existing_strengths": gap.get("existing_strengths_to_highlight", []),
        "missing_critical_skills": gap.get("missing_critical_skills", []),
        "showcase_repos": [
            r["name"] for r in depth_reports if r.get("showcase_worthy")
        ],
    }


def _score_batch(
    jobs: list[dict],
    profile: dict,
    state: GlobalState,
) -> list[dict]:
    slim_jobs = [
        {
            "job_id": j.get("job_id") or j.get("id"),
            "title": j.get("title"),
            "company": j.get("company"),
            "platform": j.get("platform"),
            "url": j.get("url"),
            "seniority_level": j.get("seniority_level"),
            "must_have_skills": j.get("must_have_skills", []),
            "nice_to_have_skills": j.get("nice_to_have_skills", []),
            "remote_friendly": j.get("remote_friendly"),
            "estimated_salary_range": j.get("estimated_salary_range"),
            "red_flags": j.get("red_flags", []),
            "company_signals": j.get("company_signals", {}),
            "role_summary": j.get("role_summary"),
        }
        for j in jobs
    ]

    system = (
        "You are a senior career advisor helping a software developer identify their best-fit job opportunities. "
        "You score jobs based on realistic match between the candidate's profile and the role requirements."
    )
    user = f"""Score each job for relevance to this candidate profile.

--- CANDIDATE PROFILE ---
{json.dumps(profile, indent=2)}

--- JOBS TO SCORE ---
{json.dumps(slim_jobs, indent=2)}

Return a JSON array with one object per job in this exact structure:
{{
  "job_id": "same id as input",
  "title": "job title",
  "company": "company name",
  "platform": "platform",
  "url": "job url",
  "relevance_score": integer 0-100,
  "match_reasons": ["reason 1", "reason 2"],
  "gap_reasons": ["gap 1", "gap 2"],
  "salary_range": "string or null",
  "seniority_level": "junior/mid/senior/lead",
  "remote_friendly": true or false,
  "recommended": true or false,
  "priority": "high" or "medium" or "low",
  "application_note": "1 sentence on what to emphasise in the application"
}}

Scoring guide:
- 80-100: Strong match, candidate should definitely apply
- 60-79: Good match with minor gaps, worth applying
- 40-59: Partial match, stretch role
- Below 40: Significant mismatch

Mark recommended=true for scores >= 65. Set priority=high for scores >= 75."""

    return llm.call_json(system, user, max_tokens=4096)
