import json
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Generates a comprehensive, role-specific question bank covering:
    technical, system design, behavioral, company-specific, and
    questions the candidate should ask the interviewer.
    """
    logs = list(state.get("logs") or [])
    target = state.get("interview_prep_target") or {}

    company = target.get("company", "")
    role = target.get("role", "")
    decoded = target.get("decoded_jd", {})
    research = target.get("company_research", {})

    logs.append(f"[question_generator] Generating question bank for {role} @ {company}...")

    system = (
        "You are a senior engineering interviewer who has conducted 500+ technical interviews. "
        "You generate realistic, role-specific questions that mirror actual interview processes "
        "at companies of this type and stage."
    )
    user = f"""Generate a comprehensive interview question bank for this role.

Company: {company} ({research.get("company_stage", "unknown stage")})
Role: {role}
Role Level: {decoded.get("role_level", "mid")}
Core Technical Focus: {decoded.get("core_technical_focus", [])}
Interview Focus Areas: {decoded.get("interview_focus_areas", [])}
Likely Interview Rounds: {json.dumps(decoded.get("likely_interview_rounds", []))}
Tech Stack Known: {research.get("tech_stack_known", [])}
What They Value: {research.get("what_they_value_in_hires", [])}

Return a JSON object with exactly this structure:
{{
  "technical_questions": [
    {{
      "question": "specific technical question",
      "difficulty": "easy" or "medium" or "hard",
      "category": "specific sub-topic e.g. 'Python async', 'LLM fine-tuning'",
      "why_theyll_ask": "what this question reveals about the candidate",
      "key_concepts_to_cover": ["concept 1", "concept 2"],
      "follow_up_questions": ["likely follow-up 1", "likely follow-up 2"]
    }}
  ],
  "system_design_questions": [
    {{
      "question": "design question",
      "scope": "what they expect you to cover",
      "time_allocated_mins": 45,
      "evaluation_criteria": ["what they're looking for in your design"]
    }}
  ],
  "behavioral_questions": [
    {{
      "question": "Tell me about a time...",
      "competency": "what trait this tests e.g. 'ownership', 'conflict resolution'",
      "what_good_looks_like": "what a strong STAR answer demonstrates",
      "red_flags": ["answers that would concern the interviewer"]
    }}
  ],
  "company_specific_questions": [
    {{
      "question": "why this company / role specific question",
      "what_theyre_testing": "genuine interest vs. generic candidate"
    }}
  ],
  "questions_to_ask_interviewer": [
    {{
      "question": "thoughtful question to ask them",
      "best_asked_to": "recruiter" or "hiring_manager" or "tech_interviewer" or "anyone",
      "why_ask_this": "what asking this signals about you"
    }}
  ]
}}

Generate: 8-10 technical, 2-3 system design, 6-8 behavioral, 3-4 company-specific, 6-8 questions to ask."""

    questions = llm.call_json(system, user, max_tokens=5000)

    total = (
        len(questions.get("technical_questions", [])) +
        len(questions.get("system_design_questions", [])) +
        len(questions.get("behavioral_questions", [])) +
        len(questions.get("company_specific_questions", []))
    )
    logs.append(f"[question_generator] Done. {total} questions generated across all categories.")

    target = {**target, "questions": questions}

    return {
        **state,
        "interview_prep_target": target,
        "logs": logs,
    }
