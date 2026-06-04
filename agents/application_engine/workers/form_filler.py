import time
import random
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

from config import user_profile
from skills import file_tools
from state import GlobalState

MIN_RELEVANCE_SCORE = 65


def run(state: GlobalState) -> GlobalState:
    logs = list(state.get("logs") or [])
    scored_jobs = state.get("scored_jobs") or []
    pending = list(state.get("pending_approvals") or [])

    target_jobs = [
        j for j in scored_jobs
        if j.get("relevance_score", 0) >= MIN_RELEVANCE_SCORE
        and j.get("resume_path")
        and j.get("cover_letter_path")
    ]

    if not target_jobs:
        logs.append("[form_filler] No jobs ready for form filling — skipping.")
        return {**state, "logs": logs}

    logs.append(f"[form_filler] Preparing application forms for {len(target_jobs)} job(s)...")
    profile = user_profile.load()

    for job in target_jobs:
        platform = job.get("platform", "")
        try:
            result = _fill_form(job, profile, platform)
            pending.append(result)
            logs.append(
                f"[form_filler] Form prepared for {job.get('company')} — {job.get('title')} "
                f"[screenshot: {result.get('form_screenshot_path')}]"
            )
        except Exception as exc:
            logs.append(f"[form_filler] Failed for {job.get('company')}: {exc}")

    logs.append(f"[form_filler] {len(pending)} applications queued for human approval.")
    return {
        **state,
        "pending_approvals": pending,
        "logs": logs,
    }


# ── Platform-specific fillers ──────────────────────────────────────────────────

def _fill_form(job: dict, profile: dict, platform: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        p_lower = platform.lower()
        if p_lower == "linkedin":
            filled_fields = _fill_linkedin(page, job, profile)
        elif p_lower == "indeed":
            filled_fields = _fill_indeed(page, job, profile)
        elif p_lower == "naukri":
            filled_fields = _fill_naukri(page, job, profile)
        else:
            filled_fields = {"note": "Platform not supported for auto-fill"}

        # Screenshot the filled form
        screenshot_dir = Path("outputs/form_screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        company_slug = "".join(c if c.isalnum() else "_" for c in job.get("company", "company"))[:20]
        screenshot_path = str(screenshot_dir / f"{company_slug}_{job.get('job_id', 'job')}.png")
        try:
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            screenshot_path = None

        browser.close()

    return {
        "job_id": job.get("job_id") or job.get("id"),
        "job_title": job.get("title"),
        "company": job.get("company"),
        "platform": platform,
        "job_url": job.get("url"),
        "resume_path": job.get("resume_path"),
        "cover_letter_path": job.get("cover_letter_path"),
        "cover_letter_content": job.get("cover_letter_content", ""),
        "form_screenshot_path": screenshot_path,
        "filled_fields": filled_fields,
        "approved": None,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


def _fill_linkedin(page: Page, job: dict, profile: dict) -> dict:
    personal = profile.get("personal", {})
    page.goto(job["url"], wait_until="networkidle")
    _delay(2, 3)

    # Click Easy Apply button
    try:
        easy_apply_btn = page.query_selector("button.jobs-apply-button")
        if easy_apply_btn:
            easy_apply_btn.click()
            _delay(1, 2)
    except Exception:
        pass

    filled: dict = {}

    # Contact info fields
    field_map = {
        "input[id*='firstName']": personal.get("full_name", "").split()[0] if personal.get("full_name") else "",
        "input[id*='lastName']": personal.get("full_name", "").split()[-1] if personal.get("full_name") else "",
        "input[id*='phoneNumber']": personal.get("phone", ""),
        "input[id*='city']": personal.get("location", ""),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            el = page.query_selector(selector)
            if el:
                el.triple_click()
                el.type(value)
                filled[selector] = value
                _delay(0.3, 0.7)
        except Exception:
            pass

    return filled


def _fill_indeed(page: Page, job: dict, profile: dict) -> dict:
    personal = profile.get("personal", {})
    page.goto(job["url"], wait_until="networkidle")
    _delay(2, 3)

    try:
        apply_btn = page.query_selector("button#indeedApplyButton")
        if not apply_btn:
            apply_btn = page.query_selector("[class*='ia-IndeedApply']")
        if apply_btn:
            apply_btn.click()
            _delay(2, 3)
    except Exception:
        pass

    filled: dict = {}

    field_map = {
        "input[name='applicant.name']": personal.get("full_name", ""),
        "input[name='applicant.email']": personal.get("email", ""),
        "input[name='applicant.phoneNumber']": personal.get("phone", ""),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            el = page.query_selector(selector)
            if el:
                el.fill(value)
                filled[selector] = value
                _delay(0.3, 0.7)
        except Exception:
            pass

    return filled


def _fill_naukri(page: Page, job: dict, profile: dict) -> dict:
    personal = profile.get("personal", {})
    page.goto(job["url"], wait_until="networkidle")
    _delay(2, 3)

    try:
        apply_btn = page.query_selector("button.apply-button")
        if not apply_btn:
            apply_btn = page.query_selector("[class*='apply-btn']")
        if apply_btn:
            apply_btn.click()
            _delay(2, 3)
    except Exception:
        pass

    filled: dict = {}

    field_map = {
        "input[placeholder*='Name']": personal.get("full_name", ""),
        "input[placeholder*='Email']": personal.get("email", ""),
        "input[placeholder*='Mobile']": personal.get("phone", ""),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            el = page.query_selector(selector)
            if el:
                el.fill(value)
                filled[selector] = value
                _delay(0.3, 0.7)
        except Exception:
            pass

    return filled


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
