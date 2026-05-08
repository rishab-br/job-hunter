import json
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    logs.append(f"[trend_scout] Scouting trends for {state['target_role']} / {state['target_niche']}...")

    system = (
        "You are a senior technical hiring manager and industry trends analyst with deep knowledge "
        "of software engineering job markets, GitHub ecosystems, and what skills recruiters actively look for."
    )
    user = f"""Analyze the current job market trends for the following profile:

Target Role: {state["target_role"]}
Target Niche: {state["target_niche"]}
Target Market: {state["target_market"]}

Based on your knowledge of recent job postings, GitHub trending projects, Stack Overflow developer surveys,
and what recruiters in this space are prioritising, return a comprehensive trends report.

Return a JSON object with exactly this structure:
{{
  "target_role": "{state["target_role"]}",
  "target_niche": "{state["target_niche"]}",
  "must_have_skills": ["skill1", "skill2", ...],
  "good_to_have_skills": ["skill1", "skill2", ...],
  "trending_technologies": ["tech1", "tech2", ...],
  "hot_project_types": [
    {{"name": "project type name", "why": "why recruiters value this", "example_stack": ["tech1", "tech2"]}}
  ],
  "github_portfolio_signals": [
    "what signal 1 tells recruiters",
    "what signal 2 tells recruiters"
  ],
  "declining_skills": ["skill that is losing relevance"],
  "certifications_valued": ["cert1", "cert2"],
  "summary": "2-3 sentence overview of the market landscape for this role"
}}"""

    trend_data = llm.call_json(system, user, max_tokens=3000)
    logs.append(
        f"[trend_scout] Done. Found {len(trend_data.get('must_have_skills', []))} must-have "
        f"and {len(trend_data.get('trending_technologies', []))} trending technologies."
    )

    return {
        **state,
        "trend_data": trend_data,
        "logs": logs,
    }
