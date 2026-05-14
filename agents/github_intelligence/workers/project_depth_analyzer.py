import json
from skills import github_tools, llm
from state import GlobalState

MAX_REPOS_TO_ANALYZE = 15


def run(state: GlobalState) -> GlobalState:
    username = state["github_username"]
    repos: list[dict] = state.get("github_repos") or []
    logs = list(state.get("logs") or [])
    logs.append(f"[project_depth_analyzer] Analyzing top repos for {username}...")

    # Score and rank repos: weight stars + recency, skip forks
    def repo_priority(r: dict) -> float:
        recency_score = max(0, 180 - (github_tools.days_since(r["last_pushed"]) or 999))
        return r["stars"] * 2 + recency_score * 0.5

    ranked = sorted(repos, key=repo_priority, reverse=True)[:MAX_REPOS_TO_ANALYZE]

    # Enrich top repos with README content
    token = state.get("github_token")
    enriched = []
    for r in ranked:
        readme = github_tools.get_readme_content(username, r["name"], token=token)
        readme_len = len(readme) if readme else 0
        enriched.append({
            **r,
            "readme_length_chars": readme_len,
            "readme_preview": (readme or "")[:800],  # first 800 chars for context
            "days_since_push": github_tools.days_since(r["last_pushed"]),
        })

    logs.append(f"[project_depth_analyzer] Sending {len(enriched)} repos to Claude for depth analysis...")

    system = (
        "You are an expert software engineering mentor reviewing a developer's GitHub portfolio. "
        "You assess project quality, completeness, and market relevance."
    )
    user = f"""Analyze each of these GitHub repositories and return a depth report for each.

Target role: {state["target_role"]}
Target niche: {state["target_niche"]}

Repos to analyze:
{json.dumps(enriched, indent=2)}

Return a JSON array. Each element must have exactly this structure:
{{
  "name": "repo-name",
  "url": "https://github.com/...",
  "language": "Python",
  "topics": ["topic1"],
  "stars": 0,
  "readme_quality": "detailed" or "basic" or "missing",
  "recency": "active" or "recent" or "stale",
  "completeness_score": integer 0-100,
  "showcase_worthy": boolean,
  "strengths": ["strength 1", "strength 2"],
  "improvements_needed": ["improvement 1", "improvement 2"]
}}

Recency guide: active = pushed within 30 days, recent = 30-180 days, stale = 180+ days.
Completeness considers: README quality, description, topics, test signals, deployment evidence, code comments."""

    depth_reports: list[dict] = llm.call_json(system, user, max_tokens=4096)
    logs.append(f"[project_depth_analyzer] Done. {sum(1 for r in depth_reports if r.get('showcase_worthy'))} showcase-worthy repos identified.")

    return {
        **state,
        "repo_depth_reports": depth_reports,
        "logs": logs,
    }
