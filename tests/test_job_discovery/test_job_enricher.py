"""Unit tests for job-enricher HTML extraction — pure functions, no network."""
from agents.job_discovery.workers.job_enricher import (
    MAX_DESC_CHARS,
    _clean_to_text,
    _extract_description,
)

LINKEDIN_JOB_PAGE = """
<html><head><script>var noise = 1;</script><style>.x{color:red}</style></head>
<body>
<nav>Jobs | People | Learning</nav>
<div class="show-more-less-html__markup">
  <p>We are hiring a <b>Senior ML Engineer</b> to build agentic pipelines.</p>
  <ul><li>5+ years Python &amp; PyTorch</li><li>LangGraph experience</li></ul>
</div>
<footer>© LinkedIn</footer>
</body></html>
"""


def test_linkedin_selector_extraction():
    desc = _extract_description(LINKEDIN_JOB_PAGE, "LinkedIn")
    assert "Senior ML Engineer" in desc
    assert "Python & PyTorch" in desc          # entities unescaped
    assert "var noise" not in desc             # script stripped
    assert "Jobs | People" not in desc         # nav stripped


def test_keyword_anchor_fallback_for_unknown_platform():
    filler = "word " * 200
    page = f"<html><body><p>About us blah blah.</p><p>Responsibilities: build agents. {filler}</p></body></html>"
    desc = _extract_description(page, "UnknownBoard")
    # extraction should anchor near the "responsibilities" keyword, not page start
    assert "Responsibilities" in desc
    assert desc.index("Responsibilities") < 100


def test_description_truncated_to_budget():
    huge = '<div class="show-more-less-html__markup">' + ("x" * (MAX_DESC_CHARS * 2)) + "</div>"
    desc = _extract_description(huge, "LinkedIn")
    assert len(desc) <= MAX_DESC_CHARS


def test_clean_to_text_unescapes_and_normalises():
    out = _clean_to_text("<p>A &amp; B&#x27;s   <b>team</b></p>")
    assert out == "A & B's team"
