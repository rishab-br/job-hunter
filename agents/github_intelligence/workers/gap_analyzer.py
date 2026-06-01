import json
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    logs.append("[gap_analyzer] Comparing profile against market trends...")

    audit = state.get("github_audit") or {}
    depth_reports = state.get("repo_depth_reports") or []
    trend_data = state.get("trend_data") or {}

    # Summarise what the user currently has
    current_languages = audit.get("top_languages", [])
    # Normalize topics to strings — LLM sometimes returns dicts instead of plain strings
    if not isinstance(depth_reports, list):
        depth_reports = []
    current_topics = list({
        topic if isinstance(topic, str) else topic.get("name", str(topic))
        for r in depth_reports
        if isinstance(r, dict)
        for topic in (r.get("topics") or [])
        if topic
    })
    showcase_repos = [r["name"] for r in depth_reports if isinstance(r, dict) and r.get("showcase_worthy")]
    weak_repos = [r["name"] for r in depth_reports if isinstance(r, dict) and r.get("completeness_score", 100) < 50]

    depth_summary = json.dumps([
        {
            "name": r["name"],
            "completeness_score": r.get("completeness_score"),
            "showcase_worthy": r.get("showcase_worthy"),
            "improvements_needed": r.get("improvements_needed"),
        }
        for r in depth_reports if isinstance(r, dict)
    ], indent=2)

    system = (
        "You are a senior engineering career coach specialising in helping developers "
        "close the gap between their current profile and what top employers are looking for."
    )
    user = f"""Perform a gap analysis between this developer's current GitHub profile and the market requirements.

--- CURRENT PROFILE ---
Profile audit:
{json.dumps(audit, indent=2)}

Current languages/technologies: {current_languages}
Current GitHub topics across repos: {current_topics}
Showcase-worthy repos: {showcase_repos}
Weak repos (completeness < 50): {weak_repos}

Repo depth summary:
{depth_summary}

--- MARKET REQUIREMENTS ---
{json.dumps(trend_data, indent=2)}

--- TARGET ---
Role: {state["target_role"]}
Niche: {state["target_niche"]}
Market: {state["target_market"]}

Return a JSON object with exactly this structure:
{{
  "missing_critical_skills": ["skill that is must-have but absent from profile"],
  "missing_good_to_have_skills": ["skill that is valued but not present"],
  "missing_project_types": [
    {{"project_type": "name", "why_it_matters": "recruiter perspective"}}
  ],
  "weak_repos_to_fix": [
    {{"repo_name": "name", "top_issues": ["issue1", "issue2"]}}
  ],
  "profile_presentation_gaps": ["gap in bio/README/topics/pinned repos"],
  "existing_strengths_to_highlight": ["strength that aligns with market"],
  "gap_severity": "high" or "medium" or "low",
  "summary": "3-4 sentence honest assessment of where the developer stands vs the market"
}}"""

    gap_analysis = llm.call_json(system, user, max_tokens=3000)
    logs.append(
        f"[gap_analyzer] Done. Gap severity: {gap_analysis.get('gap_severity')}. "
        f"{len(gap_analysis.get('missing_critical_skills', []))} critical skills missing."
    )

    return {
        **state,
        "gap_analysis": gap_analysis,
        "logs": logs,
    }
