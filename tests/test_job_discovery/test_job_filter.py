"""Unit tests for the job_filter node — pure functions, no network."""
from agents.job_discovery.workers.job_filter import run, _should_drop

# ── Helpers ────────────────────────────────────────────────────────────────────

def _jd(job_id, seniority="junior", remote=False):
    return {"job_id": job_id, "seniority_level": seniority, "remote_friendly": remote}

def _job(id_, title="AI Eng", company="Acme", location="Bangalore, India"):
    return {"id": id_, "title": title, "company": company, "location": location}

def _state(analyzed, discovered, filters):
    return {
        "analyzed_jds": analyzed,
        "discovered_jobs": discovered,
        "discovery_filters": filters,
        "logs": [],
    }


# ── Seniority tests ────────────────────────────────────────────────────────────

def test_seniority_blocks_senior_for_fresher():
    assert _should_drop(_jd("j1", "senior"), _job("j1"), {"max_seniority": "fresher"})

def test_seniority_blocks_lead_for_junior():
    assert _should_drop(_jd("j1", "lead"), _job("j1"), {"max_seniority": "junior"})

def test_seniority_passes_junior_for_junior():
    assert _should_drop(_jd("j1", "junior"), _job("j1"), {"max_seniority": "junior"}) is None

def test_seniority_unknown_always_passes():
    assert _should_drop(_jd("j1", "unknown"), _job("j1"), {"max_seniority": "fresher"}) is None

def test_no_seniority_filter_passes_all():
    assert _should_drop(_jd("j1", "lead"), _job("j1"), {}) is None


# ── Location tests ─────────────────────────────────────────────────────────────

def test_location_blocks_wrong_city():
    reason = _should_drop(
        _jd("j1"), _job("j1", location="Mumbai, India"),
        {"locations": ["Bangalore"], "remote_ok": True},
    )
    assert reason and "Mumbai" in reason

def test_location_passes_matching_city():
    assert _should_drop(
        _jd("j1"), _job("j1", location="Bangalore, India"),
        {"locations": ["Bangalore"], "remote_ok": True},
    ) is None

def test_location_passes_remote_job_when_remote_ok():
    assert _should_drop(
        _jd("j1", remote=True), _job("j1", location="San Francisco"),
        {"locations": ["Bangalore"], "remote_ok": True},
    ) is None

def test_location_blocks_remote_when_no_remote():
    reason = _should_drop(
        _jd("j1", remote=True), _job("j1", location="San Francisco"),
        {"locations": ["Bangalore"], "remote_ok": False},
    )
    assert reason is not None

def test_location_passes_unknown_location_leniently():
    assert _should_drop(
        _jd("j1"), _job("j1", location=""),
        {"locations": ["Bangalore"], "remote_ok": True},
    ) is None


# ── Full node run tests ────────────────────────────────────────────────────────

def test_run_filters_by_seniority_and_keeps_sync():
    jds = [_jd("j1", "junior"), _jd("j2", "senior"), _jd("j3", "mid")]
    jobs = [_job("j1"), _job("j2"), _job("j3")]
    result = run(_state(jds, jobs, {"max_seniority": "mid"}))

    kept_ids = {j["job_id"] for j in result["analyzed_jds"]}
    meta_ids  = {j["id"] for j in result["discovered_jobs"]}
    assert kept_ids == {"j1", "j3"}
    assert kept_ids == meta_ids       # discovered_jobs stays in sync

def test_run_no_filters_passes_everything():
    jds  = [_jd("j1", "lead"), _jd("j2", "senior")]
    jobs = [_job("j1"), _job("j2")]
    result = run(_state(jds, jobs, {}))
    assert len(result["analyzed_jds"]) == 2

def test_run_empty_input_is_safe():
    result = run(_state([], [], {"max_seniority": "junior"}))
    assert result["analyzed_jds"] == []
    assert result["discovered_jobs"] == []
