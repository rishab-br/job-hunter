import json
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    active_offers = state.get("active_offers") or []
    existing_evals = list(state.get("offer_evaluations") or [])

    if not active_offers:
        logs.append("[offer_parser] No active offers to parse.")
        return {**state, "logs": logs}

    logs.append(f"[offer_parser] Parsing {len(active_offers)} offer(s)...")

    already_parsed_ids = {e["offer_id"] for e in existing_evals}
    evaluations = list(existing_evals)

    for offer in active_offers:
        offer_id = offer.get("offer_id")
        if offer_id in already_parsed_ids:
            continue

        parsed = _parse_offer(offer)
        evaluations.append({
            "offer_id": offer_id,
            "company": offer.get("company"),
            "job_title": offer.get("job_title"),
            "parsed_offer": parsed,
            "market_benchmark": None,
            "risk_assessment": None,
            "counter_recommendation": None,
            "negotiation_script_path": None,
            "response_coaching": None,
        })
        logs.append(
            f"[offer_parser] Parsed offer from {offer.get('company')} — "
            f"CTC: {parsed.get('total_ctc_annual')}"
        )

    return {
        **state,
        "offer_evaluations": evaluations,
        "logs": logs,
    }


def _parse_offer(offer: dict) -> dict:
    offer_text = offer.get("offer_letter_text") or ""
    company = offer.get("company", "")
    role = offer.get("job_title", "")

    system = (
        "You are an expert in employment contracts and compensation packages. "
        "You extract every financial and legal component from offer letters with precision."
    )
    user = f"""Extract all components from this job offer letter.

Company: {company}
Role: {role}

Offer letter text:
---
{offer_text[:6000]}
---

Return a JSON object with exactly this structure:
{{
  "base_salary_annual": "e.g. ₹18,00,000 or $90,000 — string with currency",
  "variable_pay_annual": "target bonus/variable — string or null",
  "joining_bonus": "one-time joining bonus — string or null",
  "esops_rsus": "equity grant details — string or null",
  "total_ctc_annual": "total cost to company per year — string",
  "notice_period_days": integer or null,
  "probation_period_days": integer or null,
  "work_location": "onsite / hybrid / remote",
  "joining_date": "string or null",
  "offer_validity_date": "deadline to respond — string or null",
  "benefits": ["benefit 1", "benefit 2"],
  "has_non_compete_clause": true or false,
  "has_ip_assignment_clause": true or false,
  "has_moonlighting_restriction": true or false,
  "has_clawback_clause": true or false,
  "other_notable_terms": ["term 1", "term 2"],
  "raw_salary_components": {{
    "notes": "any ambiguous components that need human review"
  }}
}}"""

    return llm.call_json(system, user, max_tokens=2000)
