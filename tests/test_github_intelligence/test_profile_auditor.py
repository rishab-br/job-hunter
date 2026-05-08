from state import initial_state
from agents.github_intelligence.workers.profile_auditor import run


def test_profile_auditor_returns_state():
    state = initial_state(
        github_username="testuser",
        target_role="AI Engineer",
        target_market="India",
        target_niche="MLOps",
    )
    result = run(state)
    assert "github_audit" in result
