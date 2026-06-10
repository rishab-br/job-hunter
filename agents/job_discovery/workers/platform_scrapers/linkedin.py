"""
LinkedIn job discovery — guest mode, zero login.

Uses LinkedIn's public guest jobs API endpoint, which returns job card HTML
without requiring any authentication, cookies, or session state.
No account is touched, so there is no ban risk on your personal profile.
"""
import html as html_lib
import re
import time
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from state import GlobalState

MAX_JOBS  = 25

# LinkedIn's public guest search endpoint — works without cookies or a session.
# This is the same endpoint LinkedIn's own public job-search page calls under the hood.
_GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.linkedin.com/jobs/search/",
}


def run(state: GlobalState) -> GlobalState:
    logs     = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    role   = state.get("target_role", "")
    market = state.get("target_market", "")
    logs.append(f"[linkedin] Guest search: '{role}' in {market} (no login required)")

    jobs: list[dict] = []
    start = 0

    try:
        with httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
            while len(jobs) < MAX_JOBS:
                resp = client.get(_GUEST_API, params={
                    "keywords": role,
                    "location": market,
                    "start":    start,
                    "count":    25,
                    "f_TPR":    "r604800",   # last 7 days
                    "sortBy":   "DD",
                })
                if resp.status_code != 200:
                    logs.append(f"[linkedin] API returned HTTP {resp.status_code} at offset {start} — stopping.")
                    break

                batch = _parse_listings(resp.text)
                if not batch:
                    break   # no more results

                seen_ids = {j["id"] for j in jobs}
                for job in batch:
                    if job["id"] not in seen_ids:
                        jobs.append(job)
                        seen_ids.add(job["id"])
                        if len(jobs) >= MAX_JOBS:
                            break

                if len(jobs) >= MAX_JOBS:
                    break

                start += len(batch)
                time.sleep(random.uniform(1.5, 3.0))   # polite pacing between pages

    except Exception as exc:
        logs.append(f"[linkedin] Error: {exc}")

    logs.append(f"[linkedin] Collected {len(jobs)} listings.")
    return {**state, "discovered_jobs": existing + jobs, "logs": logs}


# ── HTML parsing ──────────────────────────────────────────────────────────────
# The guest API returns raw <li>…</li> fragments (no wrapping document).

def _parse_listings(html: str) -> list[dict]:
    jobs = []
    for card_html in re.findall(r"<li>(.*?)</li>", html, re.DOTALL):
        job = _parse_card(card_html)
        if job:
            jobs.append(job)
    return jobs


def _parse_card(card: str) -> Optional[dict]:
    # Job URL — the primary key; skip the card if it's absent.
    # LinkedIn returns regional subdomains (in., uk., ca., etc.) not always www.
    url_m = re.search(
        r'href="(https://[a-z]{2,}\.linkedin\.com/jobs/view/[^"]+)"',
        card,
    )
    if not url_m:
        return None
    # Strip tracking query params — keep only the clean canonical URL
    url = url_m.group(1).split("?")[0].rstrip("/")

    # Stable job ID: numeric portion at the end of the slug
    slug = url.split("/jobs/view/")[-1]           # e.g. "python-dev-at-acme-4397658289"
    numeric_m = re.search(r"(\d{7,})$", slug)     # LinkedIn IDs are 7-10 digit numbers
    job_id = f"li_{numeric_m.group(1)}" if numeric_m else f"li_{uuid.uuid4().hex[:8]}"

    # Job title  ── h3.base-search-card__title
    title = _text_between(card, r"base-search-card__title[^>]*>", r"</h3>")
    if not title:
        return None   # malformed card

    # Company name  ── h4.base-search-card__subtitle (may wrap an <a>)
    company = _text_between(card, r"base-search-card__subtitle[^>]*>", r"</h4>")

    # Location  ── span.job-search-card__location
    location = _text_between(card, r"job-search-card__location[^>]*>", r"</span>")

    return {
        "id":          job_id,
        "platform":    "LinkedIn",
        "title":       title,
        "company":     company or "",
        "location":    location or "",
        "url":         url,
        # Descriptions aren't available in the guest listing view.
        # The job scorer uses title + company + role for relevance ranking.
        "description": "",
        "salary_range": None,
        "job_type":    None,
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
    }


def _text_between(html: str, opener_pattern: str, closer: str) -> str:
    """Extract and clean text between a regex-matched opener tag and a literal closer."""
    m = re.search(opener_pattern + r"(.*?)" + re.escape(closer), html, re.DOTALL)
    if not m:
        return ""
    raw = m.group(1)
    stripped = re.sub(r"<[^>]+>", " ", raw)        # remove nested tags
    unescaped = html_lib.unescape(stripped)          # &amp; → &  etc.
    return re.sub(r"\s+", " ", unescaped).strip()
