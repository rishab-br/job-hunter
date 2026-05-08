import time
import random
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, Page

from config import settings
from state import GlobalState

# Canonical status values used across the system
STATUS_APPLIED = "applied"
STATUS_VIEWED = "viewed"
STATUS_SHORTLISTED = "shortlisted"
STATUS_INTERVIEW = "interview_scheduled"
STATUS_REJECTED = "rejected"
STATUS_UNKNOWN = "unknown"


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    applications = state.get("applications") or []
    current_statuses = dict(state.get("application_statuses") or {})

    if not applications:
        logs.append("[application_monitor] No submitted applications to monitor.")
        return {**state, "logs": logs}

    logs.append(f"[application_monitor] Checking status for {len(applications)} application(s)...")

    # Group by platform to open one browser session per platform
    by_platform: dict[str, list[dict]] = {}
    for app in applications:
        by_platform.setdefault(app.get("platform", "unknown"), []).append(app)

    for platform, apps in by_platform.items():
        try:
            statuses = _check_platform(platform, apps)
            current_statuses.update(statuses)
            logs.append(f"[application_monitor] {platform}: checked {len(apps)} app(s).")
        except Exception as exc:
            logs.append(f"[application_monitor] {platform}: error — {exc}")

    changed = [
        f"{app.get('company')} → {current_statuses.get(app.get('job_id'), STATUS_UNKNOWN)}"
        for app in applications
        if current_statuses.get(app.get("job_id")) not in (STATUS_APPLIED, STATUS_UNKNOWN)
    ]
    if changed:
        logs.append(f"[application_monitor] Status updates: {', '.join(changed)}")
    else:
        logs.append("[application_monitor] No new status changes detected.")

    return {
        **state,
        "application_statuses": current_statuses,
        "logs": logs,
    }


# ── Platform-specific status checkers ─────────────────────────────────────────

def _check_platform(platform: str, apps: list[dict]) -> dict[str, str]:
    if platform == "linkedin":
        return _check_linkedin(apps)
    if platform == "indeed":
        return _check_indeed(apps)
    if platform == "naukri":
        return _check_naukri(apps)
    return {app["job_id"]: STATUS_UNKNOWN for app in apps}


def _check_linkedin(apps: list[dict]) -> dict[str, str]:
    if not settings.linkedin_email or not settings.linkedin_password:
        return {app["job_id"]: STATUS_UNKNOWN for app in apps}

    statuses: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _login_linkedin(page)

        page.goto(
            "https://www.linkedin.com/my-items/saved-jobs/?cardType=APPLIED",
            wait_until="networkidle",
        )
        _delay(2, 3)

        # Build a lookup from company name → status label on the page
        cards = page.query_selector_all(".job-card-container")
        platform_statuses: dict[str, str] = {}
        for card in cards:
            try:
                company_el = card.query_selector(".job-card-container__company-name")
                status_el = card.query_selector(".job-card-container__footer-item")
                if company_el and status_el:
                    company = company_el.inner_text().strip().lower()
                    raw_status = status_el.inner_text().strip().lower()
                    platform_statuses[company] = _normalise_linkedin_status(raw_status)
            except Exception:
                continue

        for app in apps:
            company_key = app.get("company", "").lower()
            statuses[app["job_id"]] = platform_statuses.get(company_key, STATUS_APPLIED)

        browser.close()
    return statuses


def _check_indeed(apps: list[dict]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        if settings.indeed_email and settings.indeed_password:
            page.goto("https://secure.indeed.com/account/login", wait_until="networkidle")
            _delay()
            try:
                page.fill("input[name='__email']", settings.indeed_email)
                page.click("button[type='submit']")
                page.wait_for_selector("input[name='__password']", timeout=5000)
                page.fill("input[name='__password']", settings.indeed_password)
                page.click("button[type='submit']")
                page.wait_for_load_state("networkidle")
                _delay(2, 3)
            except Exception:
                pass

        page.goto("https://my.indeed.com/applied", wait_until="networkidle")
        _delay(2, 3)

        cards = page.query_selector_all("[class*='applied-job']")
        platform_statuses: dict[str, str] = {}
        for card in cards:
            try:
                company_el = card.query_selector("[class*='companyName']")
                status_el = card.query_selector("[class*='applicationStatus']")
                if company_el and status_el:
                    company = company_el.inner_text().strip().lower()
                    raw = status_el.inner_text().strip().lower()
                    platform_statuses[company] = _normalise_indeed_status(raw)
            except Exception:
                continue

        for app in apps:
            company_key = app.get("company", "").lower()
            statuses[app["job_id"]] = platform_statuses.get(company_key, STATUS_APPLIED)

        browser.close()
    return statuses


def _check_naukri(apps: list[dict]) -> dict[str, str]:
    # Naukri status requires login; return applied as default for now
    return {app["job_id"]: STATUS_APPLIED for app in apps}


# ── Status normalisers ─────────────────────────────────────────────────────────

def _normalise_linkedin_status(raw: str) -> str:
    if any(w in raw for w in ("viewed", "seen")):
        return STATUS_VIEWED
    if any(w in raw for w in ("shortlist", "considering")):
        return STATUS_SHORTLISTED
    if any(w in raw for w in ("interview", "schedule")):
        return STATUS_INTERVIEW
    if any(w in raw for w in ("rejected", "not selected", "closed")):
        return STATUS_REJECTED
    return STATUS_APPLIED


def _normalise_indeed_status(raw: str) -> str:
    if "reviewed" in raw or "viewed" in raw:
        return STATUS_VIEWED
    if "shortlist" in raw:
        return STATUS_SHORTLISTED
    if "interview" in raw:
        return STATUS_INTERVIEW
    if "rejected" in raw or "declined" in raw:
        return STATUS_REJECTED
    return STATUS_APPLIED


def _login_linkedin(page: Page) -> None:
    page.goto("https://www.linkedin.com/login", wait_until="networkidle")
    _delay()
    page.fill("#username", settings.linkedin_email)
    _delay(0.5, 1.0)
    page.fill("#password", settings.linkedin_password)
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    time.sleep(3)


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
