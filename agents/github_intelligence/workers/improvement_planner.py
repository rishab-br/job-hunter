import json
from datetime import date
from skills import llm, file_tools
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    logs.append("[improvement_planner] Generating prioritised improvement plan...")

    gap_analysis = state.get("gap_analysis") or {}
    depth_reports = state.get("repo_depth_reports") or []
    trend_data = state.get("trend_data") or {}
    audit = state.get("github_audit") or {}

    system = (
        "You are a senior engineering career coach. You create concrete, actionable portfolio "
        "improvement plans that help developers land roles at top companies."
    )
    user = f"""Create a prioritised, actionable GitHub portfolio improvement plan.

--- GAP ANALYSIS ---
{json.dumps(gap_analysis, indent=2)}

--- MARKET TRENDS ---
Must-have skills: {trend_data.get("must_have_skills", [])}
Hot project types: {trend_data.get("hot_project_types", [])}
GitHub portfolio signals: {trend_data.get("github_portfolio_signals", [])}

--- CURRENT PROFILE SCORE ---
Overall: {audit.get("overall_score")}/100
Bio quality: {audit.get("bio_quality")}

--- TARGET ---
Role: {state["target_role"]}
Niche: {state["target_niche"]}

Return a JSON array of improvement action items, sorted by priority (1 = do first).
Each item must have exactly this structure:
{{
  "priority": integer starting at 1,
  "category": "build_project" or "polish_repo" or "profile_update",
  "title": "short action title",
  "description": "what to do and why it will attract HR attention",
  "effort": "small" or "medium" or "large",
  "impact": "high" or "medium" or "low",
  "specific_actions": ["concrete step 1", "concrete step 2", "concrete step 3"],
  "target_repo_or_area": "repo name or profile area this applies to"
}}

Rules:
- Include 3-5 build_project items with specific project ideas (name, stack, what it demonstrates)
- Include polish_repo items for existing weak repos
- Include profile_update items (bio, pinned repos, README badges, etc.)
- Prioritise high-impact, lower-effort items first
- Be specific — "Add a FastAPI + Redis rate-limiter project showcasing async Python" not "add a backend project"
- Limit to 10-12 total items"""

    improvement_plan: list[dict] = llm.call_json(system, user, max_tokens=4096)
    logs.append(f"[improvement_planner] Generated {len(improvement_plan)} improvement actions.")

    # Save human-readable report to outputs
    report = _render_report(state, improvement_plan, gap_analysis, audit)
    filename = f"improvement_plan_{date.today().isoformat()}.md"
    saved_path = file_tools.save_text(report, "github_intelligence", filename)
    logs.append(f"[improvement_planner] Report saved to {saved_path}")

    return {
        **state,
        "improvement_plan": improvement_plan,
        "logs": logs,
    }


def _render_report(
    state: GlobalState,
    plan: list[dict],
    gap: dict,
    audit: dict,
) -> str:
    lines = [
        f"# GitHub Portfolio Improvement Plan",
        f"",
        f"**GitHub:** [{state['github_username']}](https://github.com/{state['github_username']})",
        f"**Target Role:** {state['target_role']}  |  **Niche:** {state['target_niche']}  |  **Market:** {state['target_market']}",
        f"**Profile Score:** {audit.get('overall_score', 'N/A')}/100  |  **Gap Severity:** {gap.get('gap_severity', 'N/A').upper()}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"{gap.get('summary', '')}",
        f"",
        f"---",
        f"",
        f"## Critical Gaps",
        f"",
    ]

    for skill in gap.get("missing_critical_skills", []):
        lines.append(f"- {skill}")

    lines += [
        f"",
        f"---",
        f"",
        f"## Improvement Plan ({len(plan)} actions)",
        f"",
    ]

    for item in plan:
        effort_icon = {"small": "🟢", "medium": "🟡", "large": "🔴"}.get(item.get("effort", ""), "⚪")
        impact_icon = {"high": "⬆️", "medium": "➡️", "low": "⬇️"}.get(item.get("impact", ""), "")
        lines += [
            f"### {item['priority']}. {item['title']}",
            f"",
            f"**Category:** `{item.get('category', '')}` | **Effort:** {effort_icon} {item.get('effort', '')} | **Impact:** {impact_icon} {item.get('impact', '')}",
            f"",
            f"{item.get('description', '')}",
            f"",
            f"**Actions:**",
        ]
        for action in item.get("specific_actions", []):
            lines.append(f"- {action}")
        lines.append("")

    return "\n".join(lines)
