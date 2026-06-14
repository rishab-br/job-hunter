"""Role expander — first node in the discovery graph.

Asks the LLM to generate synonym / equivalent job titles for the target
role so scrapers cast a wider net. A fresher searching "AI Engineer" also
surfaces "AI Developer", "GenAI Engineer", "LLM Engineer", etc.

The original title is always index-0 so scrapers can treat it as the
primary term when only one slot is available (e.g. Playwright searches).
"""
from skills import llm
from state import GlobalState

MAX_VARIANTS = 7   # enough to cover synonyms without flooding scrapers


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    role  = state.get("target_role", "").strip()
    niche = state.get("target_niche", "").strip()
    filters = state.get("discovery_filters") or {}
    max_sen = filters.get("max_seniority", "")

    if not role:
        return {**state, "search_roles": [], "logs": logs}

    # If expansion already happened (re-run / resume), skip.
    if state.get("search_roles"):
        logs.append(f"[role_expander] Already expanded: {state['search_roles']}")
        return {**state, "logs": logs}

    seniority_hint = f" The candidate is at '{max_sen}' level." if max_sen else ""
    niche_hint = f" Domain/niche: {niche}." if niche else ""

    system = (
        "You are a technical recruiter who knows every job title variation used in the "
        "software/AI industry across India and globally."
    )
    user = f"""A candidate is searching for jobs with the title: "{role}".{niche_hint}{seniority_hint}

Generate up to {MAX_VARIANTS} job titles that:
1. Require almost the same core skills as "{role}"
2. Would appear on real job boards (LinkedIn, Naukri, Greenhouse, Lever)
3. Are appropriate for the seniority level mentioned (if any)
4. Cover common variations companies actually post (e.g. "AI Engineer" → "AI Developer", "GenAI Engineer", "LLM Engineer", "Applied AI Engineer", "Machine Learning Engineer")

Return a JSON array of strings. Put "{role}" first. No duplicates. No explanations.
Example: ["{role}", "Variant 1", "Variant 2", ...]"""

    try:
        variants = llm.call_json(system, user, max_tokens=256)
        if not isinstance(variants, list):
            raise ValueError(f"Unexpected response shape: {type(variants)}")
        # Ensure original role is always present and first
        clean = [role] + [v for v in variants if isinstance(v, str) and v.lower() != role.lower()]
        search_roles = clean[:MAX_VARIANTS]
    except Exception as exc:
        logs.append(f"[role_expander] LLM expansion failed ({exc}) — using original title only.")
        search_roles = [role]

    logs.append(f"[role_expander] Search titles: {search_roles}")
    return {**state, "search_roles": search_roles, "logs": logs}
