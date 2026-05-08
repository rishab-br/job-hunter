import json
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Deeply decodes the target JD to understand what the company is
    actually looking for — beyond the surface-level requirements.
    """
    logs = list(state.get("logs") or [])
    target = state.get("interview_prep_target") or {}

    jd_text = target.get("jd_text", "")
    company = target.get("company", "")
    role = target.get("role", "")

    logs.append(f"[jd_decoder] Decoding JD for {role} @ {company}...")

    system = (
        "You are a senior engineering hiring manager with 10+ years of interviewing experience. "
        "You can read between the lines of job descriptions to understand what companies "
        "actually test for vs. what they list."
    )
    user = f"""Decode this job description deeply.

Company: {company}
Role: {role}

JD Text:
---
{jd_text[:5000]}
---

Return a JSON object with exactly this structure:
{{
  "role_level": "junior" or "mid" or "senior" or "lead" or "staff",
  "core_technical_focus": ["the 3-4 things that matter most technically"],
  "must_demonstrate": ["capabilities the candidate MUST show — not just list on resume"],
  "likely_interview_rounds": [
    {{"round": "round name", "format": "what it looks like", "duration_mins": 45}}
  ],
  "hidden_requirements": ["things not explicitly listed but clearly expected"],
  "what_they_wont_test": ["skills listed but probably not grilled on"],
  "interview_focus_areas": ["top 3 things they will drill deep on"],
  "culture_fit_signals": ["what kind of person they want — read from tone and phrasing"],
  "day_to_day_reality": "honest 2-3 sentence description of what you'd actually do",
  "green_flags_in_jd": ["positive signals about the role/company"],
  "yellow_flags_in_jd": ["things to clarify or watch out for"],
  "seniority_signals": ["specific phrases that reveal expected seniority level"]
}}"""

    decoded = llm.call_json(system, user, max_tokens=2500)
    logs.append(
        f"[jd_decoder] Done. Role level: {decoded.get('role_level')} | "
        f"Focus areas: {decoded.get('interview_focus_areas', [])}"
    )

    # Attach decoded JD to the prep target
    target = {**target, "decoded_jd": decoded}

    return {
        **state,
        "interview_prep_target": target,
        "logs": logs,
    }
