<div align="center">

<br/>

<img src="https://img.shields.io/badge/⚡-JobHunter-00D4FF?style=for-the-badge&labelColor=0D1117&color=00D4FF" height="42"/>

### Hierarchical multi-agent job hunting system — portfolio audit to offer negotiation, fully orchestrated.

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-Dashboard-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Playwright](https://img.shields.io/badge/Playwright-Scraping-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

<br/>

</div>

---

## What is this?

JobHunter is a production-grade agentic AI system that handles the entire job search lifecycle as a stateful, resumable pipeline. Each stage is an independent **Lead Agent** with its own worker graph — they share a single `GlobalState` and are orchestrated by a **Master Orchestrator** built on LangGraph.

```
GitHub Portfolio Audit → Job Discovery → Application Engine → Status Tracking → Offer Intelligence → Interview Prep
       ↑                      ↑                  ↑
  Improvement Plan      Job Enricher     Human Approval Gate
  (10 prioritised       (page fetch +    (LangGraph interrupt())
   actions)              web context)
```

> **No application is ever submitted without your explicit approval.** The human-in-the-loop gate is a first-class LangGraph `interrupt()`, not a workaround.

---

## Agent Architecture

<details open>
<summary><b>🔬 GitHub Intelligence Lead</b> — Portfolio audit &amp; gap analysis</summary>

| Worker | What it does |
|--------|-------------|
| **Profile Auditor** | GitHub API → bio quality, activity score, language breakdown, 0–100 profile score |
| **Project Depth Analyzer** | Per-repo: README quality, tech stack detection, recency, completeness score |
| **Trend Scout** | LLM → must-have skills + hot project types for your target role &amp; niche |
| **Gap Analyzer** | Profile vs. market trends → severity-rated gap report (high / medium / low) |
| **Improvement Planner** | Prioritised 10-action plan → `outputs/github_intelligence/improvement_plan_<date>.md` |

</details>

<details>
<summary><b>🔍 Job Discovery Lead</b> — Multi-platform scraping &amp; scoring</summary>

| Worker | What it does |
|--------|-------------|
| **LinkedIn Scraper** | httpx → LinkedIn's public guest jobs API — **zero login, zero cookies, zero ban risk**. Handles regional subdomains + tracking-param stripping |
| **Indeed Scraper** | Playwright → no login required → paginate across 3 pages → 25 listings |
| **Naukri Scraper** | Playwright → SEO URL + query-param fallback → new-tab JD extraction |
| **ATS Boards Scraper** | Greenhouse + Lever **public JSON APIs** — structured postings with full JDs, zero scraping fragility. Boards come from a seed list + DuckDuckGo discovery of companies hiring your target role |
| **Job Enricher** | Two-phase: concurrent httpx fetch of each job's public detail page (descriptions the guest API omits) + DuckDuckGo company-context search appended to every JD |
| **JD Analyzer** | LLM → extracts must-have skills, seniority, red flags, company signals per JD |
| **Relevance Scorer** | Embedding pre-filter (Gemini `gemini-embedding-001`, cosine top-K) → LLM scores only the best candidates → 0–100 match score, sorted &amp; prioritised |

</details>

<details>
<summary><b>📄 Application Engine Lead</b> — Tailored docs + human-approved submission</summary>

| Worker | What it does |
|--------|-------------|
| **Resume Tailor** | LLM → ATS-optimised resume mirroring the JD → Markdown source + **rendered PDF** (headless Chromium) in `outputs/resumes/` |
| **Cover Letter Writer** | LLM → role + company-specific 3-paragraph letter → `outputs/cover_letters/` |
| **Form Filler** | Playwright → fills every field on LinkedIn / Indeed / Naukri, takes screenshot |
| **⚠️ Human Approval Gate** | `LangGraph interrupt()` — pipeline pauses, you review docs + screenshot before anything is submitted |
| **Submission Executor** | Playwright → clicks Submit *only* after your explicit approval. **Greenhouse and Lever forms are public** (standardised fields, PDF resume upload) — the only platforms where a true end-to-end apply works with no login |

</details>

<details>
<summary><b>📊 Status Tracker Lead</b> — Application monitoring &amp; follow-ups</summary>

| Worker | What it does |
|--------|-------------|
| **Application Monitor** | Playwright → polls LinkedIn/Indeed for status changes on submitted apps |
| **Follow-up Scheduler** | LLM → drafts follow-up emails for apps silent for 7+ days |
| **Ghosted Detector** | Flags applications with zero movement after 21 days |
| **Pipeline Reporter** | Weekly markdown digest → `outputs/reports/pipeline_<date>.md` |

</details>

<details>
<summary><b>💰 Offer Intelligence Lead</b> — CTC benchmarking &amp; negotiation</summary>

| Worker | What it does |
|--------|-------------|
| **Offer Parser** | LLM → extracts every CTC component (base, bonus, equity, benefits) |
| **Market Benchmarker** | AmbitionBox scrape + LLM → P25/P50/P75/P90 bands for your role &amp; market |
| **Clause Risk Analyzer** | LLM → NCA, IP assignment, clawback, notice period — severity-rated |
| **Counter-offer Calculator** | LLM → specific ask number + walk-away floor + 5 justification points |
| **Negotiation Script Gen** | LLM → email + phone scripts + pushback handling → `outputs/negotiation/` |
| **Response Coach** | LLM → analyzes employer's reply → recommends accept / counter / decline |

</details>

<details>
<summary><b>🎤 Interview Prep Lead</b> — Role-specific cheat sheets</summary>

| Worker | What it does |
|--------|-------------|
| **JD Decoder** | LLM → surfaces hidden requirements, culture signals, likely interview focus |
| **Company Researcher** | Fetches company website → talking points, smart questions to ask |
| **Question Generator** | LLM → 8–10 technical + 2–3 system design + 6–8 behavioral + company-specific |
| **Answer Crafter** | LLM → STAR-format answers, system design frameworks, technical walkthroughs |
| **Cheat Sheet Builder** | Assembles full cheat sheet + 5-min quick card → `outputs/interview_prep/` |

</details>

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| `LangGraph interrupt()` for approval | Graph pauses mid-execution, checkpointed to disk — resumes exactly where it stopped across server restarts |
| Single `GlobalState` TypedDict | All 6 lead agents and 30+ workers share one schema; the Master Orchestrator routes on `current_phase` |
| Standalone subgraph execution | Individual module runs bypass the master graph — prevents unintended cascading to downstream phases |
| Dedicated `skills/` layer | Workers never import Playwright or the GitHub API directly — all I/O goes through `skills/` |
| Guest-mode LinkedIn scraping | Deliberate pivot away from authenticated automation: the public guest API needs no account, so there is no account to ban and no stored credentials to leak |
| Enrich-after-scrape pattern | The guest API returns thin listings; a separate enricher node concurrently fetches public job pages + web context, so scraping stays fast and ban-safe while JDs stay rich |
| ATS-first submission | Greenhouse/Lever publish jobs as public JSON APIs and accept applications through public forms — structured data in, real submissions out, no ToS gray zone |
| Embeddings before LLM scoring | When discovery returns more than 20 jobs, a cosine pre-filter (3072-dim Gemini embeddings) discards poor fits before the LLM sees them — scoring cost stays flat as sources grow |
| Groq primary, Gemini fallback | Groq's Llama 3.3 70B is fast and cheap for structured extraction; Gemini 2.5 Flash handles JSON-mode fallback |
| FastAPI + SSE streaming | Backend streams agent log lines to the React dashboard in real time via Server-Sent Events |

---

## Agent Types Demonstrated

| Type | Where in the system |
|------|-------------------|
| **Reactive** | Form Filler, Submission Executor |
| **Model-based** | Status Tracker, Application Monitor |
| **Goal-based** | Resume Tailor, Application Engine Lead |
| **Utility-based** | Relevance Scorer, Clause Risk Analyzer |
| **Learning** | Improvement Planner — adapts plan based on which applications generate responses |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | [LangGraph](https://langchain-ai.github.io/langgraph/) — StateGraph, subgraphs, MemorySaver |
| LLM routing | [Groq](https://groq.com) (Llama 3.3 70B) + [Gemini](https://ai.google.dev) (2.5 Flash) fallback |
| Browser automation | [Playwright](https://playwright.dev/) — anti-detection, multi-tab, screenshot |
| HTTP scraping | [httpx](https://www.python-httpx.org/) — LinkedIn guest API, job-page enrichment, DuckDuckGo context |
| Backend | [FastAPI](https://fastapi.tiangolo.com) + SSE streaming |
| Frontend | [React 18](https://react.dev) + TypeScript + [Vite](https://vitejs.dev) + [Tailwind CSS](https://tailwindcss.com) |
| GitHub data | [PyGithub](https://pygithub.readthedocs.io/) + GitHub OAuth |
| Auth + storage | [Supabase](https://supabase.com) (multi-user) with local JSON fallback |
| Config | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Language | Python 3.11+ |

---

## Project Structure

```
JobHunter/
├── main.py                          # CLI entry point (7 subcommands)
├── state/global_state.py            # GlobalState TypedDict + SystemPhase enum
├── orchestrator/master.py           # Master Orchestrator — routing, compile, interrupt/resume
│
├── agents/
│   ├── github_intelligence/         # Lead + 5 workers
│   ├── job_discovery/               # Lead + 3 scrapers + enricher + analyzer + scorer
│   ├── application_engine/          # Lead + 5 workers (incl. human approval gate)
│   ├── status_tracker/              # Lead + 4 workers
│   ├── offer_intelligence/          # Lead + 6 workers
│   └── interview_prep/              # Lead + 5 workers
│
├── skills/
│   ├── llm.py                       # Groq → Gemini fallback, text + JSON modes
│   ├── github_tools.py              # GitHub API helpers
│   ├── browser_tools.py             # Playwright session helpers
│   └── file_tools.py                # Output file management
│
├── backend/
│   ├── main.py                      # FastAPI app — serves React SPA + API routes
│   ├── runner.py                    # Background job runner + SSE pub/sub
│   └── routes/                      # sessions, modules, data, stream, auth
│
├── frontend/                        # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── App.tsx                  # State management, routing, SSE listener
│       ├── screens/                 # Dashboard, GithubIntel, JobDiscovery, Applications, Offers, InterviewPrep
│       └── modals/                  # NewSession, Offer, Prep
│
├── config/settings.py               # Pydantic settings — reads .env
└── memory/sessions/                 # JSON session files (Supabase fallback)
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/rishab-br/job-hunter.git
cd job-hunter

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -e .
playwright install chromium
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env` — minimum required keys:

```env
GEMINI_API_KEY=...          # Primary LLM
GROQ_API_KEY_1=...          # App Groq key (optional but recommended)
GROQ_API_KEY_2=...          # Graphify Groq key
GITHUB_TOKEN=...            # For GitHub Intelligence
GITHUB_USERNAME=...
```

> LinkedIn job discovery needs **no credentials** — it uses the public guest API.

### 3. Start the dashboard

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend dev server
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** → Create a session → Run modules from the dashboard.

---

## CLI Usage

```bash
# Audit your GitHub portfolio
python main.py github --username rishab-br --role "AI Engineer" --niche "Agentic AI" --market "India"

# Full pipeline end-to-end
python main.py full --username rishab-br --role "AI Engineer" --niche "Agentic AI" --market "India"

# Check application statuses
python main.py status --thread-id <uuid>

# Evaluate a job offer
python main.py offer --thread-id <uuid> --company "Stripe" --role "ML Engineer" --offer-file offer.txt

# Resume after human-approval gate
python main.py resume --thread-id <uuid> --approve

# Get coaching on employer's response
python main.py respond --thread-id <uuid> --offer-id offer_abc12345 --response-file reply.txt

# Generate interview prep for a role
python main.py prep --company "Acme AI" --role "ML Engineer" --jd-file jd.txt

# One-shot autonomous discovery + digest (cron / Task Scheduler friendly)
python main.py daily --role "AI Engineer" --niche "Agentic AI" --market "India"

# Autopilot: discovery every morning at 08:00, digest to Telegram
python main.py autopilot --role "AI Engineer" --niche "Agentic AI" --at 08:00
```

---

## 🌅 Autopilot — the agent that works while you sleep

```
every morning at 08:00
        │
        ▼
Job Discovery subgraph (LinkedIn guest + Indeed + Naukri + Greenhouse + Lever)
        │
        ▼
Dedupe against every job seen on previous runs   (memory/autopilot/seen_jobs.json)
        │
        ▼
Markdown digest → outputs/digests/digest_<date>.md
        │
        ▼
📧 Gmail: "JobHunter Daily — 7 new matches, 2 high priority" (HTML digest)
   + optional 📱 Telegram compact summary
```

- **Discovery only** — autopilot never applies to anything. The human approval gate is untouchable.
- **Profile-aware** — reuses the freshest GitHub audit from your saved sessions, so relevance scores reflect *your* strengths without re-auditing every morning.
- **Zero new dependencies** — scheduling is a transparent sleep-until loop; email is stdlib `smtplib`; Telegram is one `httpx.post`.
- **Three ways to run it:** `python main.py autopilot` (foreground loop), OS cron / Task Scheduler calling `python main.py daily`, or `docker compose --profile autopilot up -d`.

**Gmail setup** (digests always land in `outputs/digests/` regardless): enable 2-Step Verification, create an [App Password](https://myaccount.google.com/apppasswords), then set `SMTP_USERNAME` + `SMTP_PASSWORD` in `.env`. The digest arrives as a styled HTML email with a plain-text fallback. Telegram stays available as an optional secondary channel (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`).

---

## Outputs

All generated files land in `outputs/` (gitignored — contains personal data):

| Path | Content |
|------|---------|
| `github_intelligence/improvement_plan_<date>.md` | Prioritised portfolio action plan |
| `resumes/<company>_resume.md` | ATS-optimised resume per job |
| `cover_letters/<company>_cover_letter.md` | Role + company-specific letter |
| `form_screenshots/<company>.png` | Form preview before submission |
| `negotiation/<company>_negotiation_script.md` | Full email + phone negotiation playbook |
| `negotiation/<company>_response_coaching.md` | Coaching after employer replies |
| `interview_prep/<company>_cheat_sheet.md` | Full Q&amp;A cheat sheet |
| `interview_prep/<company>_quick_card.md` | 5-minute pre-interview card |
| `reports/pipeline_<date>.md` | Weekly application pipeline digest |
| `digests/digest_<date>.md` | Autopilot daily discovery digest |

---

## Roadmap

- [x] GitHub Intelligence — portfolio audit + gap analysis + improvement plan
- [x] Job Discovery — LinkedIn (guest API, no login) / Indeed / Naukri scrapers
- [x] Job Enricher — concurrent description fetch + DuckDuckGo company context
- [x] Greenhouse + Lever — public JSON API discovery + real end-to-end form submission
- [x] Resume PDF rendering — Markdown → styled PDF via headless Chromium
- [x] Embedding pre-filter — Gemini embeddings rank jobs before LLM scoring
- [x] Application Engine — resume + cover letter tailoring + form filling
- [x] Human Approval Gate — LangGraph `interrupt()` before every submission
- [x] Status Tracker — application monitoring + follow-up scheduling + ghosted detection
- [x] Offer Intelligence — CTC benchmarking + clause risk + counter-offer + negotiation script
- [x] Interview Prep — JD decoding + Q&A generation + cheat sheet builder
- [x] FastAPI backend + SSE real-time log streaming
- [x] React dashboard — Mission Control with live agent log terminal
- [x] GitHub OAuth + Supabase multi-user support
- [x] Autopilot — daily autonomous discovery + dedupe + Telegram digest
- [ ] Gmail trigger — auto-detect offer emails and kick off Offer Intelligence
- [ ] pgvector semantic job search — embed JDs and find similar roles
- [ ] Multi-user portfolio sharing — share your improvement plan publicly

---

## Disclaimer

Built for personal job search use. LinkedIn job discovery deliberately uses only the **public guest API** — no account, no cookies, no authenticated automation. Automated interactions with Indeed and Naukri may conflict with their Terms of Service. The system is intentionally designed with a **human approval gate before every form submission** — no application is ever auto-submitted.

---

<div align="center">

Built by [Rishab](https://github.com/rishab-br) · Demonstrating hierarchical multi-agent orchestration, stateful LangGraph workflows, and human-in-the-loop system design.

</div>
