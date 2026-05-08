import json
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    evaluations = list(state.get("offer_evaluations") or [])
    active_offers = state.get("active_offers") or []

    offer_text_by_id = {o.get("offer_id"): o.get("offer_letter_text", "") for o in active_offers}
    unanalyzed = [e for e in evaluations if e.get("risk_assessment") is None]

    if not unanalyzed:
        logs.append("[clause_risk_analyzer] All offers already risk-analyzed.")
        return {**state, "logs": logs}

    logs.append(f"[clause_risk_analyzer] Analyzing clauses in {len(unanalyzed)} offer(s)...")

    for eval_item in evaluations:
        if eval_item.get("risk_assessment") is not None:
            continue

        offer_text = offer_text_by_id.get(eval_item["offer_id"], "")
        parsed = eval_item.get("parsed_offer", {})
        risk = _analyze_clauses(offer_text, parsed, eval_item.get("company", ""))
        eval_item["risk_assessment"] = risk

        high_risks = [c for c in risk.get("clauses", []) if c.get("severity") == "high"]
        logs.append(
            f"[clause_risk_analyzer] {eval_item['company']}: "
            f"overall risk = {risk.get('overall_risk_level')} | "
            f"{len(high_risks)} high-severity clause(s) flagged."
        )

    return {
        **state,
        "offer_evaluations": evaluations,
        "logs": logs,
    }


def _analyze_clauses(offer_text: str, parsed: dict, company: str) -> dict:
    # Supplement text analysis with flags already extracted by the parser
    known_flags = {
        "non_compete": parsed.get("has_non_compete_clause", False),
        "ip_assignment": parsed.get("has_ip_assignment_clause", False),
        "moonlighting_restriction": parsed.get("has_moonlighting_restriction", False),
        "clawback": parsed.get("has_clawback_clause", False),
    }

    system = (
        "You are an employment lawyer and compensation specialist. "
        "You identify and explain risks in job offer terms clearly for a software developer audience."
    )
    user = f"""Analyze this job offer for risky, unusual, or one-sided clauses.

Company: {company}
Known flags from initial parse: {json.dumps(known_flags)}

Offer letter text (may be truncated):
---
{offer_text[:5000] if offer_text else "Full text not available — analyze based on known flags above."}
---

Return a JSON object with exactly this structure:
{{
  "overall_risk_level": "low" or "medium" or "high",
  "clauses": [
    {{
      "clause_type": "non_compete" or "ip_assignment" or "notice_period" or "clawback" or "moonlighting" or "garden_leave" or "probation" or "arbitration" or "other",
      "severity": "low" or "medium" or "high",
      "description": "What this clause says",
      "risk_explanation": "Why it's problematic and what it means for the candidate",
      "is_standard": true or false,
      "negotiation_advice": "Specific language to request changing or removing this"
    }}
  ],
  "notice_period_assessment": {{
    "duration_days": integer or null,
    "is_standard_for_market": true or false,
    "comment": "context on whether this is reasonable"
  }},
  "red_flags_summary": ["flag 1", "flag 2"],
  "positive_terms": ["any genuinely good terms in the offer"],
  "recommended_changes": [
    {{
      "clause": "clause name",
      "ask": "exactly what to request in negotiation"
    }}
  ]
}}"""

    return llm.call_json(system, user, max_tokens=3000)
