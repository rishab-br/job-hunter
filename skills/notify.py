"""Notification delivery for autonomous runs.

Email (Gmail SMTP + App Password) is the primary channel; Telegram is an
optional secondary. Every digest is also written to outputs/digests/
regardless, so a run is never lost if no channel is configured.

All send functions return bool and never raise — autopilot must survive
notify failures.
"""
import logging
import smtplib
from email.message import EmailMessage

import httpx

from config import settings

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_TELEGRAM_LIMIT = 4096

_EMAIL_CSS = """
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a1a; line-height: 1.5; }
  h1 { font-size: 20px; color: #0f172a; }
  h2 { font-size: 16px; color: #1e3a8a; border-bottom: 2px solid #2563eb; padding-bottom: 4px; }
  h3 { font-size: 14px; margin-bottom: 2px; }
  a { color: #2563eb; }
  li { margin: 2px 0; }
"""


# ── Channel dispatch ───────────────────────────────────────────────────────────

def send_digest(subject: str, markdown_body: str, compact_text: str) -> dict[str, bool]:
    """Deliver a digest to every configured channel.
    Returns {channel: delivered} — empty dict when nothing is configured."""
    delivered: dict[str, bool] = {}
    if email_configured():
        delivered["email"] = send_email(subject, markdown_body)
    if telegram_configured():
        delivered["telegram"] = send_telegram(compact_text)
    return delivered


def send_alert(text: str) -> None:
    """Short plain-text alert (e.g. autopilot run failure) to all channels."""
    if email_configured():
        send_email("⚠️ JobHunter autopilot alert", text)
    if telegram_configured():
        send_telegram(text)


# ── Email (Gmail SMTP) ─────────────────────────────────────────────────────────

def email_configured() -> bool:
    return bool(settings.smtp_username and settings.smtp_password)


def send_email(subject: str, markdown_body: str) -> bool:
    """Send a digest email — markdown as the plain-text part, rendered HTML
    as the rich alternative. Returns True on success."""
    to_addr = settings.digest_email_to or settings.smtp_username
    try:
        msg = EmailMessage()
        msg["From"] = settings.smtp_username
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(markdown_body)
        msg.add_alternative(markdown_to_email_html(markdown_body), subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception as exc:
        log.warning(f"Email send failed: {exc}")
        return False


def markdown_to_email_html(markdown_body: str) -> str:
    import markdown as md_lib

    body = md_lib.markdown(markdown_body, extensions=["extra", "sane_lists"])
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{_EMAIL_CSS}</style></head><body>{body}</body></html>"
    )


# ── Telegram (optional secondary) ──────────────────────────────────────────────

def telegram_configured() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


def send_telegram(text: str) -> bool:
    if not telegram_configured():
        return False
    try:
        resp = httpx.post(
            TELEGRAM_API.format(token=settings.telegram_bot_token),
            json={
                "chat_id": settings.telegram_chat_id,
                "text": truncate_for_telegram(text),
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        ok = resp.status_code == 200 and resp.json().get("ok", False)
        if not ok:
            log.warning(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
        return ok
    except Exception as exc:
        log.warning(f"Telegram send error: {exc}")
        return False


def truncate_for_telegram(text: str, limit: int = _TELEGRAM_LIMIT) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 20].rsplit("\n", 1)[0]
    return cut + "\n… (truncated)"
