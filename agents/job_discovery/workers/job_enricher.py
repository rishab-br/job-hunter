"""
Job enricher — sits between the scrapers and the JD analyzer.

Two enrichment passes run in parallel using bounded thread pools:

  Phase 1 — Description fetch
    The LinkedIn guest API only returns title/company/URL.  For each job whose
    description is missing or thin, we httpx-GET the job's own detail page (the
    same URL the user would visit in a browser) and extract the main body text.
    This works for LinkedIn public job pages, Indeed, and Naukri — all of which
    render their job descriptions server-side for SEO.

  Phase 2 — Company context via DuckDuckGo
    For each unique company we run one DuckDuckGo HTML search and collect the
    top result snippets.  The snippets (tech stack, size, culture signals) are
    appended to the job description so the JD analyzer and relevance scorer get
    richer context without any schema changes.

Both passes are best-effort: a failed fetch or search is logged and skipped —
the downstream nodes degrade gracefully on an empty description.
"""

from __future__ import annotations

import html as html_lib
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import httpx

from state import GlobalState

# ── Tuning knobs ──────────────────────────────────────────────────────────────

MAX_DESC_CHARS   = 4_000   # chars of extracted job page text sent to the JD analyzer
MAX_DDG_SNIPPETS = 4       # top N DuckDuckGo result snippets per company
_DESC_WORKERS    = 5       # concurrent job-page fetches
_DDG_WORKERS     = 3       # concurrent DuckDuckGo searches (be polite)
_MIN_DESC_LEN    = 120     # skip fetch if description already this long

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Keywords that mark the start of a job-description section in page text
_JD_ANCHORS = [
    "responsibilities", "requirements", "qualifications",
    "about the role", "about this role", "what you'll do",
    "what you will do", "what we're looking for",
    "key responsibilities", "job description", "role overview",
    "your role", "the role", "skills required",
]


# ── Entry point ───────────────────────────────────────────────────────────────

def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    jobs = list(state.get("discovered_jobs") or [])

    if not jobs:
        logs.append("[job_enricher] No jobs to enrich — skipping.")
        return {**state, "logs": logs}

    target_role = state.get("target_role", "")

    # ── Phase 1: description pages ────────────────────────────────────────────
    needs_desc = [i for i, j in enumerate(jobs)
                  if j.get("url") and len(j.get("description") or "") < _MIN_DESC_LEN]

    if needs_desc:
        logs.append(f"[job_enricher] Phase 1 — fetching descriptions for {len(needs_desc)} jobs...")
        jobs = _fetch_descriptions(jobs, needs_desc, logs)
    else:
        logs.append("[job_enricher] Phase 1 — all jobs already have descriptions, skipping fetch.")

    # ── Phase 2: DuckDuckGo company context ───────────────────────────────────
    companies = list({j["company"] for j in jobs if j.get("company")})
    if companies:
        logs.append(f"[job_enricher] Phase 2 — web search for {len(companies)} companies...")
        company_ctx = _fetch_company_contexts(companies, target_role, logs)

        # Append context to each job's description field
        for job in jobs:
            ctx = company_ctx.get(job.get("company", ""), "")
            if ctx:
                existing = job.get("description") or ""
                job["description"] = existing + f"\n\n[COMPANY CONTEXT FROM WEB]\n{ctx}"

    logs.append("[job_enricher] Enrichment complete.")
    return {**state, "discovered_jobs": jobs, "logs": logs}


# ── Phase 1: description fetching ────────────────────────────────────────────

def _fetch_descriptions(
    jobs: list[dict],
    indices: list[int],
    logs: list[str],
) -> list[dict]:
    enriched = list(jobs)

    def fetch_one(idx: int) -> tuple[int, str]:
        job = enriched[idx]
        try:
            text = _get_job_description(job["url"], job.get("platform", ""))
            return idx, text
        except Exception:
            return idx, ""

    fetched = failed = 0
    with ThreadPoolExecutor(max_workers=_DESC_WORKERS, thread_name_prefix="jh-desc") as pool:
        futures = {pool.submit(fetch_one, i): i for i in indices}
        for fut in as_completed(futures):
            idx, text = fut.result()
            if text:
                enriched[idx]["description"] = text
                fetched += 1
            else:
                failed += 1

    logs.append(f"[job_enricher] Descriptions — {fetched} fetched, {failed} failed/skipped.")
    return enriched


def _get_job_description(url: str, platform: str) -> str:
    """Fetch a job detail page and return the main description text."""
    with httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
        resp = client.get(url)
    if resp.status_code != 200:
        return ""
    return _extract_description(resp.text, platform)


def _extract_description(html: str, platform: str) -> str:
    """
    Extract job-description text from raw HTML.

    Strategy:
      1. Remove script/style/nav/header/footer noise.
      2. For known platforms try a platform-specific CSS class selector.
      3. Fall back to keyword anchoring: find the first occurrence of a
         phrase like "responsibilities" and extract forward from there.
      4. Truncate to MAX_DESC_CHARS.
    """
    # Strip noisy containers
    html = re.sub(
        r"<(script|style|nav|header|footer|aside)[^>]*>.*?</(script|style|nav|header|footer|aside)>",
        " ", html, flags=re.DOTALL | re.IGNORECASE,
    )

    p = platform.lower()

    # Platform-specific class-based extraction (faster, more precise)
    platform_selectors = []
    if "linkedin" in p or "linkedin.com" in html[:500].lower():
        platform_selectors = [
            r'class="[^"]*show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>',
            r'class="[^"]*description__text[^"]*"[^>]*>(.*?)</(?:div|section)>',
        ]
    elif "indeed" in p:
        platform_selectors = [
            r'id="jobDescriptionText"[^>]*>(.*?)</div>',
            r'class="[^"]*jobsearch-JobComponent-description[^"]*"[^>]*>(.*?)</div>',
        ]
    elif "naukri" in p:
        platform_selectors = [
            r'class="[^"]*job-desc[^"]*"[^>]*>(.*?)</(?:div|section)>',
            r'class="[^"]*jd-header[^"]*"[^>]*>(.*?)</(?:div|section)>',
        ]

    for pattern in platform_selectors:
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m:
            return _clean_to_text(m.group(1))[:MAX_DESC_CHARS]

    # Generic fallback: strip all tags, then anchor on JD keywords
    full_text = _clean_to_text(html)
    lower = full_text.lower()

    earliest = len(full_text)
    for anchor in _JD_ANCHORS:
        pos = lower.find(anchor)
        if 0 < pos < earliest:
            earliest = pos

    if earliest < len(full_text) - 300:
        full_text = full_text[max(0, earliest - 80):]   # keep a little context before the keyword

    return full_text[:MAX_DESC_CHARS]


def _clean_to_text(html: str) -> str:
    """Strip HTML tags, unescape HTML entities, and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = html_lib.unescape(text)          # &amp; → &,  &gt; → >,  &#x27; → '  etc.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Phase 2: DuckDuckGo company context ──────────────────────────────────────

def _fetch_company_contexts(
    companies: list[str],
    target_role: str,
    logs: list[str],
) -> dict[str, str]:
    """Return company → joined-snippet-text via parallel DuckDuckGo searches."""
    results: dict[str, str] = {}

    def search_one(company: str) -> tuple[str, str]:
        # Stagger start times to avoid bursting DDG simultaneously
        time.sleep(random.uniform(0.4, 1.2))
        try:
            snippets = _ddg_search(company, target_role)
            return company, "\n".join(snippets)
        except Exception:
            return company, ""

    enriched_count = 0
    with ThreadPoolExecutor(max_workers=_DDG_WORKERS, thread_name_prefix="jh-ddg") as pool:
        futures = {pool.submit(search_one, c): c for c in companies}
        for fut in as_completed(futures):
            company, ctx = fut.result()
            if ctx:
                results[company] = ctx
                enriched_count += 1

    logs.append(
        f"[job_enricher] Company context — {enriched_count}/{len(companies)} companies enriched via DuckDuckGo."
    )
    return results


def _ddg_search(company: str, role: str) -> list[str]:
    """
    Hit DuckDuckGo's non-JS HTML endpoint and return top result snippets.
    html.duckduckgo.com/html/ is the official lite/accessible version of DDG
    that works without JavaScript and without an API key.
    """
    query = f'"{company}" engineering culture tech stack {role}'
    with httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
        resp = client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "wt-wt"},    # kl=wt-wt → worldwide, no locale bias
        )
    if resp.status_code != 200:
        return []

    # DDG HTML lite uses <a class="result__snippet"> for each result description
    raw = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    snippets: list[str] = []
    for s in raw[:MAX_DDG_SNIPPETS]:
        clean = re.sub(r"<[^>]+>", " ", s)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean:
            snippets.append(clean)

    return snippets
