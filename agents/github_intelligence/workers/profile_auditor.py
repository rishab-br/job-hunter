import json
from skills import github_tools, llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    username = state["github_username"]
    logs = list(state.get("logs") or [])
    logs.append("[profile_auditor] Fetching GitHub profile and repos...")

    token = state.get("github_token")
    profile = github_tools.get_profile(username, token=token)
    repos = github_tools.get_repos(username, token=token)

    # Compute derived stats locally
    active_repos = [
        r for r in repos
        if (github_tools.days_since(r["last_pushed"]) or 999) < 180
    ]
    lang_counts: dict[str, int] = {}
    for r in repos:
        if r["language"]:
            lang_counts[r["language"]] = lang_counts.get(r["language"], 0) + 1
    top_langs = sorted(lang_counts, key=lang_counts.get, reverse=True)[:6]  # type: ignore[arg-type]

    account_age_days = github_tools.days_since(profile["created_at"]) or 0

    audit_input = {
        "profile": profile,
        "total_owned_repos": len(repos),
        "active_repos_last_6_months": len(active_repos),
        "top_languages": top_langs,
        "stars_total": sum(r["stars"] for r in repos),
        "repos_with_topics": sum(1 for r in repos if r["topics"]),
        "repos_with_description": sum(1 for r in repos if r["description"]),
        "repos_with_readme": sum(1 for r in repos if r["has_readme"]),
        "account_age_days": account_age_days,
    }

    system = (
        "You are a senior technical recruiter and GitHub portfolio expert. "
        "You evaluate GitHub profiles for software engineering candidates."
    )
    user = f"""Analyze this GitHub profile data and return a structured audit.

Profile data:
{json.dumps(audit_input, indent=2)}

Target role: {state["target_role"]}
Target niche: {state["target_niche"]}
Target market: {state["target_market"]}

Return a JSON object with exactly this structure:
{{
  "bio_quality": "strong" or "weak" or "missing",
  "has_profile_readme": boolean,
  "active_repo_count": integer,
  "top_languages": [list of language strings],
  "overall_score": integer between 0 and 100,
  "summary": "2-3 sentences describing the profile's current standing for the target role",
  "key_strengths": ["strength 1", "strength 2", "strength 3"],
  "immediate_red_flags": ["flag 1", "flag 2"]
}}"""

    logs.append("[profile_auditor] Running Claude audit...")
    audit = llm.call_json(system, user)
    audit["account_age_days"] = account_age_days

    logs.append(f"[profile_auditor] Done. Overall score: {audit.get('overall_score')}/100")

    return {
        **state,
        "github_profile": profile,
        "github_repos": repos,
        "github_audit": audit,
        "logs": logs,
    }
