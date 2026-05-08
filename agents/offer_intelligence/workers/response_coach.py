import json
from datetime import datetime, timezone
from skills import llm, file_tools
from config import user_profile
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Activated when an employer responds to the candidate's counter-offer.
    Looks for offers where offer["employer_response"] is set and
    response_coaching has not yet been generated for that response.
    """
    logs = list(state.get("logs") or [])
    evaluations = list(state.get("offer_evaluations") or [])
    active_offers = state.get("active_offers") or []
    existing_coaching = list(state.get("response_coaching") or [])

    offers_with_response = [
        o for o in active_offers
        if o.get("employer_response")
    ]
    coached_ids = {c["offer_id"] for c in existing_coaching}
    to_coach = [o for o in offers_with_response if o.get("offer_id") not in coached_ids]

    if not to_coach:
        logs.append("[response_coach] No new employer responses to coach on.")
        return {**state, "logs": logs}

    logs.append(f"[response_coach] Coaching on {len(to_coach)} employer response(s)...")
    profile = user_profile.load()

    eval_by_id = {e["offer_id"]: e for e in evaluations}

    for offer in to_coach:
        offer_id = offer.get("offer_id")
        eval_item = eval_by_id.get(offer_id, {})
        coaching = _coach_response(offer, eval_item, profile, state)

        # Save coaching report
        company_slug = "".join(
            c if c.isalnum() else "_" for c in offer.get("company", "company")
        )[:25]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        filename = f"{company_slug}_response_coaching_{ts}.md"
        path = file_tools.save_text(coaching["report"], "negotiation", filename)
        coaching["report_path"] = str(path)
        coaching["offer_id"] = offer_id
        existing_coaching.append(coaching)

        logs.append(
            f"[response_coach] {offer.get('company')}: "
            f"recommended move = {coaching.get('recommended_move')} | "
            f"report → {path}"
        )

    return {
        **state,
        "response_coaching": existing_coaching,
        "logs": logs,
    }


def _coach_response(offer: dict, eval_item: dict, profile: dict, state: GlobalState) -> dict:
    employer_response = offer.get("employer_response", "")
    counter = eval_item.get("counter_recommendation", {})
    parsed = eval_item.get("parsed_offer", {})
    personal = profile.get("personal", {})

    system = (
        "You are a master negotiator coaching a software developer through a live salary negotiation. "
        "Your advice is tactical, honest, and grounded in what actually works."
    )
    user = f"""The employer has responded to our counter-offer. Coach the candidate on what to do next.

--- NEGOTIATION HISTORY ---
Company: {offer.get("company")}
Role: {offer.get("job_title")}
Original offer: {parsed.get("total_ctc_annual")}
Our counter ask: {counter.get("counter_ask")}
Our walk-away floor: {counter.get("walk_away_floor")}

--- EMPLOYER'S RESPONSE ---
{employer_response}

--- CANDIDATE CONTEXT ---
Name: {personal.get("full_name")}
Expected: {profile.get("expected_salary")}
Market fair value: {eval_item.get("market_benchmark", {}).get("fair_value_range")}

Analyze the employer's response and return a JSON object:
{{
  "response_summary": "what concessions (if any) the employer made",
  "recommended_move": "accept" or "counter_again" or "decline" or "request_time",
  "reasoning": "why this is the right move",
  "if_accept": "what to say when accepting",
  "if_counter_again": {{
    "new_ask": "revised number if countering again",
    "email_script": "exact email to send"
  }},
  "if_decline": "professional decline language",
  "if_request_time": "how to ask for more time without losing the offer",
  "red_flags_in_response": ["any concerning signals in how they responded"],
  "overall_assessment": "honest 2-3 sentence take on this offer and company based on the full negotiation"
}}"""

    analysis = llm.call_json(system, user, max_tokens=2000)

    # Build a human-readable coaching report
    report = _render_coaching_report(offer, eval_item, employer_response, analysis)

    return {**analysis, "report": report}


def _render_coaching_report(
    offer: dict,
    eval_item: dict,
    employer_response: str,
    analysis: dict,
) -> str:
    move_icon = {
        "accept": "✅",
        "counter_again": "🔄",
        "decline": "❌",
        "request_time": "⏳",
    }.get(analysis.get("recommended_move", ""), "")

    lines = [
        f"# Negotiation Response Coaching",
        f"**Company:** {offer.get('company')}  |  **Role:** {offer.get('job_title')}",
        f"",
        f"## Employer's Response",
        f"",
        f"> {employer_response.strip()}",
        f"",
        f"---",
        f"",
        f"## Analysis",
        f"",
        f"**What they conceded:** {analysis.get('response_summary')}",
        f"",
        f"**Recommended move:** {move_icon} **{analysis.get('recommended_move', '').upper().replace('_', ' ')}**",
        f"",
        f"**Why:** {analysis.get('reasoning')}",
        f"",
        f"---",
        f"",
        f"## Your Next Step",
        f"",
    ]

    move = analysis.get("recommended_move")
    if move == "accept" and analysis.get("if_accept"):
        lines += [f"```", analysis["if_accept"], f"```", f""]
    elif move == "counter_again" and analysis.get("if_counter_again"):
        c = analysis["if_counter_again"]
        lines += [
            f"**New ask:** {c.get('new_ask')}",
            f"",
            f"**Email to send:**",
            f"```",
            f"{c.get('email_script', '')}",
            f"```",
            f"",
        ]
    elif move == "decline" and analysis.get("if_decline"):
        lines += [f"```", analysis["if_decline"], f"```", f""]
    elif move == "request_time" and analysis.get("if_request_time"):
        lines += [f"```", analysis["if_request_time"], f"```", f""]

    if analysis.get("red_flags_in_response"):
        lines += [
            f"---",
            f"",
            f"## ⚠️ Red Flags in Their Response",
            f"",
        ]
        for flag in analysis["red_flags_in_response"]:
            lines.append(f"- {flag}")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## Overall Assessment",
        f"",
        f"{analysis.get('overall_assessment', '')}",
    ]

    return "\n".join(lines)
