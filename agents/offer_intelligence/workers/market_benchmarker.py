import json
import httpx
from skills import llm
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    evaluations = list(state.get("offer_evaluations") or [])

    unparsed = [e for e in evaluations if e.get("market_benchmark") is None]
    if not unparsed:
        logs.append("[market_benchmarker] All offers already benchmarked.")
        return {**state, "logs": logs}

    logs.append(f"[market_benchmarker] Benchmarking {len(unparsed)} offer(s)...")

    for eval_item in evaluations:
        if eval_item.get("market_benchmark") is not None:
            continue

        company = eval_item.get("company", "")
        role = eval_item.get("job_title", "")
        parsed = eval_item.get("parsed_offer", {})

        # Try live scrape first, fall back to Claude knowledge
        ambitionbox_data = _scrape_ambitionbox(company, role)
        benchmark = _build_benchmark(company, role, parsed, ambitionbox_data, state)
        eval_item["market_benchmark"] = benchmark

        logs.append(
            f"[market_benchmarker] {company}: fair value range "
            f"{benchmark.get('fair_value_range')} | "
            f"offer at {benchmark.get('offer_percentile')}"
        )

    return {
        **state,
        "offer_evaluations": evaluations,
        "logs": logs,
    }


def _scrape_ambitionbox(company: str, role: str) -> dict | None:
    """Scrapes AmbitionBox for India salary data. Returns None if unavailable."""
    try:
        company_slug = company.lower().replace(" ", "-").replace(".", "")
        role_slug = role.lower().replace(" ", "-")
        url = f"https://www.ambitionbox.com/salaries/{company_slug}-salaries?designation={role_slug}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)

        if resp.status_code != 200:
            return None

        # Look for salary range in page text (rough extraction)
        text = resp.text
        if "per year" in text.lower() or "lpa" in text.lower():
            return {"source": "ambitionbox", "url": url, "raw_snippet": _extract_salary_snippet(text)}

    except Exception:
        pass
    return None


def _extract_salary_snippet(html: str) -> str:
    """Pull first 500 chars of text near salary mentions."""
    lower = html.lower()
    idx = lower.find("lpa")
    if idx == -1:
        idx = lower.find("per year")
    if idx == -1:
        return ""
    start = max(0, idx - 100)
    end = min(len(html), idx + 400)
    # Strip tags roughly
    import re
    snippet = re.sub(r"<[^>]+>", " ", html[start:end])
    return " ".join(snippet.split())[:500]


def _build_benchmark(
    company: str,
    role: str,
    parsed_offer: dict,
    ambitionbox_data: dict | None,
    state: GlobalState,
) -> dict:
    system = (
        "You are a compensation benchmarking expert with deep knowledge of tech salary data "
        "across India and global markets (levels.fyi, Glassdoor, AmbitionBox, LinkedIn Salary)."
    )

    ab_context = ""
    if ambitionbox_data:
        ab_context = f"\nAmbitionBox snippet: {ambitionbox_data.get('raw_snippet', '')}"

    user = f"""Benchmark this job offer against current market rates.

Company: {company}
Role: {role}
Market: {state["target_market"]}
Niche: {state["target_niche"]}

Offered package:
{json.dumps(parsed_offer, indent=2)}
{ab_context}

Return a JSON object with exactly this structure:
{{
  "market_p25": "25th percentile salary for this role/market — string with currency",
  "market_p50": "median salary — string with currency",
  "market_p75": "75th percentile — string with currency",
  "market_p90": "90th percentile (top talent) — string with currency",
  "fair_value_range": "e.g. ₹20L–₹26L or $95k–$115k",
  "offer_percentile": "e.g. 'around P45' or 'below P25' — honest assessment",
  "offer_vs_market": "below_market or at_market or above_market",
  "data_sources": ["AmbitionBox", "industry knowledge", "levels.fyi estimates"],
  "benchmarking_notes": "any caveats (company stage, location premium, equity value etc.)",
  "negotiation_headroom": "e.g. '15-20% upside is realistic' — honest estimate",
  "competing_offers_context": "what other companies at this stage typically offer"
}}"""

    return llm.call_json(system, user, max_tokens=1500)
