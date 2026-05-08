import json
from config import user_profile
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    evaluations = list(state.get("offer_evaluations") or [])

    unprocessed = [e for e in evaluations if e.get("counter_recommendation") is None]
    if not unprocessed:
        logs.append("[counteroffer_calculator] All offers already have counter-offer recommendations.")
        return {**state, "logs": logs}

    logs.append(f"[counteroffer_calculator] Computing counter-offers for {len(unprocessed)} offer(s)...")
    profile = user_profile.load()

    for eval_item in evaluations:
        if eval_item.get("counter_recommendation") is not None:
            continue

        counter = _calculate_counter(eval_item, profile, state)
        eval_item["counter_recommendation"] = counter

        logs.append(
            f"[counteroffer_calculator] {eval_item['company']}: "
            f"ask = {counter.get('counter_ask')} | "
            f"walk-away floor = {counter.get('walk_away_floor')}"
        )

    return {
        **state,
        "offer_evaluations": evaluations,
        "logs": logs,
    }


def _calculate_counter(eval_item: dict, profile: dict, state: GlobalState) -> dict:
    parsed = eval_item.get("parsed_offer", {})
    benchmark = eval_item.get("market_benchmark", {})
    risk = eval_item.get("risk_assessment", {})

    system = (
        "You are a senior career advisor and negotiation expert specialising in tech compensation. "
        "You provide precise, data-backed counter-offer recommendations with clear reasoning."
    )
    user = f"""Compute a counter-offer recommendation for this job offer.

--- OFFER DETAILS ---
Company: {eval_item.get("company")}
Role: {eval_item.get("job_title")}
Offered CTC: {parsed.get("total_ctc_annual")}
Notice period: {parsed.get("notice_period_days")} days

--- MARKET BENCHMARK ---
{json.dumps(benchmark, indent=2)}

--- RISK ASSESSMENT ---
Overall risk: {risk.get("overall_risk_level")}
High-severity clauses: {[c for c in risk.get("clauses", []) if c.get("severity") == "high"]}
Recommended clause changes: {risk.get("recommended_changes", [])}

--- CANDIDATE CONTEXT ---
Total experience: {profile.get("total_experience_years")} years
Expected salary: {profile.get("expected_salary")}
Notice period available: {profile.get("notice_period_days")} days
Target market: {state["target_market"]}

Return a JSON object with exactly this structure:
{{
  "counter_ask": "specific number to ask for — e.g. ₹24,00,000 CTC",
  "walk_away_floor": "minimum acceptable — e.g. ₹21,00,000 CTC",
  "ideal_outcome": "best realistic outcome including non-cash items",
  "justification_points": [
    "data point 1 that supports the ask",
    "data point 2",
    "data point 3"
  ],
  "non_cash_asks": [
    "additional paid leaves",
    "remote flexibility",
    "earlier performance review",
    "signing bonus in lieu of salary increase"
  ],
  "clause_asks": ["specific clause changes to negotiate — from risk assessment"],
  "batna_assessment": "honest assessment of candidate's leverage and alternatives",
  "negotiation_strategy": "collaborative or competitive or anchoring — with brief why",
  "expected_counter_range": "what the company is likely to come back with",
  "probability_of_success": "e.g. '70% chance of 10-15% increase' — honest estimate"
}}"""

    return llm.call_json(system, user, max_tokens=2000)
