"""Unit tests for the LinkedIn guest-API HTML parser — pure functions, no network."""
from agents.job_discovery.workers.platform_scrapers.linkedin import (
    _parse_card,
    _parse_listings,
    _text_between,
)

# Mimics a real <li> fragment from the guest jobs API (regional subdomain,
# tracking params, HTML entities — all the things that bit us in production).
CARD = """
<div class="base-card">
  <a class="base-card__full-link"
     href="https://in.linkedin.com/jobs/view/python-developer-at-acme-corp-4397658289?position=1&amp;pageNum=0&amp;refId=abc&amp;trackingId=xyz">
    Python Developer
  </a>
  <h3 class="base-search-card__title">
    Python Developer &amp; ML Engineer
  </h3>
  <h4 class="base-search-card__subtitle">
    <a href="https://in.linkedin.com/company/acme">Acme &amp; Sons</a>
  </h4>
  <span class="job-search-card__location">Bengaluru, Karnataka, India</span>
</div>
"""


def test_parse_card_extracts_all_fields():
    job = _parse_card(CARD)
    assert job is not None
    assert job["title"] == "Python Developer & ML Engineer"
    assert job["company"] == "Acme & Sons"
    assert job["location"] == "Bengaluru, Karnataka, India"
    assert job["platform"] == "LinkedIn"
    assert job["description"] == ""  # guest API has no JD — enricher fills it


def test_parse_card_strips_tracking_params_from_url():
    job = _parse_card(CARD)
    assert "?" not in job["url"]
    assert "trackingId" not in job["url"]
    assert job["url"].endswith("python-developer-at-acme-corp-4397658289")


def test_parse_card_handles_regional_subdomains():
    job = _parse_card(CARD)
    assert job["url"].startswith("https://in.linkedin.com/jobs/view/")


def test_parse_card_derives_stable_numeric_job_id():
    job = _parse_card(CARD)
    assert job["id"] == "li_4397658289"


def test_parse_card_rejects_card_without_url():
    assert _parse_card("<h3 class='base-search-card__title'>No link</h3>") is None


def test_parse_card_rejects_card_without_title():
    card = '<a href="https://www.linkedin.com/jobs/view/role-1234567890">x</a>'
    assert _parse_card(card) is None


def test_parse_listings_splits_li_fragments():
    html = f"<li>{CARD}</li><li>{CARD}</li><li>broken fragment</li>"
    jobs = _parse_listings(html)
    assert len(jobs) == 2  # broken fragment silently skipped


def test_text_between_unescapes_entities_and_strips_tags():
    html = '<h3 class="base-search-card__title"><b>C&#x2B;&#x2B; &amp; Rust</b> Dev</h3>'
    out = _text_between(html, r"base-search-card__title[^>]*>", "</h3>")
    assert out == "C++ & Rust Dev"
