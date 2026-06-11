"""Notification delivery for autonomous runs.

Telegram is the primary channel (zero infra: one bot token + chat id).
Every digest is also written to outputs/digests/ regardless, so the run
is never lost if no channel is configured.
"""
import logging

import httpx

from config import settings

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_TELEGRAM_LIMIT = 4096


def telegram_configured() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


def send_telegram(text: str) -> bool:
    """Send a plain-text message to the configured Telegram chat.
    Returns True on success. Never raises — autopilot must survive notify failures."""
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
