```markdown
# Job-Hunter 

> An end-to-end AI-powered job hunting system built on a hierarchical multi-agent architecture.
> From GitHub portfolio analysis to offer negotiation — fully orchestrated, human-in-the-loop.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)](https://langchain-ai.github.io/langgraph/)
[![Claude](https://img.shields.io/badge/Claude-Anthropic-blueviolet)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is this?

JobHunter is a sophisticated agentic AI system that handles every stage of the job search process:

1. **Audits your GitHub portfolio** and tells you exactly what to build or fix to attract recruiters for your target role
2. **Discovers and scores job listings** across LinkedIn, Indeed, and Naukri against your actual profile
3. **Tailors your resume and cover letter** per job, fills application forms, and waits for your approval before submitting
4. **Tracks all applications** — monitors status changes, drafts follow-ups, flags ghosted companies
5. **Evaluates job offers** — benchmarks CTC against market data, flags risky clauses, computes a counter-offer, and generates a full negotiation script

---

## Architecture

The system is built as a **hierarchical multi-agent pipeline** using LangGraph's stateful graph framework.

```
MASTER ORCHESTRATOR  (LangGraph StateGraph + MemorySaver)
│
├── GITHUB INTELLIGENCE LEAD
│   ├── Profile Auditor          → GitHub API → profile snapshot + score
│   ├── Project Depth Analyzer   → per-repo: README, stack, recency, completeness
│   ├── Trend Scout              → Claude → must-have skills for target role/niche
│   ├── Gap Analyzer             → profile vs. market → severity-rated gap report
│   └── Improvement Planner      → prioritised action plan saved to outputs/
│
├── JOB DISCOVERY LEAD
│   ├── LinkedIn Scraper         → Playwright → up to 25 listings
│   ├── Indeed Scraper           → Playwright → up to 25 listings
│   ├── Naukri Scraper           → Playwright → up to 25 listings
│   ├── JD Analyzer              → Claude → skills, seniority, red flags per JD
│   └── Relevance Scorer         → Claude → 0-100 match score vs. your profile
│
├── APPLICATION ENGINE LEAD
│   ├── Resume Tailor            → Claude → JD-mirrored resume per job
│   ├── Cover Letter Writer      → Claude → role + company-specific letter
│   ├── Form Filler              → Playwright → fills fields, screenshots form
│   ├── Human Approval Gate      → LangGraph interrupt() → YOU review before submit
│   └── Submission Executor      → Playwright → clicks Submit only after approval
│
├── STATUS TRACKER LEAD
│   ├── Application Monitor      → Playwright → polls platforms for status changes
│   ├── Follow-up Scheduler      → Claude → drafts follow-up emails (7-day threshold)
│   ├── Ghosted Detector         → flags applications silent for 21+ days
│   └── Pipeline Reporter        → weekly markdown digest → outputs/reports/
│
└── OFFER INTELLIGENCE LEAD
    ├── Offer Parser             → Claude → extracts every CTC component
    ├── Market Benchmarker       → AmbitionBox scrape + Claude → P25/P50/P75/P90
    ├── Clause Risk Analyzer     → Claude → NCA, IP, clawback, notice period risks
    ├── Counter-offer Calculator → Claude → ask number + walk-away floor + justification
    ├── Negotiation Script Gen   → Claude → email + phone + pushback scripts
    └── Response Coach           → Claude → coaches on employer's counter-response
```

### State Flow

```
User sets target role + market
        ↓
[GitHub Intelligence]  →  audit + improvement plan
        ↓
[Job Discovery]        →  scored, ranked job list
        ↓
[Application Engine]   →  tailored docs + HUMAN APPROVAL + submission
        ↓
[Status Tracker]       →  continuous monitoring (background)
        ↓
[Offer Intelligence]   →  triggered when offer arrives
```

Global state is a single `TypedDict` that flows through the entire graph. Each Lead Agent reads and writes only its slice.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Human-in-the-loop before every submission** | Avoids ToS violations on LinkedIn/Indeed; defensible design choice |
| **LangGraph `interrupt()` for approval gate** | Graph pauses mid-execution, resumes on human input — not a hack, it's idiomatic |
| **One `GlobalState` TypedDict** | All subgraphs share the same schema; Master Orchestrator routes on `current_phase` |
| **Separate skills layer** | Workers don't import Playwright or GitHub API directly — they go through `skills/` |
| **Session persistence via JSON** | Thread IDs map to `memory/sessions/<id>.json` — resume any session across restarts |

---

## Agent Types Demonstrated

| Agent Type | Where |
|---|---|
| Reactive | Form Filler, Submission Executor |
| Model-based | Status Tracker, Pipeline Reporter |
| Goal-based | Resume Tailor, Application Engine |
| Utility-based | Relevance Scorer, Clause Risk Analyzer |
| Learning | Improvement Planner (learns from which apps get responses) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM | [Claude (Anthropic)](https://anthropic.com) via `anthropic` SDK |
| Browser automation | [Playwright](https://playwright.dev/) |
| GitHub data | [PyGithub](https://pygithub.readthedocs.io/) |
| HTTP client | [httpx](https://www.python-httpx.org/) |
| Config | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| CLI output | [rich](https://rich.readthedocs.io/) |
| Language | Python 3.11+ |

---

## Project Structure

```
JobHunter/
├── main.py                          # CLI entry point (6 subcommands)
├── pyproject.toml
├── .env.example
│
├── state/
│   └── global_state.py              # GlobalState TypedDict + SystemPhase enum
│
├── orchestrator/
│   └── master.py                    # Master Orchestrator — routing + compile + run helpers
│
├── agents/
│   ├── github_intelligence/
│   │   ├── lead.py
│   │   └── workers/                 # profile_auditor, project_depth_analyzer,
│   │       ...                      # trend_scout, gap_analyzer, improvement_planner
│   ├── job_discovery/
│   │   ├── lead.py
│   │   └── workers/
│   │       ├── platform_scrapers/   # linkedin, indeed, naukri
│   │       ├── jd_analyzer.py
│   │       └── relevance_scorer.py
│   ├── application_engine/
│   │   ├── lead.py
│   │   └── workers/                 # resume_tailor, cover_letter_writer,
│   │       ...                      # form_filler, human_approval_gate, submission_executor
│   ├── status_tracker/
│   │   ├── lead.py
│   │   └── workers/                 # application_monitor, followup_scheduler,
│   │       ...                      # ghosted_detector, pipeline_reporter
│   └── offer_intelligence/
│       ├── lead.py
│       └── workers/                 # offer_parser, market_benchmarker, clause_risk_analyzer,
│           ...                      # counteroffer_calculator, negotiation_script_gen, response_coach
│
├── skills/
│   ├── llm.py                       # Claude API wrapper (call + call_json)
│   ├── github_tools.py              # GitHub API helpers
│   ├── browser_tools.py             # Playwright helpers
│   ├── web_search_tools.py          # HTTP + search helpers
│   └── file_tools.py                # Output file management
│
├── config/
│   ├── settings.py                  # Pydantic settings (reads .env)
│   └── user_profile.py             # Loads user_data/profile.json
│
├── user_data/
│   └── profile.example.json         # Template: fill and rename to profile.json
│
└── outputs/                         # All generated files (gitignored)
    ├── resumes/
    ├── cover_letters/
    ├── negotiation/
    ├── reports/
    └── github_intelligence/
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/rishab-br/job-hunter.git
cd job-hunter

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -e .
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and GITHUB_TOKEN at minimum
```

### 3. Set up your profile

```bash
cp user_data/profile.example.json user_data/profile.json
# Edit profile.json with your real experience, education, and skills
```

---

## Usage

```bash
# Analyze your GitHub portfolio for a target role
python main.py github --username your_github_handle --role "AI Engineer" --niche "MLOps" --market "India"

# Run the full pipeline end-to-end
python main.py full --username your_github_handle --role "AI Engineer" --niche "MLOps" --market "India"

# Check application statuses (uses saved session)
python main.py status --thread-id <uuid>

# Evaluate a job offer
python main.py offer --thread-id <uuid> --company "TechCorp" --role "ML Engineer" --offer-file offer.txt

# Resume after the human-approval gate
python main.py resume --thread-id <uuid> --approve   # or --skip

# Get coaching on employer's counter-offer response
python main.py respond --thread-id <uuid> --offer-id offer_abc12345 --response-file reply.txt
```

---

## Outputs

Every run produces files in `outputs/` (gitignored — contains personal data):

| Path | Content |
|---|---|
| `outputs/github_intelligence/improvement_plan_<date>.md` | Prioritised portfolio improvement plan |
| `outputs/resumes/<company>_<role>_resume.md` | Tailored resume per application |
| `outputs/cover_letters/<company>_<role>_cover_letter.md` | Role-specific cover letter |
| `outputs/form_screenshots/<company>_<job_id>.png` | Form preview before submission |
| `outputs/negotiation/<company>_negotiation_script.md` | Full negotiation playbook |
| `outputs/negotiation/<company>_response_coaching_<ts>.md` | Coaching on employer's response |
| `outputs/reports/pipeline_<date>.md` | Weekly application pipeline digest |

---

## Roadmap

- [ ] Multi-LLM routing (Groq + Gemini Flash + Claude by task complexity)
- [ ] FastAPI backend to expose orchestrator as REST endpoints
- [ ] Next.js dashboard with real-time pipeline visualization
- [ ] Supabase integration (replace JSON session files)
- [ ] Interview Prep Lead Agent (generates Q&A from JD + your profile)
- [ ] Gmail trigger for automatic offer/status parsing
- [ ] Semantic job search with pgvector embeddings

---

## Disclaimer

This tool is built for personal job search use. Automated interactions with LinkedIn, Indeed, and Naukri may conflict with their Terms of Service. The system is intentionally designed with a **human approval gate before every form submission** — no application is submitted without explicit user confirmation.

---

## Author

Built by [Rishab](https://github.com/rishab-br) as a portfolio project demonstrating hierarchical multi-agent orchestration, stateful LangGraph workflows, and human-in-the-loop AI system design.
```

