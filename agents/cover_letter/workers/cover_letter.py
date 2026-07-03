"""Generates a tailored, JD-matched cover letter from the candidate's resume and profile."""
from datetime import datetime, timezone
from skills import llm
from state import GlobalState

_SYSTEM = (
    "You are an expert career coach and professional writer. You write compelling, "
    "authentic cover letters that get candidates to interviews. Your letters are "
    "specific, never generic — they reference the company and role directly, connect "
    "the candidate's real experience to the JD's requirements, and open with a hook "
    "that isn't 'I am writing to apply for'. You never fabricate experience."
)

_TONES = {
    "professional": "formal, polished, and confident — suitable for large enterprises and traditional industries",
    "conversational": "warm, human, and approachable — suitable for mid-size companies and modern teams",
    "enthusiastic": "energetic, passionate, and forward-looking — suitable for startups and fast-moving environments",
}

_USER_TEMPLATE = """Write a cover letter for the candidate below. This is a real application — quality matters.

## Target Position
Company: {company}
Job Title: {job_title}
Tone to use: {tone} ({tone_description})

## Job Description
{jd_section}

## Candidate Resume
{resume_section}

{context_section}

## Instructions
- Open with a strong, specific hook — never start with "I am writing to apply"
- Paragraph 1 (Hook + fit): Why this company and this role specifically. Show you know them.
- Paragraph 2 (Experience match): 2-3 concrete achievements from the resume that map to the JD's core requirements. Be specific — mention tools, numbers, outcomes.
- Paragraph 3 (Closing): Confident call to action. No begging, no "I hope to hear from you".
- 3 paragraphs only, 280-380 words total
- Maintain the specified tone throughout
- Address to "Hiring Manager" unless a specific name is available

Return a JSON object with EXACTLY this structure (no markdown fences):
{{
  "cover_letter": "<full cover letter text — preserve \\n newlines between paragraphs>",
  "key_points": ["<specific selling point used in the letter>"],
  "word_count": <integer>,
  "tone_used": "{tone}"
}}

Rules:
- key_points: 3-5 items — what you led with as the strongest arguments
- word_count: actual word count of cover_letter field
"""


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])

    resume_text = (state.get("resume_text") or "").strip()
    if not resume_text:
        logs.append("[cover_letter] No resume text in state — skipping.")
        return {**state, "logs": logs}

    company   = (state.get("_cl_company") or "the company").strip()
    job_title = (state.get("_cl_job_title") or state.get("target_role") or "").strip()
    jd_text   = (state.get("_cl_jd_text") or "").strip()
    tone      = (state.get("_cl_tone") or "professional").strip().lower()
    if tone not in _TONES:
        tone = "professional"

    # JD section — optional but strongly recommended
    if jd_text:
        jd_section = jd_text[:3500]
        if len(jd_text) > 3500:
            jd_section += "\n[... JD truncated ...]"
    else:
        jd_section = f"No JD provided — write for a generic {job_title} role at {company}."

    # Resume section
    resume_section = resume_text[:4000]
    if len(resume_text) > 4000:
        resume_section += "\n[... resume truncated ...]"

    # Optional context: GitHub audit + review gaps
    ctx_parts = []
    audit = state.get("github_audit") or {}
    if audit:
        ctx_parts.append(
            f"GitHub profile score: {audit.get('overall_score', '?')}/100. "
            f"Key strengths: {', '.join((audit.get('key_strengths') or [])[:4])}."
        )
    review = state.get("resume_review") or {}
    if review:
        ctx_parts.append(
            f"Resume review score: {review.get('overall_score', '?')}/10. "
            f"Role fit: {review.get('role_fit', '?')}."
        )
    context_section = ("## Additional Context\n" + "\n".join(ctx_parts)) if ctx_parts else ""

    logs.append(f"[cover_letter] Generating {tone} cover letter for {company} — {job_title}…")

    user_prompt = _USER_TEMPLATE.format(
        company=company,
        job_title=job_title,
        tone=tone,
        tone_description=_TONES[tone],
        jd_section=jd_section,
        resume_section=resume_section,
        context_section=context_section,
    )

    result = llm.call_json(_SYSTEM, user_prompt, max_tokens=2048)

    logs.append(
        f"[cover_letter] Done — {result.get('word_count', '?')} words, "
        f"tone: {result.get('tone_used', tone)}, "
        f"{len(result.get('key_points', []))} key points"
    )

    record = {
        "company":      company,
        "job_title":    job_title,
        "cover_letter": result.get("cover_letter", ""),
        "key_points":   result.get("key_points", []),
        "word_count":   result.get("word_count"),
        "tone":         result.get("tone_used", tone),
        "has_jd":       bool(jd_text),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = list(state.get("cover_letters") or [])
    return {**state, "cover_letters": [record] + existing, "logs": logs}
