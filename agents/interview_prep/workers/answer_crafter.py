import json
from config import user_profile
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Crafts personalised answers to every generated question using the
    candidate's actual projects, experience, and profile data.
    Behavioral answers follow the STAR format.
    Technical answers reference real code and decisions.
    """
    logs = list(state.get("logs") or [])
    target = state.get("interview_prep_target") or {}

    company = target.get("company", "")
    role = target.get("role", "")
    questions = target.get("questions", {})
    decoded = target.get("decoded_jd", {})

    logs.append(f"[answer_crafter] Crafting answers for {role} @ {company}...")

    profile = user_profile.load()
    candidate_context = _build_candidate_context(state, profile)

    # Craft answers for each category
    tech_answers = _craft_technical_answers(
        questions.get("technical_questions", []), candidate_context, role, company
    )
    behavioral_answers = _craft_behavioral_answers(
        questions.get("behavioral_questions", []), candidate_context, role
    )
    design_answers = _craft_design_answers(
        questions.get("system_design_questions", []), candidate_context, role
    )
    company_answers = _craft_company_answers(
        questions.get("company_specific_questions", []),
        candidate_context,
        target.get("company_research", {}),
        role,
        company,
    )

    crafted_answers = {
        "technical": tech_answers,
        "behavioral": behavioral_answers,
        "system_design": design_answers,
        "company_specific": company_answers,
    }

    total = sum(len(v) for v in crafted_answers.values())
    logs.append(f"[answer_crafter] Done. {total} answers crafted.")

    target = {**target, "crafted_answers": crafted_answers}

    return {
        **state,
        "interview_prep_target": target,
        "logs": logs,
    }


# ── Answer crafting per category ───────────────────────────────────────────────

def _craft_technical_answers(questions: list, context: dict, role: str, company: str) -> list:
    if not questions:
        return []

    system = (
        "You are coaching a software developer to answer technical interview questions. "
        "Answers must reference their ACTUAL projects and experience — never fabricate. "
        "Be specific, concise, and confident."
    )
    user = f"""Craft technical interview answers for this candidate.

Role: {role} at {company}

Candidate context:
{json.dumps(context, indent=2)}

Questions to answer:
{json.dumps(questions, indent=2)}

Return a JSON array. Each element:
{{
  "question": "exact question text",
  "answer": "complete, natural-sounding answer the candidate can rehearse — 2-4 minutes when spoken",
  "key_points_hit": ["the concepts this answer covers"],
  "projects_referenced": ["which of their actual projects this draws from"],
  "one_liner_summary": "30-second version if they need to be concise",
  "watch_out_for": "common mistake or follow-up to be ready for"
}}"""

    return llm.call_json(system, user, max_tokens=5000)


def _craft_behavioral_answers(questions: list, context: dict, role: str) -> list:
    if not questions:
        return []

    system = (
        "You are a career coach helping a developer craft STAR-format behavioral answers. "
        "Every answer must draw from their real experience. "
        "STAR = Situation, Task, Action, Result (with quantified impact where possible)."
    )
    user = f"""Craft STAR-format behavioral answers for this candidate.

Role: {role}

Candidate context:
{json.dumps(context, indent=2)}

Behavioral questions:
{json.dumps(questions, indent=2)}

Return a JSON array. Each element:
{{
  "question": "exact question text",
  "competency_being_tested": "e.g. ownership, leadership, conflict",
  "star_answer": {{
    "situation": "specific context — when, where, what project",
    "task": "what YOU were responsible for",
    "action": "specific steps YOU took (use 'I', not 'we')",
    "result": "quantified outcome — numbers, percentages, timelines"
  }},
  "full_answer": "natural flowing version of the STAR answer to rehearse",
  "alternative_story": "a backup story from a different project if this one doesn't land"
}}"""

    return llm.call_json(system, user, max_tokens=4000)


def _craft_design_answers(questions: list, context: dict, role: str) -> list:
    if not questions:
        return []

    system = (
        "You are a senior engineer coaching a candidate through system design interviews. "
        "Answers should show structured thinking: clarify → estimate → high-level → deep dive → trade-offs."
    )
    user = f"""Create system design answer frameworks for this candidate.

Role: {role}
Candidate context (for calibrating depth):
{json.dumps(context, indent=2)}

System design questions:
{json.dumps(questions, indent=2)}

Return a JSON array. Each element:
{{
  "question": "exact question text",
  "clarifying_questions_to_ask": ["question to ask before diving in"],
  "approach_outline": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "key_components": ["component and its role"],
  "scale_assumptions": "numbers to state upfront (users, QPS, data size)",
  "trade_offs_to_discuss": ["trade-off 1 and your recommendation"],
  "technologies_to_mention": ["specific tech choices relevant to candidate's stack"],
  "time_split_guide": "how to allocate the 45 minutes across sections"
}}"""

    return llm.call_json(system, user, max_tokens=3000)


def _craft_company_answers(
    questions: list, context: dict, research: dict, role: str, company: str
) -> list:
    if not questions:
        return []

    system = (
        "You are coaching a candidate to answer company-specific interview questions. "
        "Answers must be genuine, specific to this company, and show real research — not generic."
    )
    user = f"""Craft answers to company-specific questions.

Company: {company}
Role: {role}

Company research:
{json.dumps(research, indent=2)}

Candidate context:
{json.dumps(context, indent=2)}

Questions:
{json.dumps(questions, indent=2)}

Return a JSON array. Each element:
{{
  "question": "exact question text",
  "answer": "specific, genuine answer that references real company details",
  "key_message": "the one thing this answer must convey"
}}"""

    return llm.call_json(system, user, max_tokens=2000)


# ── Context builder ────────────────────────────────────────────────────────────

def _build_candidate_context(state: GlobalState, profile: dict) -> dict:
    """Builds a rich candidate summary from state + profile.json."""
    repos = state.get("repo_depth_reports") or []
    showcase = [
        {
            "name": r["name"],
            "language": r.get("language"),
            "topics": r.get("topics", []),
            "strengths": r.get("strengths", []),
        }
        for r in repos if r.get("showcase_worthy")
    ]

    experience = profile.get("experience", [])
    highlights = [h for exp in experience for h in exp.get("highlights", [])]

    return {
        "name": profile.get("personal", {}).get("full_name", ""),
        "total_experience_years": profile.get("total_experience_years", 0),
        "top_languages": profile.get("skills", {}).get("languages", []),
        "frameworks": profile.get("skills", {}).get("frameworks", []),
        "tools": profile.get("skills", {}).get("tools", []),
        "ai_ml_skills": profile.get("skills", {}).get("ai_ml", []),
        "cloud": profile.get("skills", {}).get("cloud", []),
        "certifications": profile.get("certifications", []),
        "experience_highlights": highlights,
        "showcase_projects": showcase,
        "github_username": state.get("github_username", ""),
        "education": profile.get("education", []),
    }
