"""
JobHunter — CLI entry point.

Subcommands
-----------
  github      Run GitHub Intelligence only (portfolio audit + improvement plan)
  full        Run the complete pipeline end-to-end
  status      Run Status Tracker against an existing session
  offer       Inject a job offer and run Offer Intelligence
  resume      Resume a pipeline paused at the human-approval gate
  respond     Inject employer's counter-offer response and get coaching
  prep        Generate a full interview cheat sheet for a specific role

Usage examples
--------------
  python main.py github  --username johndoe --role "AI Engineer" --niche "MLOps"
  python main.py full    --username johndoe --role "AI Engineer" --niche "MLOps" --market "India"
  python main.py status  --thread-id <uuid>
  python main.py offer   --thread-id <uuid> --company "TechCorp" --role "ML Engineer" --offer-file offer.txt
  python main.py resume  --thread-id <uuid> --approve
  python main.py respond --thread-id <uuid> --offer-id offer_abc12345 --response-file response.txt
  python main.py prep    --company "Acme AI" --role "ML Engineer" --jd-file jd.txt --company-url acme.ai
"""
import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from state import GlobalState, SystemPhase, initial_state
from orchestrator import (
    run_full_pipeline,
    run_module,
    resume_after_approval,
    inject_offer,
    inject_employer_response,
    inject_interview_target,
)
from agents.github_intelligence.lead import build_subgraph as _github_sg

console = Console()

# ── State persistence (simple JSON file per session) ──────────────────────────

SESSION_DIR = Path("memory/sessions")


def _save_session(thread_id: str, state: GlobalState) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{thread_id}.json"
    serialisable = {k: v for k, v in state.items() if _is_serialisable(v)}
    path.write_text(json.dumps(serialisable, indent=2, default=str), encoding="utf-8")
    console.print(f"\n[dim]Session saved → {path}[/dim]")


def _load_session(thread_id: str) -> GlobalState:
    path = SESSION_DIR / f"{thread_id}.json"
    if not path.exists():
        console.print(f"[red]No session found for thread_id: {thread_id}[/red]")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def _is_serialisable(v) -> bool:
    try:
        json.dumps(v, default=str)
        return True
    except Exception:
        return False


# ── Subcommand handlers ────────────────────────────────────────────────────────

def cmd_github(args: argparse.Namespace) -> None:
    console.print(Panel(
        f"[bold cyan]GitHub Intelligence[/bold cyan]\n"
        f"User: [green]{args.username}[/green]  →  "
        f"[yellow]{args.role}[/yellow] / {args.niche} in {args.market}",
        title="JobHunter", border_style="cyan",
    ))

    state = initial_state(
        github_username=args.username,
        target_role=args.role,
        target_market=args.market,
        target_niche=args.niche,
    )
    state["current_phase"] = SystemPhase.GITHUB_ANALYSIS

    with console.status("[cyan]Analyzing GitHub profile...[/cyan]", spinner="dots"):
        graph = _github_sg().compile()
        result: GlobalState = graph.invoke(state)

    _print_logs(result)
    _print_audit(result)
    _print_gaps(result)
    _print_plan(result)


def cmd_full(args: argparse.Namespace) -> None:
    console.print(Panel(
        f"[bold cyan]Full Pipeline[/bold cyan]\n"
        f"User: [green]{args.username}[/green]  →  "
        f"[yellow]{args.role}[/yellow] / {args.niche} in {args.market}",
        title="JobHunter", border_style="cyan",
    ))

    with console.status("[cyan]Running full pipeline...[/cyan]", spinner="dots"):
        result, thread_id = run_full_pipeline(
            github_username=args.username,
            target_role=args.role,
            target_market=args.market,
            target_niche=args.niche,
        )

    _save_session(thread_id, result)
    _print_logs(result)
    _print_pipeline_summary(result)
    console.print(f"\n[bold green]Thread ID:[/bold green] {thread_id}")
    console.print("[dim]Use this ID with 'status', 'resume', 'offer', or 'respond' subcommands.[/dim]")


def cmd_status(args: argparse.Namespace) -> None:
    console.print(Panel("[bold cyan]Status Tracker[/bold cyan]", title="JobHunter", border_style="cyan"))
    state = _load_session(args.thread_id)

    with console.status("[cyan]Checking application statuses...[/cyan]", spinner="dots"):
        result, _ = run_module("status", state, thread_id=args.thread_id)

    _save_session(args.thread_id, result)
    _print_logs(result)
    _print_pipeline_summary(result)


def cmd_offer(args: argparse.Namespace) -> None:
    offer_text = Path(args.offer_file).read_text(encoding="utf-8") if args.offer_file else args.offer_text or ""
    if not offer_text:
        console.print("[red]Provide offer text via --offer-file or --offer-text[/red]")
        sys.exit(1)

    state = _load_session(args.thread_id) if args.thread_id else _make_bare_state(args)

    console.print(Panel(
        f"[bold cyan]Offer Intelligence[/bold cyan]\n"
        f"Company: [green]{args.company}[/green]  Role: [yellow]{args.role}[/yellow]",
        title="JobHunter", border_style="cyan",
    ))

    state = inject_offer(
        state,
        company=args.company,
        job_title=args.role,
        offer_letter_text=offer_text,
        deadline_date=getattr(args, "deadline", None),
    )

    with console.status("[cyan]Evaluating offer...[/cyan]", spinner="dots"):
        result, thread_id = run_module("offer", state, thread_id=args.thread_id)

    _save_session(thread_id, result)
    _print_logs(result)
    _print_offer_summary(result)
    console.print(f"\n[bold green]Thread ID:[/bold green] {thread_id}")


def cmd_resume(args: argparse.Namespace) -> None:
    console.print(Panel(
        f"[bold cyan]Resuming Pipeline[/bold cyan]\n"
        f"Decision: [{'green' if args.approve else 'red'}]"
        f"{'APPROVE' if args.approve else 'SKIP'}[/]",
        title="JobHunter", border_style="cyan",
    ))

    with console.status("[cyan]Resuming after approval gate...[/cyan]", spinner="dots"):
        result = resume_after_approval(approved=args.approve, thread_id=args.thread_id)

    _save_session(args.thread_id, result)
    _print_logs(result)
    _print_pipeline_summary(result)


def cmd_prep(args: argparse.Namespace) -> None:
    """Run Interview Prep for a specific role."""
    # Load JD text
    if args.jd_file:
        jd_text = Path(args.jd_file).read_text(encoding="utf-8")
    elif args.jd_text:
        jd_text = args.jd_text
    else:
        console.print("[red]Provide JD via --jd-file or --jd-text[/red]")
        sys.exit(1)

    # Base state — load existing session or create a bare one
    state = _load_session(args.thread_id) if args.thread_id else _make_bare_state(args)

    console.print(Panel(
        f"[bold cyan]Interview Prep[/bold cyan]\n"
        f"Company: [green]{args.company}[/green]  →  "
        f"Role: [yellow]{args.role}[/yellow]",
        title="JobHunter", border_style="cyan",
    ))

    state = inject_interview_target(
        state,
        company=args.company,
        role=args.role,
        jd_text=jd_text,
        company_url=getattr(args, "company_url", "") or "",
        job_id=getattr(args, "job_id", None),
    )

    with console.status("[cyan]Preparing interview materials...[/cyan]", spinner="dots"):
        result, thread_id = run_module("interview_prep", state, thread_id=args.thread_id)

    _save_session(thread_id, result)
    _print_logs(result)
    _print_prep_summary(result)
    console.print(f"\n[bold green]Thread ID:[/bold green] {thread_id}")


def cmd_daily(args: argparse.Namespace) -> None:
    """One-shot autonomous discovery run — designed for cron / Task Scheduler."""
    from automation import run_daily_discovery

    console.print(Panel(
        f"[bold cyan]Autopilot — Daily Discovery[/bold cyan]\n"
        f"Role: [yellow]{args.role}[/yellow] / {args.niche} in {args.market}",
        title="JobHunter", border_style="cyan",
    ))

    with console.status("[cyan]Running autonomous discovery...[/cyan]", spinner="dots"):
        summary = run_daily_discovery(
            role=args.role, niche=args.niche,
            market=args.market, github_username=args.username,
        )

    table = Table(title="Daily Run Summary", border_style="green", show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Jobs Scored", str(summary["total_scored"]))
    table.add_row("New Since Last Run", str(summary["new_jobs"]))
    table.add_row("High Priority", str(summary["high_priority"]))
    table.add_row("Digest", summary["digest_path"])
    table.add_row("Telegram", "delivered ✅" if summary["telegram_delivered"] else "not configured")
    console.print(table)


def cmd_autopilot(args: argparse.Namespace) -> None:
    """Long-running scheduler: daily discovery at a fixed local time."""
    from automation import autopilot_loop

    console.print(Panel(
        f"[bold cyan]Autopilot Mode[/bold cyan]\n"
        f"Role: [yellow]{args.role}[/yellow] / {args.niche} in {args.market}\n"
        f"Daily run at: [green]{args.at}[/green]  (Ctrl+C to stop)",
        title="JobHunter", border_style="cyan",
    ))
    autopilot_loop(
        role=args.role, niche=args.niche,
        market=args.market, github_username=args.username, at=args.at,
    )


def cmd_respond(args: argparse.Namespace) -> None:
    response_text = Path(args.response_file).read_text(encoding="utf-8") if args.response_file else args.response_text or ""
    if not response_text:
        console.print("[red]Provide response via --response-file or --response-text[/red]")
        sys.exit(1)

    state = _load_session(args.thread_id)
    state = inject_employer_response(state, offer_id=args.offer_id, response_text=response_text)

    console.print(Panel("[bold cyan]Response Coaching[/bold cyan]", title="JobHunter", border_style="cyan"))

    with console.status("[cyan]Analyzing employer response...[/cyan]", spinner="dots"):
        result, _ = run_module("offer", state, thread_id=args.thread_id)

    _save_session(args.thread_id, result)
    _print_logs(result)
    _print_response_coaching(result)


# ── Display helpers ────────────────────────────────────────────────────────────

def _print_logs(state: GlobalState) -> None:
    console.print("\n[dim]─── Pipeline Logs ───[/dim]")
    for log in (state.get("logs") or [])[-20:]:  # last 20 to keep output clean
        console.print(f"[dim]{log}[/dim]")


def _print_audit(state: GlobalState) -> None:
    audit = state.get("github_audit")
    if not audit:
        return
    score = audit.get("overall_score", 0)
    color = "green" if score >= 70 else "yellow" if score >= 50 else "red"
    console.print(Panel(
        f"[bold]Score:[/bold] [{color}]{score}/100[/]\n"
        f"[bold]Bio Quality:[/bold] {audit.get('bio_quality')}\n"
        f"[bold]Languages:[/bold] {', '.join(audit.get('top_languages', []))}\n\n"
        f"[bold]Summary:[/bold]\n{audit.get('summary')}\n\n"
        f"[bold green]Strengths:[/bold green]\n" +
        "\n".join(f"  ✓ {s}" for s in audit.get("key_strengths", [])) +
        f"\n\n[bold red]Red Flags:[/bold red]\n" +
        "\n".join(f"  ✗ {f}" for f in audit.get("immediate_red_flags", [])),
        title="Profile Audit", border_style="blue",
    ))


def _print_gaps(state: GlobalState) -> None:
    gap = state.get("gap_analysis")
    if not gap:
        return
    sev = gap.get("gap_severity", "medium")
    color = {"high": "red", "medium": "yellow", "low": "green"}.get(sev, "white")
    table = Table(title="Gap Analysis", border_style="magenta", show_lines=True)
    table.add_column("Area", style="bold")
    table.add_column("Details")
    table.add_row("Severity", Text(sev.upper(), style=color))
    table.add_row("Missing Critical Skills", "\n".join(f"• {s}" for s in gap.get("missing_critical_skills", [])))
    table.add_row(
        "Missing Projects",
        "\n".join(f"• {p['project_type']}: {p.get('why_it_matters', '')}" for p in gap.get("missing_project_types", [])),
    )
    table.add_row("Profile Gaps", "\n".join(f"• {g}" for g in gap.get("profile_presentation_gaps", [])))
    console.print(table)
    console.print(f"\n[italic]{gap.get('summary')}[/italic]\n")


def _print_plan(state: GlobalState) -> None:
    plan = state.get("improvement_plan")
    if not plan:
        return
    table = Table(title=f"Improvement Plan ({len(plan)} actions)", border_style="green", show_lines=True)
    table.add_column("#", width=3, style="bold cyan")
    table.add_column("Action", style="bold")
    table.add_column("Category", width=16)
    table.add_column("Effort", width=8)
    table.add_column("Impact", width=8)
    e_color = {"small": "green", "medium": "yellow", "large": "red"}
    i_color = {"high": "green", "medium": "yellow", "low": "dim"}
    for item in plan:
        e, i = item.get("effort", ""), item.get("impact", "")
        table.add_row(
            str(item.get("priority")), item.get("title", ""),
            f"[dim]{item.get('category', '')}[/dim]",
            f"[{e_color.get(e, 'white')}]{e}[/]",
            f"[{i_color.get(i, 'white')}]{i}[/]",
        )
    console.print(table)
    for log in reversed(state.get("logs") or []):
        if "saved to" in log:
            console.print(f"\n[green]Full report → {log.split('saved to ')[-1]}[/green]")
            break


def _print_pipeline_summary(state: GlobalState) -> None:
    applications = state.get("applications") or []
    statuses = state.get("application_statuses") or {}
    scored = state.get("scored_jobs") or []
    ghosted = state.get("ghosted_applications") or []
    report = state.get("pipeline_report") or {}

    table = Table(title="Pipeline Summary", border_style="cyan", show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Jobs Discovered", str(len(state.get("discovered_jobs") or [])))
    table.add_row("Jobs Scored ≥ 65", str(sum(1 for j in scored if j.get("relevance_score", 0) >= 65)))
    table.add_row("Applications Submitted", str(len(applications)))
    table.add_row("Ghosted", str(len(ghosted)))
    table.add_row("Follow-ups Queued", str(len(state.get("followup_queue") or [])))
    if report:
        table.add_row("Pipeline Report", str(report.get("report_path", "")))
    console.print(table)

    if applications:
        console.print("\n[bold]Application Log:[/bold]")
        for app in applications:
            status = statuses.get(app.get("job_id"), "applied")
            s_color = {"submitted": "green", "viewed": "cyan", "shortlisted": "yellow",
                       "interview_scheduled": "bold green", "rejected": "red"}.get(status, "white")
            console.print(
                f"  [{s_color}]{status:20}[/] {app.get('company'):25} {app.get('job_title')}"
            )


def _print_offer_summary(state: GlobalState) -> None:
    evals = state.get("offer_evaluations") or []
    for ev in evals:
        parsed = ev.get("parsed_offer") or {}
        bench = ev.get("market_benchmark") or {}
        counter = ev.get("counter_recommendation") or {}
        risk = ev.get("risk_assessment") or {}
        risk_color = {"high": "red", "medium": "yellow", "low": "green"}.get(
            risk.get("overall_risk_level", ""), "white"
        )
        console.print(Panel(
            f"[bold]Offered CTC:[/bold] {parsed.get('total_ctc_annual')}\n"
            f"[bold]Fair Value Range:[/bold] {bench.get('fair_value_range')}\n"
            f"[bold]Offer Percentile:[/bold] {bench.get('offer_percentile')}\n"
            f"[bold]Risk Level:[/bold] [{risk_color}]{risk.get('overall_risk_level', '').upper()}[/]\n\n"
            f"[bold green]Counter Ask:[/bold green] {counter.get('counter_ask')}\n"
            f"[bold red]Walk-away Floor:[/bold red] {counter.get('walk_away_floor')}\n\n"
            f"[bold]Negotiation Script:[/bold] {ev.get('negotiation_script_path', 'N/A')}",
            title=f"Offer: {ev.get('company')} — {ev.get('job_title')}",
            border_style="yellow",
        ))


def _print_response_coaching(state: GlobalState) -> None:
    coaching_list = state.get("response_coaching") or []
    for coaching in coaching_list:
        move = coaching.get("recommended_move", "")
        move_icon = {"accept": "✅", "counter_again": "🔄", "decline": "❌", "request_time": "⏳"}.get(move, "")
        console.print(Panel(
            f"[bold]Recommended Move:[/bold] {move_icon} {move.upper().replace('_', ' ')}\n\n"
            f"[bold]Why:[/bold] {coaching.get('reasoning')}\n\n"
            f"[bold]Full coaching report:[/bold] {coaching.get('report_path', 'N/A')}",
            title="Response Coaching",
            border_style="yellow",
        ))


def _print_prep_summary(state: GlobalState) -> None:
    sessions = state.get("interview_prep_sessions") or []
    if not sessions:
        return
    session = sessions[-1]  # most recent
    target = state.get("interview_prep_target") or {}
    questions = target.get("questions") or {}

    tech_count = len(questions.get("technical_questions", []))
    sd_count   = len(questions.get("system_design_questions", []))
    beh_count  = len(questions.get("behavioral_questions", []))
    co_count   = len(questions.get("company_specific_questions", []))
    ask_count  = len(questions.get("questions_to_ask_interviewer", []))

    console.print(Panel(
        f"[bold]Company:[/bold]  {session.get('company')}\n"
        f"[bold]Role:[/bold]     {session.get('role')}\n"
        f"[bold]Prep Date:[/bold] {session.get('prep_date')}\n\n"
        f"[bold cyan]Questions Generated:[/bold cyan]\n"
        f"  Technical:       [green]{tech_count}[/]\n"
        f"  System Design:   [green]{sd_count}[/]\n"
        f"  Behavioral:      [green]{beh_count}[/]\n"
        f"  Company-Specific:[green]{co_count}[/]\n"
        f"  To Ask Them:     [green]{ask_count}[/]\n\n"
        f"[bold green]Cheat Sheet:[/bold green] {session.get('cheat_sheet_path', 'N/A')}\n"
        f"[bold yellow]Quick Card:[/bold yellow]  {session.get('quick_card_path', 'N/A')}",
        title="Interview Prep Complete ✅",
        border_style="green",
    ))


def _make_bare_state(args: argparse.Namespace) -> GlobalState:
    return initial_state(
        github_username=getattr(args, "username", ""),
        target_role=getattr(args, "role", ""),
        target_market=getattr(args, "market", "India"),
        target_niche=getattr(args, "niche", ""),
    )


# ── Argument parsing ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jobhunter",
        description="JobHunter — AI-powered end-to-end job hunting system",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # github
    p_github = sub.add_parser("github", help="Run GitHub portfolio analysis")
    p_github.add_argument("--username", required=True)
    p_github.add_argument("--role", required=True)
    p_github.add_argument("--niche", required=True)
    p_github.add_argument("--market", default="India")

    # full
    p_full = sub.add_parser("full", help="Run the complete pipeline")
    p_full.add_argument("--username", required=True)
    p_full.add_argument("--role", required=True)
    p_full.add_argument("--niche", required=True)
    p_full.add_argument("--market", default="India")

    # status
    p_status = sub.add_parser("status", help="Check application statuses")
    p_status.add_argument("--thread-id", required=True, dest="thread_id")

    # offer
    p_offer = sub.add_parser("offer", help="Evaluate a job offer")
    p_offer.add_argument("--company", required=True)
    p_offer.add_argument("--role", required=True)
    p_offer.add_argument("--thread-id", dest="thread_id", default=None)
    p_offer.add_argument("--offer-file", dest="offer_file", default=None)
    p_offer.add_argument("--offer-text", dest="offer_text", default=None)
    p_offer.add_argument("--username", default="")
    p_offer.add_argument("--niche", default="")
    p_offer.add_argument("--market", default="India")

    # resume
    p_resume = sub.add_parser("resume", help="Resume after human-approval gate")
    p_resume.add_argument("--thread-id", required=True, dest="thread_id")
    approve_group = p_resume.add_mutually_exclusive_group(required=True)
    approve_group.add_argument("--approve", action="store_true")
    approve_group.add_argument("--skip", dest="approve", action="store_false")

    # prep
    p_prep = sub.add_parser("prep", help="Generate interview prep materials for a specific role")
    p_prep.add_argument("--company", required=True)
    p_prep.add_argument("--role", required=True)
    p_prep.add_argument("--jd-file", dest="jd_file", default=None, help="Path to JD text file")
    p_prep.add_argument("--jd-text", dest="jd_text", default=None, help="JD text inline")
    p_prep.add_argument("--company-url", dest="company_url", default="", help="Company website URL for richer research")
    p_prep.add_argument("--job-id", dest="job_id", default=None, help="Optional job_id to link to an existing application")
    p_prep.add_argument("--thread-id", dest="thread_id", default=None, help="Existing session thread to append prep to")
    p_prep.add_argument("--username", default="")
    p_prep.add_argument("--market", default="India")
    p_prep.add_argument("--niche", default="")

    # daily (one-shot autonomous discovery)
    p_daily = sub.add_parser("daily", help="One-shot autonomous discovery run + digest (cron-friendly)")
    p_daily.add_argument("--role", required=True)
    p_daily.add_argument("--niche", default="")
    p_daily.add_argument("--market", default="India")
    p_daily.add_argument("--username", default="")

    # autopilot (long-running daily scheduler)
    p_auto = sub.add_parser("autopilot", help="Run discovery every day at a fixed time, with Telegram digest")
    p_auto.add_argument("--role", required=True)
    p_auto.add_argument("--niche", default="")
    p_auto.add_argument("--market", default="India")
    p_auto.add_argument("--username", default="")
    p_auto.add_argument("--at", default="08:00", help="Local time HH:MM for the daily run")

    # respond
    p_respond = sub.add_parser("respond", help="Get coaching on employer's counter-offer response")
    p_respond.add_argument("--thread-id", required=True, dest="thread_id")
    p_respond.add_argument("--offer-id", required=True, dest="offer_id")
    p_respond.add_argument("--response-file", dest="response_file", default=None)
    p_respond.add_argument("--response-text", dest="response_text", default=None)

    args = parser.parse_args()

    dispatch = {
        "github":  cmd_github,
        "full":    cmd_full,
        "status":  cmd_status,
        "offer":   cmd_offer,
        "resume":  cmd_resume,
        "respond": cmd_respond,
        "prep":    cmd_prep,
        "daily":   cmd_daily,
        "autopilot": cmd_autopilot,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
