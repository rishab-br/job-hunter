import time
import random
import uuid
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, Page, BrowserContext

from config import settings
from state import GlobalState

MAX_JOBS   = 25
LOGIN_URL  = "https://www.linkedin.com/login"
SEARCH_URL = "https://www.linkedin.com/jobs/search/"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def run(state: GlobalState) -> GlobalState:
    logs     = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    if not settings.linkedin_email or not settings.linkedin_password:
        logs.append("[linkedin] No credentials configured — skipping.")
        return {**state, "logs": logs, "discovered_jobs": existing}

    logs.append(f"[linkedin] Searching for '{state['target_role']}' in {state['target_market']}...")

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
                ],
            )
            context = browser.new_context(user_agent=_UA, viewport={"width": 1280, "height": 800})
            _stealth(context)
            page = context.new_page()
            _login(page)
            jobs = _search_jobs(page, state["target_role"], state["target_market"])
            browser.close()
    except Exception as exc:
        logs.append(f"[linkedin] Error: {exc}")

    logs.append(f"[linkedin] Collected {len(jobs)} listings.")
    return {**state, "discovered_jobs": existing + jobs, "logs": logs}


# ── Anti-detection ────────────────────────────────────────────────────────────

def _stealth(ctx: BrowserContext) -> None:
    ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
    """)


# ── Auth ──────────────────────────────────────────────────────────────────────

def _login(page: Page) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    _delay(1, 2)
    page.fill("#username", settings.linkedin_email)
    _delay(0.5, 1.0)
    page.fill("#password", settings.linkedin_password)
    _delay(0.5, 1.0)
    page.click("button[type='submit']")
    try:
        page.wait_for_url("**/feed**", timeout=15000)
    except Exception:
        pass
    _delay(2, 3)


# ── Search ────────────────────────────────────────────────────────────────────

def _search_jobs(page: Page, role: str, market: str) -> list[dict]:
    params = f"?keywords={role}&location={market}&f_TPR=r604800&sortBy=DD"
    page.goto(SEARCH_URL + params, wait_until="domcontentloaded", timeout=30000)
    _delay(2, 3)

    jobs: list[dict] = []
    seen: set[str]   = set()

    for _ in range(6):
        # Try multiple selector generations
        cards = (
            page.query_selector_all(".job-card-container") or
            page.query_selector_all(".jobs-search-results__list-item") or
            page.query_selector_all("[data-occludable-job-id]")
        )

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

        page.evaluate("window.scrollBy(0, 900)")
        _delay(1.5, 2.5)

    return jobs


def _extract_card(page: Page, card) -> dict | None:
    title_el = (
        card.query_selector(".job-card-list__title--link") or
        card.query_selector(".job-card-list__title") or
        card.query_selector("a[data-control-name='job_card_title']")
    )
    company_el = (
        card.query_selector(".job-card-container__company-name") or
        card.query_selector(".artdeco-entity-lockup__subtitle span")
    )
    location_el = (
        card.query_selector(".job-card-container__metadata-item") or
        card.query_selector(".job-card-container__metadata-wrapper li")
    )
    link_el = (
        card.query_selector("a.job-card-container__link") or
        card.query_selector("a.job-card-list__title--link")
    )

    if not title_el or not company_el:
        return None

    url = link_el.get_attribute("href") if link_el else ""
    if url and not url.startswith("http"):
        url = "https://www.linkedin.com" + url

    job_id = (
        f"li_{url.split('/jobs/view/')[-1].split('/')[0]}"
        if "/jobs/view/" in url
        else f"li_{uuid.uuid4().hex[:8]}"
    )

    description = ""
    try:
        card.click()
        page.wait_for_selector(".jobs-description__content", timeout=5000)
        desc_el = page.query_selector(".jobs-description__content")
        description = desc_el.inner_text().strip() if desc_el else ""
    except Exception:
        pass

    salary_el = card.query_selector(".job-card-container__salary-info")

    return {
        "id":          job_id,
        "platform":    "LinkedIn",
        "title":       title_el.inner_text().strip(),
        "company":     company_el.inner_text().strip(),
        "location":    location_el.inner_text().strip() if location_el else "",
        "url":         url,
        "description": description[:4000],
        "salary_range": salary_el.inner_text().strip() if salary_el else None,
        "job_type":    None,
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
    }


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
