"""
Greenhouse + Lever job discovery — structured public JSON APIs, zero scraping risk.

Unlike LinkedIn/Indeed/Naukri, these ATS platforms *publish* their job boards
as public JSON APIs intended for programmatic consumption:

  Greenhouse:  https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
  Lever:       https://api.lever.co/v0/postings/{token}?mode=json

Both return full job descriptions, so the enricher skips these jobs entirely.
Their application forms are also public and standardised, which makes them the
only platforms where the Submission Executor can complete a true end-to-end
apply without any login.

Board discovery is two-layered:
  1. SEED_BOARDS — curated tokens, editable below.
  2. DuckDuckGo — `site:boards.greenhouse.io {role}` style searches surface
     companies currently hiring for the target role; tokens are extracted
     from result URLs.
"""
from __future__ import annotations

import html as html_lib
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import unquote

import httpx

from state import GlobalState

MAX_JOBS_PER_SOURCE = 25     # cap across all Greenhouse boards / all Lever boards
MAX_BOARDS          = 12     # boards fetched per platform (seeds + discovered)
_BOARD_WORKERS      = 5

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Curated board tokens — companies that regularly hire AI/ML/backend roles.
# Add your own: the token is the slug in boards.greenhouse.io/<token> or
# jobs.lever.co/<token>.
SEED_BOARDS: dict[str, list[str]] = {
    "greenhouse": ["anthropic", "openai", "databricks", "scaleai", "weightsandbiases"],
    "lever": ["mistral", "palantir", "plaid"],
}

# Title tokens too generic to count as a role match on their own
_GENERIC_TOKENS = {"the", "and", "of", "a", "an", "in", "for", "with", "to"}


# ── Entry point ───────────────────────────────────────────────────────────────

def run(state: GlobalState) -> GlobalState:
    logs     = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    role   = state.get("target_role", "")
    market = state.get("target_market", "")
    logs.append(f"[ats_boards] Greenhouse + Lever discovery for '{role}' (public JSON APIs)")

    # 1. Collect board tokens: seeds + DDG-discovered
    gh_tokens = list(SEED_BOARDS["greenhouse"])
    lv_tokens = list(SEED_BOARDS["lever"])
    try:
        found_gh, found_lv = _discover_boards(role)
        gh_tokens += [t for t in found_gh if t not in gh_tokens]
        lv_tokens += [t for t in found_lv if t not in lv_tokens]
        logs.append(
            f"[ats_boards] Boards: {len(gh_tokens)} greenhouse, {len(lv_tokens)} lever "
            f"({len(found_gh) + len(found_lv)} discovered via web search)"
        )
    except Exception as exc:
        logs.append(f"[ats_boards] Board discovery failed ({exc}) — using seeds only.")

    gh_tokens = gh_tokens[:MAX_BOARDS]
    lv_tokens = lv_tokens[:MAX_BOARDS]

    # 2. Fetch boards concurrently
    jobs: list[dict] = []
    with ThreadPoolExecutor(max_workers=_BOARD_WORKERS, thread_name_prefix="jh-ats") as pool:
        futures = {pool.submit(_fetch_greenhouse_board, t): ("greenhouse", t) for t in gh_tokens}
        futures |= {pool.submit(_fetch_lever_board, t): ("lever", t) for t in lv_tokens}
        for fut in as_completed(futures):
            platform, token = futures[fut]
            try:
                jobs.extend(fut.result())
            except Exception as exc:
                logs.append(f"[ats_boards] {platform}/{token}: {exc}")

    # 3. Filter to the target role, then (leniently) to the target market
    role_matched = [j for j in jobs if _title_matches(j["title"], role)]
    final = _filter_by_market(role_matched, market)

    # 4. Per-platform cap, newest first
    gh_jobs = [j for j in final if j["platform"] == "Greenhouse"][:MAX_JOBS_PER_SOURCE]
    lv_jobs = [j for j in final if j["platform"] == "Lever"][:MAX_JOBS_PER_SOURCE]
    final = gh_jobs + lv_jobs

    logs.append(
        f"[ats_boards] {len(jobs)} postings fetched → {len(role_matched)} role matches "
        f"→ {len(final)} after market filter/cap."
    )
    return {**state, "discovered_jobs": existing + final, "logs": logs}


# ── Board discovery via DuckDuckGo ────────────────────────────────────────────

def _discover_boards(role: str) -> tuple[list[str], list[str]]:
    """Search DDG for company boards hiring the target role; return token lists."""
    gh: list[str] = []
    lv: list[str] = []
    queries = [
        f'site:boards.greenhouse.io "{role}"',
        f'site:job-boards.greenhouse.io "{role}"',
        f'site:jobs.lever.co "{role}"',
    ]
    with httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
        for q in queries:
            try:
                resp = client.get("https://html.duckduckgo.com/html/", params={"q": q, "kl": "wt-wt"})
                if resp.status_code != 200:
                    continue
                found_gh, found_lv = _extract_board_tokens(resp.text)
                gh += [t for t in found_gh if t not in gh]
                lv += [t for t in found_lv if t not in lv]
            except Exception:
                continue
            time.sleep(random.uniform(0.5, 1.2))
    return gh, lv


def _extract_board_tokens(html: str) -> tuple[list[str], list[str]]:
    """Pull greenhouse/lever board tokens out of DDG result HTML (handles redirect-encoded URLs)."""
    text = unquote(html)
    gh = re.findall(r"(?:job-)?boards\.greenhouse\.io/([A-Za-z0-9_]+)", text)
    lv = re.findall(r"jobs\.lever\.co/([A-Za-z0-9_-]+)", text)

    def clean(tokens: list[str]) -> list[str]:
        out: list[str] = []
        for t in tokens:
            t = t.lower()
            if t in ("embed", "jobs", "v1", "boards") or len(t) < 2:
                continue
            if t not in out:
                out.append(t)
        return out

    return clean(gh), clean(lv)


# ── Greenhouse ────────────────────────────────────────────────────────────────

def _fetch_greenhouse_board(token: str) -> list[dict]:
    with httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
        resp = client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
            params={"content": "true"},
        )
        if resp.status_code != 200:
            return []
        company = _greenhouse_company_name(client, token)
    return _parse_greenhouse_jobs(resp.json(), company or token.title())


def _greenhouse_company_name(client: httpx.Client, token: str) -> str:
    try:
        resp = client.get(f"https://boards-api.greenhouse.io/v1/boards/{token}")
        if resp.status_code == 200:
            return resp.json().get("name", "")
    except Exception:
        pass
    return ""


def _parse_greenhouse_jobs(data: dict, company: str) -> list[dict]:
    jobs = []
    for j in data.get("jobs", []):
        if not j.get("absolute_url") or not j.get("title"):
            continue
        # content is HTML-escaped HTML — unescape twice-encoded entities, then strip tags
        content = _clean_html(html_lib.unescape(j.get("content") or ""))
        jobs.append({
            "id":           f"gh_{j.get('id')}",
            "platform":     "Greenhouse",
            "title":        j["title"].strip(),
            "company":      company,
            "location":     (j.get("location") or {}).get("name", ""),
            "url":          j["absolute_url"],
            "description":  content[:4000],
            "salary_range": None,
            "job_type":     None,
            "scraped_at":   datetime.now(timezone.utc).isoformat(),
        })
    return jobs


# ── Lever ─────────────────────────────────────────────────────────────────────

def _fetch_lever_board(token: str) -> list[dict]:
    with httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
        resp = client.get(f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"})
    if resp.status_code != 200:
        return []
    return _parse_lever_postings(resp.json(), token)


def _parse_lever_postings(data: list, token: str) -> list[dict]:
    jobs = []
    for p in data if isinstance(data, list) else []:
        if not p.get("hostedUrl") or not p.get("text"):
            continue
        cats = p.get("categories") or {}
        location = cats.get("location") or ""
        if (p.get("workplaceType") or "").lower() == "remote" and "remote" not in location.lower():
            location = f"{location} (Remote)".strip()
        jobs.append({
            "id":           f"lv_{p.get('id')}",
            "platform":     "Lever",
            "title":        p["text"].strip(),
            "company":      token.replace("-", " ").title(),
            "location":     location,
            "url":          p["hostedUrl"],
            "apply_url":    p.get("applyUrl") or f"{p['hostedUrl']}/apply",
            "description":  (p.get("descriptionPlain") or "")[:4000],
            "salary_range": None,
            "job_type":     cats.get("commitment"),
            "scraped_at":   datetime.now(timezone.utc).isoformat(),
        })
    return jobs


# ── Filtering ─────────────────────────────────────────────────────────────────

def _title_matches(title: str, role: str) -> bool:
    """True if the job title shares at least one meaningful token with the target role."""
    role_tokens = {
        t for t in re.split(r"[^a-z0-9+#]+", role.lower())
        if t and t not in _GENERIC_TOKENS
    }
    if not role_tokens:
        return True
    title_l = title.lower()
    return any(t in title_l for t in role_tokens)


def _filter_by_market(jobs: list[dict], market: str) -> list[dict]:
    """Keep jobs in the target market or remote. Lenient: if that empties the
    list, return everything — a remote-friendly ATS role elsewhere is still
    worth scoring."""
    if not market:
        return jobs
    market_l = market.lower()
    filtered = [
        j for j in jobs
        if market_l in (j.get("location") or "").lower()
        or "remote" in (j.get("location") or "").lower()
        or "remote" in j.get("title", "").lower()
    ]
    return filtered if filtered else jobs


def _clean_html(html: str) -> str:
    """Strip tags, unescape entities, normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()
