"""ATS-optimised resume tailoring — rewrites the base resume to match a specific JD."""
from datetime import datetime, timezone
from skills import llm
from state import GlobalState

_SYSTEM = (
    "You are a senior technical recruiter and ATS optimisation expert. "
    "You rewrite resumes to pass Applicant Tracking Systems while remaining "
    "truthful — you never fabricate experience, only reframe and highlight "
    "what is already there. You know exactly which keywords ATS scanners "
    "look for and how to integrate them naturally."
)

_USER_TEMPLATE = """You must tailor the following resume for the target job description below.

## Target Role
Company: {company}
Job Title: {job_title}

## Job Description
{jd_text}

## Original Resume
{resume_text}

{review_context}

## Your Task
Rewrite the resume to:
1. Mirror the JD's exact language — use the same keywords, acronyms, and phrases
2. Reorder bullet points so the most JD-relevant achievements appear first
3. Add any skills / tools / methodologies from the JD that the candidate genuinely has (inferred from the resume) but didn't explicitly list
4. Remove or deprioritise content irrelevant to this specific role
5. Use ATS-safe formatting: plain text, no tables, no columns, simple bullet points with hyphens
6. Keep all dates, titles, company names, and facts exactly as they appear — do NOT fabricate anything

Return a JSON object with EXACTLY this structure (no markdown fences):
{{
  "tailored_resume": "<full rewritten resume as a plain text string — preserve \\n newlines>",
  "ats_score_estimate": <number 1-10, one decimal — estimated ATS match score for this JD>,
  "keywords_matched": ["<keyword from JD already in original resume>"],
  "keywords_added": ["<keyword from JD not in original but now integrated>"],
  "changes": [
    {{
      "section": "<Resume section — e.g. Skills, Experience, Summary>",
      "change": "<one sentence describing what was changed and why>"
    }}
  ]
}}

Rules:
- tailored_resume: complete resume text, ready to paste — minimum 200 words
- keywords_matched: 5-15 items
- keywords_added: 3-10 items (only genuinely inferrable from resume, no fabrication)
- changes: 4-10 specific, concrete changes made
"""


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])

    resume_text = (state.get("resume_text") or "").strip()
    if not resume_text:
        logs.append("[ats_modifier] No resume text in state — skipping.")
        return {**state, "logs": logs}

    jd_text    = (state.get("_ats_jd_text") or "").strip()
    company    = (state.get("_ats_company") or "Unknown Company").strip()
    job_title  = (state.get("_ats_job_title") or state.get("target_role") or "").strip()

    if not jd_text:
        logs.append("[ats_modifier] No JD text provided — skipping.")
        return {**state, "logs": logs}

    # Optional: cross-reference the resume review gap analysis
    review = state.get("resume_review") or {}
    if review:
        missing = [s.get("skill", "") for s in (review.get("missing_skills") or [])]
        weaknesses = [w.get("point", "") for w in (review.get("weaknesses") or [])]
        review_context = (
            "## Resume Review Context (from prior analysis)\n"
            f"Overall score: {review.get('overall_score', '?')}/10\n"
            f"Missing skills: {', '.join(missing[:8])}\n"
            f"Key weaknesses: {', '.join(weaknesses[:5])}\n"
            "Use this to make especially targeted improvements.\n"
        )
    else:
        review_context = ""

    # Truncate to stay within token budget
    resume_excerpt = resume_text[:5000]
    if len(resume_text) > 5000:
        resume_excerpt += "\n[... resume truncated ...]"

    jd_excerpt = jd_text[:4000]
    if len(jd_text) > 4000:
        jd_excerpt += "\n[... JD truncated ...]"

    logs.append(f"[ats_modifier] Tailoring resume for {company} — {job_title}…")

    user_prompt = _USER_TEMPLATE.format(
        company=company,
        job_title=job_title,
        jd_text=jd_excerpt,
        resume_text=resume_excerpt,
        review_context=review_context,
    )

    result = llm.call_json(_SYSTEM, user_prompt, max_tokens=4096)

    logs.append(
        f"[ats_modifier] Done — ATS estimate {result.get('ats_score_estimate', '?')}/10, "
        f"{len(result.get('keywords_added', []))} keywords added, "
        f"{len(result.get('changes', []))} changes made"
    )

    # Build the record and prepend (newest first)
    record = {
        "company":           company,
        "job_title":         job_title,
        "jd_excerpt":        jd_text[:300],
        "tailored_resume":   result.get("tailored_resume", ""),
        "ats_score_estimate": result.get("ats_score_estimate"),
        "keywords_matched":  result.get("keywords_matched", []),
        "keywords_added":    result.get("keywords_added", []),
        "changes":           result.get("changes", []),
        "generated_at":      datetime.now(timezone.utc).isoformat(),
    }

    existing = list(state.get("ats_modified_resumes") or [])
    updated  = [record] + existing   # newest first

    return {**state, "ats_modified_resumes": updated, "logs": logs}
