import json
from skills import llm, file_tools
from config import user_profile
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    evaluations = list(state.get("offer_evaluations") or [])

    unscripted = [e for e in evaluations if not e.get("negotiation_script_path")]
    if not unscripted:
        logs.append("[negotiation_script_gen] All offers already have negotiation scripts.")
        return {**state, "logs": logs}

    logs.append(f"[negotiation_script_gen] Generating scripts for {len(unscripted)} offer(s)...")
    profile = user_profile.load()

    for eval_item in evaluations:
        if eval_item.get("negotiation_script_path"):
            continue

        script = _generate_script(eval_item, profile, state)
        company_slug = "".join(
            c if c.isalnum() else "_" for c in eval_item.get("company", "company")
        )[:25]
        filename = f"{company_slug}_negotiation_script.md"
        path = file_tools.save_text(script, "negotiation", filename)
        eval_item["negotiation_script_path"] = str(path)

        logs.append(f"[negotiation_script_gen] Script saved → {path}")

    return {
        **state,
        "offer_evaluations": evaluations,
        "logs": logs,
    }


def _generate_script(eval_item: dict, profile: dict, state: GlobalState) -> str:
    parsed = eval_item.get("parsed_offer", {})
    benchmark = eval_item.get("market_benchmark", {})
    counter = eval_item.get("counter_recommendation", {})
    risk = eval_item.get("risk_assessment", {})
    personal = profile.get("personal", {})

    company = eval_item.get("company", "")
    company_size = "startup"  # default; can be enriched from JD analysis
    # Try to find company size from scored_jobs
    scored = state.get("scored_jobs") or []
    for job in scored:
        if job.get("company", "").lower() == company.lower():
            company_size = (job.get("company_signals") or {}).get("size", "startup")
            break

    system = (
        "You are a master negotiator and career coach. You write negotiation scripts "
        "that are confident, data-backed, warm, and professional. The goal is a win-win, "
        "not a confrontation. Scripts must feel like they were written by a human, not a template."
    )
    user = f"""Write a complete negotiation script for this job offer.

--- CONTEXT ---
Candidate name: {personal.get("full_name")}
Company: {company} ({company_size})
Role: {eval_item.get("job_title")}
Current offer: {parsed.get("total_ctc_annual")}
Counter ask: {counter.get("counter_ask")}
Walk-away floor: {counter.get("walk_away_floor")}

Key justification points:
{json.dumps(counter.get("justification_points", []), indent=2)}

Non-cash asks:
{json.dumps(counter.get("non_cash_asks", []), indent=2)}

Clause changes to request:
{json.dumps(counter.get("clause_asks", []), indent=2)}

Strategy: {counter.get("negotiation_strategy")}
Market fair value: {benchmark.get("fair_value_range")}
Offer percentile: {benchmark.get("offer_percentile")}

--- INSTRUCTIONS ---
Write a Markdown document containing ALL of these sections:

## 1. Email Script (Counter-offer)
The actual email to send — subject line, full body, professional sign-off.
Tone calibrated to company size ({company_size}).
Reference data without sounding aggressive. Express genuine enthusiasm for the role.

## 2. Phone/Video Call Script
If they call instead of emailing: opening line, how to present the counter verbally,
how to handle silence, what to say if they push back immediately.

## 3. Handling Common Pushbacks
For each scenario, provide exact language:
- "We don't have budget flexibility"
- "This is our standard offer for this level"
- "We have other candidates we're considering"
- "Can you decide by [date]?"

## 4. Clause Negotiation Language
Exact language to request each clause change identified in risk analysis.

## 5. Walk-away Statement
If they reject the counter entirely and the offer is below {counter.get("walk_away_floor")} —
professional but firm language to decline or request more time.

Write as if coaching a friend. Be specific, human, and tactical."""

    return llm.call(system, user, max_tokens=4000)
