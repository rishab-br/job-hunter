"""LLM-powered resume analysis against target role and market trends."""
import json
from skills import llm
from state import GlobalState

_SYSTEM = (
    "You are an expert technical recruiter and career coach specialising in "
    "tech and AI roles. You evaluate resumes with deep knowledge of what hiring "
    "managers look for, ATS systems, and current market demand."
)

_USER_TEMPLATE = """Review the following resume for a candidate targeting: **{role}** in the **{niche}** space ({market} market).

{github_context}

---
RESUME TEXT:
{resume_text}
---

Evaluate this resume thoroughly and return a JSON object with EXACTLY this structure (no extra keys, no markdown fences):
{{
  "overall_score": <number 1-10, one decimal place>,
  "score_rationale": "<2-3 sentences explaining the score>",
  "role_fit": "<one of: strong | moderate | weak>",
  "format_quality": "<one of: excellent | good | average | poor>",
  "strengths": [
    {{"point": "<short title>", "detail": "<one sentence explanation>"}}
  ],
  "weaknesses": [
    {{"point": "<short title>", "detail": "<one sentence explanation>"}}
  ],
  "missing_skills": [
    {{
      "skill": "<skill or keyword>",
      "importance": "<one of: critical | important | nice-to-have>",
      "why": "<why this matters for the target role right now>"
    }}
  ],
  "ats_score": <number 1-10>,
  "ats_concerns": ["<concern 1>", "<concern 2>"],
  "market_alignment": "<one paragraph on how well this resume is positioned for current market demand>",
  "recommendations": [
    {{"action": "<specific thing to do>", "impact": "<one of: high | medium | low>"}}
  ]
}}

Rules:
- strengths: 3-6 items
- weaknesses: 3-6 items
- missing_skills: 4-8 items based on what's genuinely absent for the role
- recommendations: 3-5 actionable items, most impactful first
- Be honest and constructive — the candidate needs real feedback, not flattery
"""


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    resume_text = (state.get("resume_text") or "").strip()

    if not resume_text:
        logs.append("[resume_reviewer] No resume text found in state — skipping.")
        return {**state, "logs": logs}

    role   = state.get("target_role", "Software Engineer")
    niche  = state.get("target_niche", "Tech")
    market = state.get("target_market", "Global")

    # Optionally weave in GitHub audit for richer cross-referencing
    github_audit = state.get("github_audit") or {}
    if github_audit:
        github_context = (
            f"The candidate's GitHub profile has been analysed:\n"
            f"- Overall score: {github_audit.get('overall_score', '?')}/100\n"
            f"- Key strengths: {', '.join(github_audit.get('key_strengths', []))}\n"
            f"- Top languages: {', '.join(github_audit.get('top_languages', []))}\n"
            f"Cross-reference the resume against these GitHub signals where relevant.\n"
        )
    else:
        github_context = ""

    # Truncate resume to ~6 000 chars to stay within token budget
    resume_excerpt = resume_text[:6000]
    if len(resume_text) > 6000:
        resume_excerpt += "\n[... resume truncated for analysis ...]"

    user_prompt = _USER_TEMPLATE.format(
        role=role,
        niche=niche,
        market=market,
        github_context=github_context,
        resume_text=resume_excerpt,
    )

    logs.append(f"[resume_reviewer] Analysing resume for '{role}' ({len(resume_text)} chars)…")
    review = llm.call_json(_SYSTEM, user_prompt, max_tokens=2048)
    logs.append(
        f"[resume_reviewer] Done — score {review.get('overall_score', '?')}/10, "
        f"fit: {review.get('role_fit', '?')}, "
        f"ATS: {review.get('ats_score', '?')}/10"
    )

    return {**state, "resume_review": review, "logs": logs}
