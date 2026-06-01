import time
import random
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, Page, BrowserContext

from config import settings
from state import GlobalState

MAX_JOBS = 25

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _base_url(market: str) -> str:
    return "https://in.indeed.com" if "india" in market.lower() else "https://www.indeed.com"


def run(state: GlobalState) -> GlobalState:
    logs     = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    role   = state["target_role"]
    market = state["target_market"]
    logs.append(f"[indeed] Searching for '{role}' in {market}...")

    jobs: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-extensions",
                ],
            )
            context = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1366, "height": 768},
                locale="en-US",
            )
            _stealth(context)
            page = context.new_page()
            page.set_default_timeout(45000)

            if settings.indeed_email and settings.indeed_password:
                _login(page, market)

            jobs = _search_jobs(page, role, market)
            browser.close()
    except Exception as exc:
        logs.append(f"[indeed] Error: {exc}")

    logs.append(f"[indeed] Collected {len(jobs)} listings.")
    return {**state, "discovered_jobs": existing + jobs, "logs": logs}


# ── Anti-detection ────────────────────────────────────────────────────────────

def _stealth(ctx: BrowserContext) -> None:
    ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver',  { get: () => undefined });
        Object.defineProperty(navigator, 'plugins',    { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages',  { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'platform',   { get: () => 'Win32' });
        window.chrome = { runtime: {} };
    """)


# ── Auth ──────────────────────────────────────────────────────────────────────

def _login(page: Page, market: str) -> None:
    base = _base_url(market)
    try:
        page.goto(f"{base}/account/login", wait_until="domcontentloaded", timeout=30000)
        _delay(1, 2)
        page.fill("input[name='__email']", settings.indeed_email)
        _delay(0.5, 1.0)
        page.click("button[type='submit']")
        page.wait_for_selector("input[name='__password']", timeout=8000)
        page.fill("input[name='__password']", settings.indeed_password)
        _delay(0.5, 1.0)
        page.click("button[type='submit']")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        _delay(1, 2)
    except Exception:
        pass


# ── Search ────────────────────────────────────────────────────────────────────

def _search_jobs(page: Page, role: str, market: str) -> list[dict]:
    base = _base_url(market)
    url  = f"{base}/jobs?q={quote_plus(role)}&l={quote_plus(market)}&sort=date&fromage=7"

    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    # Indeed is a React SPA — wait for job cards to actually render
    try:
        page.wait_for_selector("[data-jk], .job_seen_beacon, .jobsearch-ResultsList li", timeout=15000)
    except Exception:
        _delay(3, 5)

    jobs: list[dict] = []
    seen: set[str]   = set()

    for page_num in range(3):
        if page_num > 0:
            next_btn = (
                page.query_selector("a[data-testid='pagination-page-next']") or
                page.query_selector("[aria-label='Next Page']") or
                page.query_selector("a[aria-label*='next']")
            )
            if not next_btn:
                break
            next_btn.click()
            try:
                page.wait_for_selector("[data-jk], .job_seen_beacon", timeout=12000)
            except Exception:
                _delay(3, 4)

        # Try multiple card selector strategies
        cards = (
            page.query_selector_all("[data-jk]") or
            page.query_selector_all(".job_seen_beacon") or
            page.query_selector_all(".resultContent") or
            page.query_selector_all("[class*='result_']")
        )

        if not cards:
            _delay(2, 3)
            continue

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

    return jobs


def _extract_card(page: Page, card, base: str) -> dict | None:
    # Title — try multiple selectors in priority order
    title_el = (
        card.query_selector("h2.jobTitle a span") or
        card.query_selector("h2.jobTitle span[title]") or
        card.query_selector("[data-testid='jobTitle'] span") or
        card.query_selector("h2 a span[title]") or
        card.query_selector("h2 a")
    )
    # Company
    company_el = (
        card.query_selector("[data-testid='company-name']") or
        card.query_selector(".companyName") or
        card.query_selector("[class*='companyName']") or
        card.query_selector("span.companyName")
    )
    # Location
    location_el = (
        card.query_selector("[data-testid='text-location']") or
        card.query_selector(".companyLocation") or
        card.query_selector("[class*='companyLocation']")
    )
    # Link
    link_el = (
        card.query_selector("h2.jobTitle a") or
        card.query_selector("h2 a")
    )

    if not title_el or not company_el:
        return None

    href   = (link_el.get_attribute("href") or "") if link_el else ""
    url    = href if href.startswith("http") else base + href
    job_id = f"id_{url.split('jk=')[-1].split('&')[0]}" if "jk=" in url else f"id_{uuid.uuid4().hex[:8]}"

    # Load JD from side panel / job page
    description = ""
    try:
        if link_el:
            link_el.click()
            try:
                page.wait_for_selector("#jobDescriptionText, .jobsearch-jobDescriptionText", timeout=6000)
            except Exception:
                _delay(1, 2)
            desc_el = (
                page.query_selector("#jobDescriptionText") or
                page.query_selector(".jobsearch-jobDescriptionText")
            )
            description = desc_el.inner_text().strip() if desc_el else ""
    except Exception:
        pass

    salary_el = (
        card.query_selector("[class*='salary-snippet']") or
        card.query_selector("[data-testid='attribute_snippet_testid']")
    )
    type_el = card.query_selector("[class*='job-snippet'] li")

    title_text = title_el.get_attribute("title") or title_el.inner_text().strip()

    return {
        "id":          job_id,
        "platform":    "Indeed",
        "title":       title_text,
        "company":     company_el.inner_text().strip(),
        "location":    location_el.inner_text().strip() if location_el else "",
        "url":         url,
        "description": description[:4000],
        "salary_range": salary_el.inner_text().strip() if salary_el else None,
        "job_type":    type_el.inner_text().strip() if type_el else None,
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
    }


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
