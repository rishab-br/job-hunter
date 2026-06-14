import time
import random
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, Page, BrowserContext

from state import GlobalState

MAX_JOBS = 25
BASE_URL = "https://www.naukri.com"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def run(state: GlobalState) -> GlobalState:
    logs     = list(state.get("logs") or [])
    existing = list(state.get("discovered_jobs") or [])

    market       = state["target_market"]
    search_roles = (state.get("search_roles") or [state["target_role"]])[:3]
    logs.append(f"[naukri] Searching {len(search_roles)} title(s) in {market}: {search_roles}")

    jobs: list[dict] = []
    seen_ids: set[str] = set()
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
            context = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1366, "height": 768},
                locale="en-IN",
            )
            _stealth(context)
            page = context.new_page()
            page.set_default_timeout(45000)
            for role in search_roles:
                for job in _search_jobs(page, role, market):
                    if job["id"] not in seen_ids:
                        jobs.append(job)
                        seen_ids.add(job["id"])
            browser.close()
    except Exception as exc:
        logs.append(f"[naukri] Error: {exc}")

    logs.append(f"[naukri] Collected {len(jobs)} listings.")
    return {**state, "discovered_jobs": existing + jobs, "logs": logs}


# ── Anti-detection ────────────────────────────────────────────────────────────

def _stealth(ctx: BrowserContext) -> None:
    ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver',  { get: () => undefined });
        Object.defineProperty(navigator, 'plugins',    { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages',  { get: () => ['en-IN', 'en'] });
        window.chrome = { runtime: {} };
    """)


# ── Search ────────────────────────────────────────────────────────────────────

def _search_jobs(page: Page, role: str, market: str) -> list[dict]:
    # Build SEO slug URL (e.g. /ai-engineer-jobs-in-india)
    role_slug     = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")
    location_slug = re.sub(r"[^a-z0-9]+", "-", market.lower()).strip("-")
    seo_url  = f"{BASE_URL}/{role_slug}-jobs-in-{location_slug}"
    # Fallback: query-param URL
    qp_url   = f"{BASE_URL}/jobs?keyword={quote_plus(role)}&location={quote_plus(market)}&experience=0-8&sort=1"

    # Try SEO URL first, fall back to query-param URL if no cards found
    for attempt_url in [seo_url, qp_url]:
        page.goto(attempt_url, wait_until="domcontentloaded", timeout=45000)
        _delay(2, 3)
        _dismiss_popups(page)

        # Wait for job cards to appear
        try:
            page.wait_for_selector(
                ".srp-jobtuple-wrapper, article.jobTuple, [class*='jobTuple'], .list",
                timeout=10000,
            )
        except Exception:
            _delay(2, 3)

        cards = _get_cards(page)
        if cards:
            break
    else:
        return []

    jobs: list[dict] = []
    seen: set[str]   = set()

    for page_num in range(3):
        if page_num > 0:
            next_btn = (
                page.query_selector("a[class*='next']") or
                page.query_selector("[class*='pagination'] a:last-child") or
                page.query_selector("a[aria-label*='next' i]")
            )
            if not next_btn:
                break
            next_btn.click()
            try:
                page.wait_for_selector(".srp-jobtuple-wrapper, article.jobTuple", timeout=10000)
            except Exception:
                _delay(2, 3)
            _dismiss_popups(page)

        for card in _get_cards(page):
            try:
                job = _extract_card(page, card)
                if job and job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
                    if len(jobs) >= MAX_JOBS:
                        return jobs
            except Exception:
                continue

    return jobs


def _get_cards(page: Page) -> list:
    return (
        page.query_selector_all(".srp-jobtuple-wrapper") or
        page.query_selector_all("article.jobTuple") or
        page.query_selector_all("[class*='jobTuple']") or
        page.query_selector_all(".list > li")
    )


def _dismiss_popups(page: Page) -> None:
    for selector in [
        "button.loginButton",
        "[class*='close']",
        "[data-ga-track*='close']",
        "button[title='Close']",
        ".nI-gNb-xBtn",
    ]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                _delay(0.3, 0.6)
        except Exception:
            pass


# ── Card extraction ────────────────────────────────────────────────────────────

def _extract_card(page: Page, card) -> dict | None:
    # Title — current Naukri structure
    title_el = (
        card.query_selector("a.title") or
        card.query_selector(".row1 a") or
        card.query_selector("[class*='title'] a") or
        card.query_selector("h2 a")
    )
    # Company
    company_el = (
        card.query_selector("a.comp-name") or
        card.query_selector(".comp-dtls-wrap a") or
        card.query_selector("[class*='comp-name']") or
        card.query_selector(".companyInfo span") or
        card.query_selector("a.subTitle")
    )
    # Location
    location_el = (
        card.query_selector(".loc span") or
        card.query_selector("[class*='location'] li") or
        card.query_selector(".locWdth span") or
        card.query_selector(".location span")
    )
    # Salary
    salary_el = (
        card.query_selector(".sal-wrap span") or
        card.query_selector("[class*='salary']")
    )
    # Experience
    exp_el = (
        card.query_selector(".exp-wrap span") or
        card.query_selector("[class*='experience'] span")
    )

    if not title_el or not company_el:
        return None

    url    = title_el.get_attribute("href") or ""
    job_id = _extract_naukri_id(url)

    # Fetch full description in a new tab
    description = ""
    if url:
        try:
            new_page = page.context.new_page()
            new_page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _delay(1, 2)
            desc_el = (
                new_page.query_selector(".job-desc") or
                new_page.query_selector("[class*='jobDescContainer']") or
                new_page.query_selector(".jdSection") or
                new_page.query_selector("#job_jd")
            )
            description = desc_el.inner_text().strip() if desc_el else ""
            new_page.close()
        except Exception:
            pass

    return {
        "id":          job_id,
        "platform":    "Naukri",
        "title":       title_el.inner_text().strip(),
        "company":     company_el.inner_text().strip(),
        "location":    location_el.inner_text().strip() if location_el else "",
        "url":         url,
        "description": description[:4000],
        "salary_range": salary_el.inner_text().strip() if salary_el else None,
        "job_type":    exp_el.inner_text().strip() if exp_el else None,
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
    }


def _extract_naukri_id(url: str) -> str:
    match = re.search(r"-(\d+)\.htm", url)
    return f"nk_{match.group(1)}" if match else f"nk_{uuid.uuid4().hex[:8]}"


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
