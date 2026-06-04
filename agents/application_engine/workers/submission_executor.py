import time
import random
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

from config import settings, user_profile
from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Fires ONLY for applications that passed human_approval_gate.
    Re-opens the browser, navigates to the job, re-fills, and clicks Submit.
    Records outcome in state.applications.
    """
    logs = list(state.get("logs") or [])
    confirmed = state.get("pending_approvals") or []
    existing_applications = list(state.get("applications") or [])

    if not confirmed:
        logs.append("[submission_executor] No approved applications to submit.")
        return {**state, "logs": logs}

    logs.append(f"[submission_executor] Submitting {len(confirmed)} approved application(s)...")
    profile = user_profile.load()
    new_applications: list[dict] = []

    for item in confirmed:
        platform = item.get("platform", "")
        logs.append(f"[submission_executor] Submitting to {item['company']} ({platform})...")

        result = _submit(item, profile, platform)
        result["job_title"] = item["job_title"]
        result["company"] = item["company"]
        result["platform"] = platform
        result["job_url"] = item["job_url"]
        result["resume_path"] = item.get("resume_path")
        result["cover_letter_path"] = item.get("cover_letter_path")
        result["submitted_at"] = datetime.now(timezone.utc).isoformat()
        new_applications.append(result)

        logs.append(
            f"[submission_executor] {item['company']}: {result['status']}"
        )

    return {
        **state,
        "applications": existing_applications + new_applications,
        "pending_approvals": [],
        "logs": logs,
    }


# ── Submission handlers ────────────────────────────────────────────────────────

def _submit(item: dict, profile: dict, platform: str) -> dict:
    try:
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
                status = _submit_linkedin(page, item, profile)
            elif p_lower == "indeed":
                status = _submit_indeed(page, item, profile)
            elif p_lower == "naukri":
                status = _submit_naukri(page, item, profile)
            else:
                status = "platform_not_supported"

            browser.close()
        return {"job_id": item.get("job_id"), "status": status}

    except Exception as exc:
        return {"job_id": item.get("job_id"), "status": "failed", "error": str(exc)}


def _submit_linkedin(page: Page, item: dict, profile: dict) -> str:
    personal = profile.get("personal", {})
    page.goto(item["job_url"], wait_until="networkidle")
    _delay(2, 3)

    try:
        apply_btn = page.query_selector("button.jobs-apply-button")
        if not apply_btn:
            return "apply_button_not_found"
        apply_btn.click()
        _delay(2, 3)
    except Exception:
        return "apply_button_error"

    # Step through Easy Apply modal pages until Submit is reached
    for _ in range(8):
        # Upload resume if file input is visible
        resume_input = page.query_selector("input[type='file']")
        if resume_input and item.get("resume_path") and Path(item["resume_path"]).exists():
            resume_input.set_input_files(item["resume_path"])
            _delay(1, 2)

        # Fill any visible text inputs
        _fill_visible_text_inputs(page, personal)

        # Check for Submit button first
        submit_btn = page.query_selector("button[aria-label='Submit application']")
        if submit_btn:
            submit_btn.click()
            page.wait_for_load_state("networkidle")
            return "submitted"

        # Check for CAPTCHA
        if page.query_selector("iframe[title*='security']"):
            return "captcha_blocked"

        # Next step
        next_btn = page.query_selector("button[aria-label='Continue to next step']")
        if not next_btn:
            next_btn = page.query_selector("button[aria-label='Review your application']")
        if next_btn:
            next_btn.click()
            _delay(1, 2)
        else:
            break

    return "submit_button_not_reached"


def _submit_indeed(page: Page, item: dict, profile: dict) -> str:
    personal = profile.get("personal", {})
    page.goto(item["job_url"], wait_until="networkidle")
    _delay(2, 3)

    try:
        apply_btn = page.query_selector("button#indeedApplyButton")
        if not apply_btn:
            apply_btn = page.query_selector("[class*='ia-IndeedApply']")
        if not apply_btn:
            return "apply_button_not_found"
        apply_btn.click()
        _delay(2, 3)
    except Exception:
        return "apply_button_error"

    for _ in range(6):
        _fill_visible_text_inputs(page, personal)

        if page.query_selector("iframe[src*='captcha']"):
            return "captcha_blocked"

        submit_btn = page.query_selector("button[class*='ia-continueButton']")
        if submit_btn:
            label = submit_btn.inner_text().strip().lower()
            submit_btn.click()
            _delay(1, 2)
            if "submit" in label:
                return "submitted"
        else:
            break

    return "submit_button_not_reached"


def _submit_naukri(page: Page, item: dict, profile: dict) -> str:
    personal = profile.get("personal", {})
    page.goto(item["job_url"], wait_until="networkidle")
    _delay(2, 3)

    try:
        apply_btn = page.query_selector("button.apply-button")
        if not apply_btn:
            apply_btn = page.query_selector("[class*='apply-btn']")
        if not apply_btn:
            return "apply_button_not_found"
        apply_btn.click()
        _delay(2, 3)
    except Exception:
        return "apply_button_error"

    _fill_visible_text_inputs(page, personal)

    submit_btn = page.query_selector("button[class*='submit']")
    if submit_btn:
        submit_btn.click()
        page.wait_for_load_state("networkidle")
        return "submitted"

    return "submit_button_not_reached"


def _fill_visible_text_inputs(page: Page, personal: dict) -> None:
    field_hints = {
        "name": personal.get("full_name", ""),
        "email": personal.get("email", ""),
        "phone": personal.get("phone", ""),
        "mobile": personal.get("phone", ""),
    }
    inputs = page.query_selector_all("input[type='text'], input[type='email'], input[type='tel']")
    for inp in inputs:
        try:
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            aria_label = (inp.get_attribute("aria-label") or "").lower()
            hint = placeholder or aria_label
            for key, value in field_hints.items():
                if key in hint and value:
                    current = inp.input_value()
                    if not current:
                        inp.fill(value)
                    break
            _delay(0.2, 0.5)
        except Exception:
            continue


def _delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))
