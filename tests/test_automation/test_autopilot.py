"""Unit tests for autopilot digest/dedupe logic — pure functions, no network."""
from datetime import datetime, timedelta, timezone

from automation.autopilot import (
    _split_new_jobs,
    build_compact_summary,
    build_digest,
    build_email_subject,
    seconds_until,
)
from skills.notify import markdown_to_email_html, truncate_for_telegram

JOBS = [
    {"job_id": "gh_1", "title": "AI Engineer", "company": "Acme", "platform": "Greenhouse",
     "relevance_score": 88, "priority": "high", "url": "https://x/1",
     "match_reasons": ["LangGraph experience", "Python depth"],
     "application_note": "Lead with the multi-agent project."},
    {"job_id": "lv_2", "title": "ML Engineer", "company": "Beta", "platform": "Lever",
     "relevance_score": 70, "priority": "medium", "url": "https://x/2"},
]


def test_split_new_jobs_partitions_and_stamps():
    seen = {"lv_2": "2026-06-01T00:00:00+00:00"}
    new, updated = _split_new_jobs(JOBS, seen)
    assert [j["job_id"] for j in new] == ["gh_1"]      # lv_2 already seen
    assert set(updated) == {"gh_1", "lv_2"}            # both stamps refreshed
    assert updated["lv_2"] > "2026-06-01"


def test_split_new_jobs_skips_idless_entries():
    new, seen = _split_new_jobs([{"title": "no id"}], {})
    assert new == [] and seen == {}


def test_digest_contains_scores_and_high_priority_flag():
    md = build_digest(JOBS, total_scored=25, role="AI Engineer", market="India")
    assert "**New since last run:** 2" in md
    assert "**High priority:** 1" in md
    assert "🔥 AI Engineer — Acme" in md
    assert "88/100" in md
    assert "Lead with the multi-agent project." in md


def test_digest_empty_day():
    md = build_digest([], total_scored=12, role="AI Engineer", market="India")
    assert "No new jobs today" in md


def test_compact_summary_caps_at_five_jobs():
    many = [dict(JOBS[0], job_id=f"j{i}") for i in range(9)]
    text = build_compact_summary(many, total_scored=30, role="AI Engineer")
    assert text.count("/100") == 5
    assert "9 new" in text


def test_email_subject_variants():
    assert "nothing new" in build_email_subject(0, 0)
    assert "1 new match (" in build_email_subject(1, 0)
    subject = build_email_subject(7, 2)
    assert "7 new matches" in subject and "2 high priority" in subject


def test_email_html_renders_digest_markdown():
    html = markdown_to_email_html(build_digest(JOBS, 25, "AI Engineer", "India"))
    assert "<h1>" in html and "<h2>" in html
    assert "AI Engineer — Acme" in html
    assert "<a href=\"https://x/1\">" in html or "https://x/1" in html


def test_telegram_truncation_keeps_whole_lines():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(200))
    out = truncate_for_telegram(text)
    assert len(out) <= 4096
    assert out.endswith("… (truncated)")
    # cut happens at a line boundary, not mid-line
    assert not out.rsplit("\n", 2)[-2].endswith("xx" + "…")


def test_seconds_until_always_future_and_under_24h():
    for at in ("00:00", "08:00", "23:59"):
        s = seconds_until(at)
        assert 0 < s <= 24 * 3600


def test_seconds_until_rolls_to_tomorrow():
    past = (datetime.now() - timedelta(minutes=5)).strftime("%H:%M")
    assert seconds_until(past) > 23 * 3600
