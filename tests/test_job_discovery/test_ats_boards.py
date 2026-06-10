"""Unit tests for Greenhouse/Lever board parsing — pure functions, no network."""
from agents.job_discovery.workers.platform_scrapers.ats_boards import (
    _extract_board_tokens,
    _filter_by_market,
    _parse_greenhouse_jobs,
    _parse_lever_postings,
    _title_matches,
)

GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 4567890,
            "title": "Senior AI Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/4567890",
            "location": {"name": "Bengaluru, India"},
            "content": "&lt;p&gt;Build &amp;amp; ship agentic ML pipelines.&lt;/p&gt;",
            "updated_at": "2026-06-01T00:00:00-04:00",
        },
        {
            "id": 111,
            "title": "Missing URL — should be skipped",
            "absolute_url": None,
        },
    ]
}

LEVER_RESPONSE = [
    {
        "id": "ab12cd34-5678",
        "text": "Machine Learning Engineer",
        "hostedUrl": "https://jobs.lever.co/acme/ab12cd34-5678",
        "applyUrl": "https://jobs.lever.co/acme/ab12cd34-5678/apply",
        "categories": {"location": "Bengaluru", "commitment": "Full-time"},
        "workplaceType": "remote",
        "descriptionPlain": "Train and deploy models at scale.",
    },
    {"id": "no-url", "text": "Broken posting"},
]


def test_greenhouse_parser_extracts_and_unescapes():
    jobs = _parse_greenhouse_jobs(GREENHOUSE_RESPONSE, "Acme Corp")
    assert len(jobs) == 1  # broken posting skipped
    job = jobs[0]
    assert job["id"] == "gh_4567890"
    assert job["platform"] == "Greenhouse"
    assert job["company"] == "Acme Corp"
    assert job["location"] == "Bengaluru, India"
    # double-escaped HTML content fully cleaned
    assert job["description"] == "Build & ship agentic ML pipelines."


def test_lever_parser_extracts_apply_url_and_remote():
    jobs = _parse_lever_postings(LEVER_RESPONSE, "acme")
    assert len(jobs) == 1
    job = jobs[0]
    assert job["id"] == "lv_ab12cd34-5678"
    assert job["platform"] == "Lever"
    assert job["apply_url"].endswith("/apply")
    assert "Remote" in job["location"]      # workplaceType surfaced
    assert job["job_type"] == "Full-time"


def test_board_token_extraction_from_ddg_html():
    html = (
        '<a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fboards.greenhouse.io%2Fanthropic%2Fjobs%2F123">x</a>'
        '<a href="https://jobs.lever.co/mistral/abc-def">y</a>'
        '<a href="https://job-boards.greenhouse.io/openai">z</a>'
        '<a href="https://boards.greenhouse.io/embed/job_board?for=acme">junk</a>'
    )
    gh, lv = _extract_board_tokens(html)
    assert "anthropic" in gh
    assert "openai" in gh
    assert "embed" not in gh
    assert lv == ["mistral"]


def test_title_matching_is_token_based():
    assert _title_matches("Senior AI Engineer, Platform", "AI Engineer")
    assert _title_matches("Machine Learning Engineer", "ML Engineer")  # "engineer" token
    assert not _title_matches("Account Executive", "AI Engineer")
    assert _title_matches("Anything", "")  # empty role matches everything


def test_market_filter_keeps_local_and_remote_but_never_empties():
    jobs = [
        {"title": "A", "location": "Bengaluru, India"},
        {"title": "B", "location": "San Francisco (Remote)"},
        {"title": "C", "location": "London"},
    ]
    out = _filter_by_market(jobs, "India")
    assert {j["title"] for j in out} == {"A", "B"}
    # remote roles match any market
    out_remote = _filter_by_market(jobs, "Mars")
    assert {j["title"] for j in out_remote} == {"B"}
    # if nothing matches at all, the filter falls back to everything
    onsite_only = [{"title": "C", "location": "London"}, {"title": "D", "location": "Berlin"}]
    assert len(_filter_by_market(onsite_only, "Mars")) == 2
