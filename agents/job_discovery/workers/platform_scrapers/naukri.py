import time
import random
import re
import uuid
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, Page

from state import GlobalState

MAX_JOBS = 25
BASE_URL = "https://www.naukri.com"


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    logs.append(
        f"[naukri] Searching for '{state['target_role']}' in {state['target_market']}..."
    )

    jobs: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()
            jobs = _search_jobs(page, state["target_role"], state["target_market"])
            browser.close()
    except Exception as exc:
        logs.append(f"[naukri] Error: {exc}")

    logs.append(f"[naukri] Collected {len(jobs)} listings.")
    return {
        **state,
        "discovered_jobs": existing + jobs,
        "logs": logs,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _search_jobs(page: Page, role: str, market: str) -> list[dict]:
    role_slug = role.lower().replace(" ", "-")
    location_slug = market.lower().replace(" ", "-")
    url = f"{BASE_URL}/{role_slug}-jobs-in-{location_slug}"

    page.goto(url, wait_until="networkidle")
    _delay(2, 3)

    # Dismiss any popups
    try:
        page.click("button.loginButton", timeout=2000)
    except Exception:
        pass

    jobs: list[dict] = []
    seen: set[str] = set()

    for _ in range(3):
        cards = page.query_selector_all("article.jobTuple")
        if not cards:
            cards = page.query_selector_all(".srp-jobtuple-wrapper")

        for card in cards:
            try:
                job = _extract_card(page, card)
                if job and job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
                    if len(jobs) >= MAX_JOBS:
                        return jobs
            except Exception:
                continue

        next_btn = page.query_selector("a[class*='next']")
        if not next_btn:
            break
        next_btn.click()
        page.wait_for_load_state("networkidle")
        _delay(2, 3)

    return jobs


def _extract_card(page: Page, card) -> dict | None:
    title_el = card.query_selector("a.title")
    if not title_el:
        title_el = card.query_selector(".jobTitle a")
    company_el = card.query_selector("a.subTitle")
    if not company_el:
        company_el = card.query_selector(".companyInfo a")
    location_el = card.query_selector(".location span")
    salary_el = card.query_selector(".salary")
    exp_el = card.query_selector(".experience")

    if not title_el or not company_el:
        return None

    url = title_el.get_attribute("href") or ""
    job_id = _extract_naukri_id(url)

    # Open job in new tab to get description
    description = ""
    try:
        new_page = page.context.new_page()
        new_page.goto(url, wait_until="networkidle")
        _delay(1, 2)
        desc_el = new_page.query_selector(".job-desc")
        if not desc_el:
            desc_el = new_page.query_selector("[class*='jobDescContainer']")
        description = desc_el.inner_text().strip() if desc_el else ""
        new_page.close()
    except Exception:
        pass

    return {
        "id": job_id,
        "platform": "naukri",
        "title": title_el.inner_text().strip(),
        "company": company_el.inner_text().strip(),
        "location": location_el.inner_text().strip() if location_el else "",
        "url": url,
        "description": description[:4000],
        "salary_range": salary_el.inner_text().strip() if salary_el else None,
        "job_type": exp_el.inner_text().strip() if exp_el else None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_naukri_id(url: str) -> str:
    match = re.search(r"-(\d+)\.htm", url)
    return f"nk_{match.group(1)}" if match else f"nk_{uuid.uuid4().hex[:8]}"


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
