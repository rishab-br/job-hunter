import httpx
import re
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Researches the company to prepare for culture-fit questions,
    'why this company' answers, and smart questions to ask the interviewer.
    """
    logs = list(state.get("logs") or [])
    target = state.get("interview_prep_target") or {}

    company = target.get("company", "")
    role = target.get("role", "")
    company_url = target.get("company_url", "")

    logs.append(f"[company_researcher] Researching {company}...")

    # Try to scrape company website for real context
    website_snippet = _fetch_website_snippet(company_url) if company_url else ""

    system = (
        "You are a thorough company researcher helping a candidate prepare for a job interview. "
        "You combine available information with your knowledge to build a useful company profile."
    )
    user = f"""Research this company for interview preparation.

Company: {company}
Role being applied for: {role}
Website snippet (if available): {website_snippet[:2000] if website_snippet else "Not available"}

Return a JSON object with exactly this structure:
{{
  "what_they_build": "clear 2-3 sentence description of their product/service",
  "business_model": "how they make money",
  "company_stage": "seed" or "series_a_b" or "growth" or "pre_ipo" or "public" or "enterprise",
  "estimated_size": "e.g. 50-200 employees",
  "tech_stack_known": ["technologies they are publicly known to use"],
  "engineering_culture_signals": ["signals about how their eng team works"],
  "recent_notable_news": ["funding, product launches, partnerships, or news — if known"],
  "competitors": ["2-3 main competitors"],
  "why_join_talking_points": [
    "genuine, specific reason 1 a candidate would want to join",
    "genuine, specific reason 2",
    "genuine, specific reason 3"
  ],
  "smart_questions_to_ask": [
    {{
      "question": "A specific, thoughtful question to ask the interviewer",
      "why_ask": "what this question signals about you"
    }}
  ],
  "glassdoor_culture_themes": ["common themes from employee reviews if known"],
  "what_they_value_in_hires": ["based on culture and role — what they actually care about"]
}}"""

    research = llm.call_json(system, user, max_tokens=2500)
    logs.append(
        f"[company_researcher] Done. Stage: {research.get('company_stage')} | "
        f"{len(research.get('smart_questions_to_ask', []))} smart questions generated."
    )

    target = {**target, "company_research": research}

    return {
        **state,
        "interview_prep_target": target,
        "logs": logs,
    }


def _fetch_website_snippet(url: str) -> str:
    """Fetches and strips homepage text for company context."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
            )
        }
        resp = httpx.get(url, headers=headers, timeout=8, follow_redirects=True)
        if resp.status_code == 200:
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:3000]
    except Exception:
        pass
    return ""
