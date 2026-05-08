```markdown
# JobHunter 

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

### Master Orchestrator
Routes between all Lead Agents using a single `GlobalState` TypedDict and `current_phase` enum. Compiled with `MemorySaver` checkpointing for interrupt/resume support.

---

### GitHub Intelligence Lead
| Worker | What it does |
|---|---|
| Profile Auditor | GitHub API → profile snapshot, bio quality, activity score |
| Project Depth Analyzer | Per-repo: README quality, stack, recency, completeness score |
| Trend Scout | Claude → must-have skills and hot project types for target role/niche |
| Gap Analyzer | Profile vs. market trends → severity-rated gap report |
| Improvement Planner | Prioritised action plan → saved to `outputs/github_intelligence/` |

---

### Job Discovery Lead
| Worker | What it does |
|---|---|
| LinkedIn Scraper | Playwright → login → search → extract up to 25 listings with full JD |
| Indeed Scraper | Playwright → search (no login required) → paginate → 25 listings |
| Naukri Scraper | Playwright → role+location URL → open each job → 25 listings |
| JD Analyzer | Claude → extracts skills, seniority, red flags, company signals per JD |
| Relevance Scorer | Claude → 0–100 match score against your profile, ranked |

---

### Application Engine Lead
| Worker | What it does |
|---|---|
| Resume Tailor | Claude → JD-mirrored resume per job → `outputs/resumes/` |
| Cover Letter Writer | Claude → role + company-specific letter → `outputs/cover_letters/` |
| Form Filler | Playwright → fills all fields, takes screenshot — does NOT submit |
| **Human Approval Gate** | **LangGraph `interrupt()` — YOU review resume + letter + screenshot before anything is submitted** |
| Submission Executor | Playwright → clicks Submit only after explicit human approval |

---

### Status Tracker Lead
| Worker | What it does |
|---|---|
| Application Monitor | Playwright → polls LinkedIn/Indeed for status changes on submitted apps |
| Follow-up Scheduler | Claude → drafts follow-up emails for apps silent 7+ days |
| Ghosted Detector | Flags applications with no movement after 21 days |
| Pipeline Reporter | Weekly markdown digest → `outputs/reports/pipeline_<date>.md` |

---

### Offer Intelligence Lead
| Worker | What it does |
|---|---|
| Offer Parser | Claude → extracts every CTC component from the offer letter |
| Market Benchmarker | AmbitionBox scrape + Claude → P25/P50/P75/P90 for role/market |
| Clause Risk Analyzer | Claude → NCA, IP assignment, clawback, notice period risk ratings |
| Counter-offer Calculator | Claude → specific ask number + walk-away floor + justification points |
| Negotiation Script Gen | Claude → email + phone + pushback scripts → `outputs/negotiation/` |
| Response Coach | Claude → analyzes employer's reply, recommends accept/counter/decline |

---

### State Flow

```
User sets target role + market
         │
         ▼
GitHub Intelligence  →  portfolio audit + improvement plan
         │
         ▼
Job Discovery        →  scored, ranked job list
         │
         ▼
Application Engine   →  tailored docs → HUMAN APPROVAL → submission
         │
         ▼
Status Tracker       →  continuous monitoring (runs periodically)
         │
         ▼
Offer Intelligence   →  triggered when an offer arrives
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Human-in-the-loop before every submission | Avoids ToS issues with job platforms; deliberate design choice |
| LangGraph `interrupt()` for the approval gate | Graph pauses mid-execution and resumes on human input — not a workaround, it's idiomatic LangGraph |
| Single `GlobalState` TypedDict | All subgraphs share the same schema; the Master Orchestrator routes on `current_phase` |
| Dedicated skills layer | Workers never import Playwright or GitHub API directly — all external calls go through `skills/` |
| JSON session persistence | Thread IDs map to `memory/sessions/<id>.json` — resume any session across restarts |

---

## Agent Types Demonstrated

| Agent Type | Where in the system |
|---|---|
| Reactive | Form Filler, Submission Executor |
| Model-based | Status Tracker, Pipeline Reporter |
| Goal-based | Resume Tailor, Application Engine |
| Utility-based | Relevance Scorer, Clause Risk Analyzer |
| Learning | Improvement Planner (learns from which applications get responses) |

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
├── state/
│   └── global_state.py              # GlobalState TypedDict + SystemPhase enum
├── orchestrator/
│   └── master.py                    # Master Orchestrator — routing, compile, run helpers
├── agents/
│   ├── github_intelligence/lead.py + workers/
│   ├── job_discovery/lead.py + workers/platform_scrapers/
│   ├── application_engine/lead.py + workers/
│   ├── status_tracker/lead.py + workers/
│   └── offer_intelligence/lead.py + workers/
├── skills/
│   ├── llm.py                       # Claude API wrapper
│   ├── github_tools.py              # GitHub API helpers
│   ├── browser_tools.py             # Playwright helpers
│   └── file_tools.py                # Output file management
├── config/
│   ├── settings.py                  # Pydantic settings (reads .env)
│   └── user_profile.py
├── user_data/
│   └── profile.example.json         # Fill this in and rename to profile.json
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
# Edit .env — add ANTHROPIC_API_KEY and GITHUB_TOKEN at minimum
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
python main.py github --username your_handle --role "AI Engineer" --niche "MLOps" --market "India"

# Run the full pipeline end-to-end
python main.py full --username your_handle --role "AI Engineer" --niche "MLOps" --market "India"

# Check application statuses (uses saved session)
python main.py status --thread-id <uuid>

# Evaluate a job offer
python main.py offer --thread-id <uuid> --company "TechCorp" --role "ML Engineer" --offer-file offer.txt

# Resume after the human-approval gate
python main.py resume --thread-id <uuid> --approve

# Get coaching on employer's counter-offer response
python main.py respond --thread-id <uuid> --offer-id offer_abc12345 --response-file reply.txt
```

---

## Outputs

Every run generates files in `outputs/` (gitignored — contains personal data):

| File | Content |
|---|---|
| `outputs/github_intelligence/improvement_plan_<date>.md` | Prioritised portfolio improvement plan |
| `outputs/resumes/<company>_resume.md` | Tailored resume per application |
| `outputs/cover_letters/<company>_cover_letter.md` | Role-specific cover letter |
| `outputs/form_screenshots/<company>.png` | Form preview before submission |
| `outputs/negotiation/<company>_negotiation_script.md` | Full negotiation playbook |
| `outputs/negotiation/<company>_response_coaching.md` | Coaching on employer's response |
| `outputs/reports/pipeline_<date>.md` | Weekly application pipeline digest |

---

## Roadmap

- [ ] Multi-LLM routing (Groq + Gemini Flash + Claude by task complexity)
- [ ] FastAPI backend exposing the orchestrator as REST endpoints
- [ ] Next.js dashboard with real-time pipeline visualization
- [ ] Supabase integration (replace JSON session files with PostgreSQL)
- [ ] Interview Prep Lead Agent (generates Q&A from JD + your profile)
- [ ] Gmail trigger for automatic offer/status parsing
- [ ] Semantic job search with pgvector embeddings

---

## Disclaimer

This tool is built for personal job search use. Automated interactions with LinkedIn, Indeed, and Naukri may conflict with their Terms of Service. The system is intentionally designed with a **human approval gate before every form submission** — no application is ever submitted without your explicit confirmation.

---

## Author

Built by [Rishab](https://github.com/rishab-br) as a portfolio project demonstrating hierarchical multi-agent orchestration, stateful LangGraph workflows, and human-in-the-loop AI system design.
