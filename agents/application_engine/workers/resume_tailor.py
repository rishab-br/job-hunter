import json
from config import user_profile
from skills import llm, file_tools
from state import GlobalState

MIN_RELEVANCE_SCORE = 65


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    scored_jobs = state.get("scored_jobs") or []

    target_jobs = [j for j in scored_jobs if j.get("relevance_score", 0) >= MIN_RELEVANCE_SCORE]

    if not target_jobs:
        logs.append("[resume_tailor] No jobs above score threshold — nothing to tailor.")
        return {**state, "logs": logs}

    logs.append(f"[resume_tailor] Tailoring resume for {len(target_jobs)} job(s)...")
    profile = user_profile.load()

    for job in target_jobs:
        resume_md = _tailor_resume(profile, job, state)
        filename = _safe_filename(job.get("company", "company"), job.get("title", "role")) + "_resume.md"
        path = file_tools.save_text(resume_md, "resumes", filename)
        job["resume_path"] = str(path)
        logs.append(f"[resume_tailor] Saved resume → {path}")

    return {
        **state,
        "scored_jobs": scored_jobs,
        "logs": logs,
    }


def _tailor_resume(profile: dict, job: dict, state: GlobalState) -> str:
    system = (
        "You are an expert technical resume writer. You write clean, ATS-optimised resumes "
        "in Markdown format that mirror the language of the job description and highlight "
        "the candidate's most relevant experience. Never fabricate experience."
    )
    user = f"""Tailor this candidate's resume specifically for the job below.

--- CANDIDATE PROFILE ---
{json.dumps(profile, indent=2)}

--- TARGET JOB ---
Title: {job.get("title")}
Company: {job.get("company")}
Location: {job.get("location")}
Must-have skills: {job.get("must_have_skills", [])}
Nice-to-have skills: {job.get("nice_to_have_skills", [])}
Role summary: {job.get("role_summary")}
Application note: {job.get("application_note")}

--- INSTRUCTIONS ---
1. Reorder and emphasise experience highlights that match must-have skills
2. Mirror the JD's exact terminology where truthful (e.g. if JD says "MLOps", use "MLOps" not "ML pipeline management")
3. Rewrite the summary to speak directly to this role
4. Lead with the most relevant skills for this role in the skills section
5. Keep it to 1 page worth of content (concise bullet points, no fluff)
6. Format as clean Markdown with sections: Summary, Experience, Skills, Education, Certifications

Return ONLY the resume in Markdown. No commentary before or after."""

    return llm.call(system, user, max_tokens=3000)


def _safe_filename(company: str, role: str) -> str:
    def clean(s: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in s.lower())[:30]
    return f"{clean(company)}_{clean(role)}"
