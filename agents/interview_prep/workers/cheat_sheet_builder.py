import json
from datetime import date
from config import user_profile
from skills import llm, file_tools
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Compiles everything into a single, print-ready interview cheat sheet.
    Also generates a quick 'last 5 minutes before the call' summary card.
    Saves to outputs/interview_prep/<company>_<role>_cheat_sheet.md.
    """
    logs = list(state.get("logs") or [])
    target = state.get("interview_prep_target") or {}
    sessions = list(state.get("interview_prep_sessions") or [])

    company = target.get("company", "company")
    role = target.get("role", "role")

    logs.append(f"[cheat_sheet_builder] Compiling cheat sheet for {role} @ {company}...")

    profile = user_profile.load()
    quick_ref = _generate_quick_reference(target, profile, state)
    full_sheet = _build_full_cheat_sheet(target, profile, quick_ref)

    # Save
    slug = _slug(company, role)
    path = file_tools.save_text(full_sheet, "interview_prep", f"{slug}_cheat_sheet.md")

    # Save quick reference separately
    quick_path = file_tools.save_text(
        _build_quick_card(target, quick_ref),
        "interview_prep",
        f"{slug}_quick_card.md",
    )

    logs.append(f"[cheat_sheet_builder] Cheat sheet saved → {path}")
    logs.append(f"[cheat_sheet_builder] Quick card saved → {quick_path}")

    # Complete the session record
    session = {
        "company": company,
        "role": role,
        "prep_date": date.today().isoformat(),
        "cheat_sheet_path": str(path),
        "quick_card_path": str(quick_path),
        "decoded_jd": target.get("decoded_jd"),
        "company_research": target.get("company_research"),
        "question_count": _count_questions(target.get("questions", {})),
    }
    sessions.append(session)

    return {
        **state,
        "interview_prep_sessions": sessions,
        "interview_prep_target": {**target, "cheat_sheet_path": str(path)},
        "logs": logs,
    }


# ── Report builders ────────────────────────────────────────────────────────────

def _generate_quick_reference(target: dict, profile: dict, state: GlobalState) -> dict:
    decoded = target.get("decoded_jd", {})
    research = target.get("company_research", {})
    answers = target.get("crafted_answers", {})

    system = "You are a career coach distilling interview prep into the most critical points."
    user = f"""Distill this interview prep into the most essential talking points.

Company: {target.get("company")}
Role: {target.get("role")}
Role level: {decoded.get("role_level")}
Core focus: {decoded.get("core_technical_focus", [])}
What they must demonstrate: {decoded.get("must_demonstrate", [])}
Culture fit signals: {decoded.get("culture_fit_signals", [])}
What company values: {research.get("what_they_value_in_hires", [])}

Return a JSON object:
{{
  "three_things_to_nail": ["the 3 most important things to get right in this interview"],
  "your_strongest_talking_points": ["3-4 specific things from your background to mention proactively"],
  "opening_pitch": "60-second 'tell me about yourself' tailored to this role",
  "salary_strategy": "when and how to discuss salary for this specific company stage",
  "mindset_reminder": "1-2 sentences to read 5 minutes before the call to get in the right headspace",
  "things_to_avoid": ["2-3 things NOT to do or say in this specific interview"]
}}"""

    return llm.call_json(system, user, max_tokens=1500)


def _build_full_cheat_sheet(target: dict, profile: dict, quick_ref: dict) -> str:
    company = target.get("company", "")
    role = target.get("role", "")
    decoded = target.get("decoded_jd", {})
    research = target.get("company_research", {})
    questions = target.get("questions", {})
    answers = target.get("crafted_answers", {})
    personal = profile.get("personal", {})

    lines = [
        f"# Interview Prep: {role} @ {company}",
        f"**Prepared:** {date.today().isoformat()}  |  "
        f"**Level:** {decoded.get('role_level', 'N/A').upper()}  |  "
        f"**Stage:** {research.get('company_stage', 'N/A')}",
        f"",
        f"---",
        f"",
        f"## ⚡ 3 Things to Nail",
        f"",
    ]
    for i, thing in enumerate(quick_ref.get("three_things_to_nail", []), 1):
        lines.append(f"{i}. **{thing}**")

    lines += [
        f"",
        f"---",
        f"",
        f"## 🎤 Opening Pitch (60 seconds)",
        f"",
        f"{quick_ref.get('opening_pitch', '')}",
        f"",
        f"---",
        f"",
        f"## 🏢 Company Intel",
        f"",
        f"**What they build:** {research.get('what_they_build', '')}",
        f"**Business model:** {research.get('business_model', '')}",
        f"**Tech stack:** {', '.join(research.get('tech_stack_known', []))}",
        f"",
        f"**Why join (your genuine reasons):**",
    ]
    for pt in research.get("why_join_talking_points", []):
        lines.append(f"- {pt}")

    lines += [
        f"",
        f"**Culture signals:** {', '.join(research.get('engineering_culture_signals', []))}",
        f"",
        f"---",
        f"",
        f"## 🔍 What They're Really Looking For",
        f"",
        f"**Must demonstrate:**",
    ]
    for item in decoded.get("must_demonstrate", []):
        lines.append(f"- {item}")

    lines += [
        f"",
        f"**Interview focus areas:**",
    ]
    for area in decoded.get("interview_focus_areas", []):
        lines.append(f"- {area}")

    lines += [
        f"",
        f"**Hidden requirements:**",
    ]
    for req in decoded.get("hidden_requirements", []):
        lines.append(f"- {req}")

    # Technical Q&A
    lines += [
        f"",
        f"---",
        f"",
        f"## 💻 Technical Questions & Answers",
        f"",
    ]
    for item in answers.get("technical", []):
        lines += [
            f"### Q: {item.get('question', '')}",
            f"",
            f"{item.get('answer', '')}",
            f"",
            f"> **30-sec version:** {item.get('one_liner_summary', '')}",
            f">",
            f"> **Watch out for:** {item.get('watch_out_for', '')}",
            f"",
        ]

    # System Design
    if answers.get("system_design"):
        lines += [
            f"---",
            f"",
            f"## 🏗️ System Design Frameworks",
            f"",
        ]
        for item in answers.get("system_design", []):
            lines += [
                f"### {item.get('question', '')}",
                f"",
                f"**Scale assumptions:** {item.get('scale_assumptions', '')}",
                f"",
                f"**Approach:**",
            ]
            for step in item.get("approach_outline", []):
                lines.append(f"- {step}")
            lines += [
                f"",
                f"**Trade-offs to discuss:**",
            ]
            for tradeoff in item.get("trade_offs_to_discuss", []):
                lines.append(f"- {tradeoff}")
            lines.append(f"")

    # Behavioral
    lines += [
        f"---",
        f"",
        f"## 🧠 Behavioral Questions & STAR Answers",
        f"",
    ]
    for item in answers.get("behavioral", []):
        star = item.get("star_answer", {})
        lines += [
            f"### Q: {item.get('question', '')}",
            f"*Tests: {item.get('competency_being_tested', '')}*",
            f"",
            f"**S:** {star.get('situation', '')}",
            f"**T:** {star.get('task', '')}",
            f"**A:** {star.get('action', '')}",
            f"**R:** {star.get('result', '')}",
            f"",
        ]

    # Company-specific
    lines += [
        f"---",
        f"",
        f"## 🎯 Company-Specific Questions",
        f"",
    ]
    for item in answers.get("company_specific", []):
        lines += [
            f"### Q: {item.get('question', '')}",
            f"",
            f"{item.get('answer', '')}",
            f"",
        ]

    # Questions to ask
    lines += [
        f"---",
        f"",
        f"## ❓ Your Questions to Ask Them",
        f"",
    ]
    for q in questions.get("questions_to_ask_interviewer", []):
        lines += [
            f"- **{q.get('question', '')}**",
            f"  *(Best for: {q.get('best_asked_to', 'anyone')} — {q.get('why_ask_this', '')})*",
        ]

    # Salary
    lines += [
        f"",
        f"---",
        f"",
        f"## 💰 Salary Strategy",
        f"",
        f"{quick_ref.get('salary_strategy', '')}",
        f"",
        f"---",
        f"",
        f"## ⚠️ Things to Avoid",
        f"",
    ]
    for thing in quick_ref.get("things_to_avoid", []):
        lines.append(f"- {thing}")

    lines += [
        f"",
        f"---",
        f"",
        f"## 💬 Strongest Talking Points (mention proactively)",
        f"",
    ]
    for pt in quick_ref.get("your_strongest_talking_points", []):
        lines.append(f"- {pt}")

    return "\n".join(lines)


def _build_quick_card(target: dict, quick_ref: dict) -> str:
    """A single-page 'read this 5 minutes before the call' card."""
    company = target.get("company", "")
    role = target.get("role", "")
    research = target.get("company_research", {})

    lines = [
        f"# ⚡ Quick Card: {role} @ {company}",
        f"*Read this 5 minutes before the call.*",
        f"",
        f"---",
        f"",
        f"**What they build:** {research.get('what_they_build', '')}",
        f"",
        f"**3 things to nail:**",
    ]
    for i, t in enumerate(quick_ref.get("three_things_to_nail", []), 1):
        lines.append(f"{i}. {t}")

    lines += [
        f"",
        f"**Your opening pitch:**",
        f"> {quick_ref.get('opening_pitch', '')}",
        f"",
        f"**Proactively mention:**",
    ]
    for pt in quick_ref.get("your_strongest_talking_points", []):
        lines.append(f"- {pt}")

    lines += [
        f"",
        f"**Do NOT:**",
    ]
    for thing in quick_ref.get("things_to_avoid", []):
        lines.append(f"- {thing}")

    lines += [
        f"",
        f"---",
        f"*{quick_ref.get('mindset_reminder', '')}*",
    ]

    return "\n".join(lines)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _count_questions(questions: dict) -> int:
    return sum(
        len(questions.get(k, []))
        for k in ("technical_questions", "system_design_questions",
                  "behavioral_questions", "company_specific_questions")
    )


def _slug(company: str, role: str) -> str:
    def clean(s: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in s.lower())[:25]
    return f"{clean(company)}_{clean(role)}"
