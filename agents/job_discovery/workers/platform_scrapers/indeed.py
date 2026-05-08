import time
import random
import uuid
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, Page

from config import settings
from state import GlobalState

MAX_JOBS = 25


def _base_url(market: str) -> str:
    return "https://in.indeed.com" if "india" in market.lower() else "https://www.indeed.com"


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    logs.append(
        f"[indeed] Searching for '{state['target_role']}' in {state['target_market']}..."
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
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Indeed allows unauthenticated search
            if settings.indeed_email and settings.indeed_password:
                _login(page, state["target_market"])

            jobs = _search_jobs(page, state["target_role"], state["target_market"])
            browser.close()
    except Exception as exc:
        logs.append(f"[indeed] Error: {exc}")

    logs.append(f"[indeed] Collected {len(jobs)} listings.")
    return {
        **state,
        "discovered_jobs": existing + jobs,
        "logs": logs,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _login(page: Page, market: str) -> None:
    base = _base_url(market)
    page.goto(f"{base}/account/login", wait_until="networkidle")
    _delay()
    try:
        page.fill("input[name='__email']", settings.indeed_email)
        _delay(0.5, 1.0)
        page.click("button[type='submit']")
        page.wait_for_selector("input[name='__password']", timeout=5000)
        page.fill("input[name='__password']", settings.indeed_password)
        _delay()
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
    except Exception:
        pass  # Continue without login if flow changes


def _search_jobs(page: Page, role: str, market: str) -> list[dict]:
    base = _base_url(market)
    page.goto(
        f"{base}/jobs?q={role}&l={market}&fromage=7&sort=date",
        wait_until="networkidle",
    )
    _delay(2, 3)

    jobs: list[dict] = []
    seen: set[str] = set()

    # Paginate up to 3 pages
    for _ in range(3):
        cards = page.query_selector_all("[class*='job_seen_beacon']")
        if not cards:
            cards = page.query_selector_all(".resultContent")

        for card in cards:
            try:
                job = _extract_card(page, card, base)
                if job and job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
                    if len(jobs) >= MAX_JOBS:
                        return jobs
            except Exception:
                continue

        # Try next page
        next_btn = page.query_selector("a[data-testid='pagination-page-next']")
        if not next_btn:
            break
        next_btn.click()
        page.wait_for_load_state("networkidle")
        _delay(2, 3)

    return jobs


def _extract_card(page: Page, card, base: str) -> dict | None:
    title_el = card.query_selector("[class*='jobTitle'] a")
    company_el = card.query_selector("[class*='companyName']")
    location_el = card.query_selector("[class*='companyLocation']")

    if not title_el or not company_el:
        return None

    href = title_el.get_attribute("href") or ""
    url = href if href.startswith("http") else base + href
    job_id = f"id_{uuid.uuid4().hex[:8]}"

    # Extract job key from URL for deduplication
    if "jk=" in url:
        job_id = f"id_{url.split('jk=')[-1].split('&')[0]}"

    # Click to load description
    description = ""
    try:
        title_el.click()
        page.wait_for_selector("#jobDescriptionText", timeout=4000)
        desc_el = page.query_selector("#jobDescriptionText")
        description = desc_el.inner_text().strip() if desc_el else ""
    except Exception:
        pass

    salary_el = card.query_selector("[class*='salary-snippet']")
    type_el = card.query_selector("[class*='job-snippet'] li")

    return {
        "id": job_id,
        "platform": "indeed",
        "title": title_el.inner_text().strip(),
        "company": company_el.inner_text().strip(),
        "location": location_el.inner_text().strip() if location_el else "",
        "url": url,
        "description": description[:4000],
        "salary_range": salary_el.inner_text().strip() if salary_el else None,
        "job_type": type_el.inner_text().strip() if type_el else None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
