import json
from skills import llm
from state import GlobalState

BATCH_SIZE = 8  # jobs per Claude call to stay within context limits


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    jobs = state.get("discovered_jobs") or []

    if not jobs:
        logs.append("[jd_analyzer] No jobs to analyze.")
        return {**state, "analyzed_jds": [], "logs": logs}

    logs.append(f"[jd_analyzer] Analyzing {len(jobs)} job descriptions in batches of {BATCH_SIZE}...")

    analyzed: list[dict] = []
    batches = [jobs[i : i + BATCH_SIZE] for i in range(0, len(jobs), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        logs.append(f"[jd_analyzer] Processing batch {i + 1}/{len(batches)}...")
        results = _analyze_batch(batch, state["target_role"], state["target_niche"])
        analyzed.extend(results)

    logs.append(f"[jd_analyzer] Done. {len(analyzed)} JDs analyzed.")
    return {
        **state,
        "analyzed_jds": analyzed,
        "logs": logs,
    }


def _analyze_batch(jobs: list[dict], target_role: str, target_niche: str) -> list[dict]:
    # Strip descriptions to save tokens — keep first 1500 chars per job
    slim = [
        {
            "id": j["id"],
            "platform": j["platform"],
            "title": j["title"],
            "company": j["company"],
            "location": j["location"],
            "description": (j.get("description") or "")[:1500],
            "salary_range": j.get("salary_range"),
        }
        for j in jobs
    ]

    system = (
        "You are a senior technical recruiter with deep expertise in software engineering roles. "
        "You extract structured intelligence from job descriptions accurately and concisely."
    )
    user = f"""Analyze each job description and return structured intelligence.

Target Role Context: {target_role} / {target_niche}

Jobs to analyze:
{json.dumps(slim, indent=2)}

Return a JSON array. Each element must correspond to one job and have exactly this structure:
{{
  "job_id": "same id as input",
  "must_have_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill1", "skill2"],
  "seniority_level": "junior" or "mid" or "senior" or "lead" or "unknown",
  "remote_friendly": true or false,
  "estimated_salary_range": "string like '18-25 LPA' or '80k-100k USD'" or null,
  "red_flags": ["flag1", "flag2"],
  "company_signals": {{
    "size": "startup" or "mid-size" or "enterprise" or "unknown",
    "culture_keywords": ["keyword1", "keyword2"]
  }},
  "role_summary": "1-2 sentence summary of what this role actually involves"
}}

Return one object per input job. Match array order to input order."""

    return llm.call_json(system, user, max_tokens=4096)
