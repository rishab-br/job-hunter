import json
from config import user_profile
from skills import llm, file_tools
from state import GlobalState

MIN_RELEVANCE_SCORE = 65


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    scored_jobs = state.get("scored_jobs") or []

    target_jobs = [
        j for j in scored_jobs
        if j.get("relevance_score", 0) >= MIN_RELEVANCE_SCORE and j.get("resume_path")
    ]

    if not target_jobs:
        logs.append("[cover_letter_writer] No qualifying jobs — skipping.")
        return {**state, "logs": logs}

    logs.append(f"[cover_letter_writer] Writing cover letters for {len(target_jobs)} job(s)...")
    profile = user_profile.load()

    for job in target_jobs:
        letter = _write_cover_letter(profile, job, state)
        filename = _safe_filename(job.get("company", "company"), job.get("title", "role")) + "_cover_letter.md"
        path = file_tools.save_text(letter, "cover_letters", filename)
        job["cover_letter_path"] = str(path)
        job["cover_letter_content"] = letter
        logs.append(f"[cover_letter_writer] Saved cover letter → {path}")

    return {
        **state,
        "scored_jobs": scored_jobs,
        "logs": logs,
    }


def _write_cover_letter(profile: dict, job: dict, state: GlobalState) -> str:
    personal = profile.get("personal", {})
    company_size = (job.get("company_signals") or {}).get("size", "unknown")
    culture_keywords = (job.get("company_signals") or {}).get("culture_keywords", [])

    system = (
        "You are an expert cover letter writer for software engineering roles. "
        "You write concise, genuine letters that connect the candidate's real work "
        "to the company's actual needs. Never write generic filler."
    )
    user = f"""Write a tailored cover letter for this application.

--- CANDIDATE ---
Name: {personal.get("full_name")}
Experience: {profile.get("total_experience_years")} years
GitHub: {personal.get("github_url")}
Key projects/highlights: {[h for exp in profile.get("experience", []) for h in exp.get("highlights", [])]}

--- TARGET JOB ---
Title: {job.get("title")}
Company: {job.get("company")} ({company_size} company)
Location: {job.get("location")}
Culture signals: {culture_keywords}
Must-have skills required: {job.get("must_have_skills", [])}
Role summary: {job.get("role_summary")}
Application note (what to emphasise): {job.get("application_note")}

--- CANDIDATE'S STRONGEST MATCHES ---
Match reasons: {job.get("match_reasons", [])}

--- INSTRUCTIONS ---
1. Opening: one punchy sentence on why this specific company/role excites the candidate
2. Body paragraph 1: connect 2-3 of the candidate's real achievements to the role's must-haves
3. Body paragraph 2: show awareness of what the company does and how the candidate adds value
4. Closing: clear ask, professional sign-off
5. Tone: calibrate to company size — startup = direct and energetic, enterprise = polished and structured
6. Length: 3-4 short paragraphs max, no fluff
7. Format as Markdown

Return ONLY the cover letter. No meta-commentary."""

    return llm.call(system, user, max_tokens=1500)


def _safe_filename(company: str, role: str) -> str:
    def clean(s: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in s.lower())[:30]
    return f"{clean(company)}_{clean(role)}"
