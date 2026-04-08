"""jot dashboard / report / review"""

from __future__ import annotations

from datetime import date, timedelta

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich import box

from jot.config import Config
from jot.vault import Vault

console = Console()


@click.command("dashboard")
def cmd_dashboard() -> None:
    """Show a summary dashboard of the vault."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    stats = vault.stats()
    limit = cfg.dashboard_limit

    # Stats panel
    stat_table = Table(box=None, show_header=False, padding=(0, 2))
    stat_table.add_column(style="bold cyan")
    stat_table.add_column(justify="right")
    stat_table.add_row("Notes", str(stats["total_notes"]))
    stat_table.add_row("Words", str(stats["total_words"]))
    stat_table.add_row("Tags", str(stats["total_tags"]))
    stat_table.add_row("Orphans", str(stats["orphans"]))
    stat_table.add_row("Broken links", str(stats["unresolved"]))

    console.print(Panel(stat_table, title=f"[bold]{root.name}[/bold]", border_style="cyan"))

    # Recent notes
    recent = vault.recent(limit)
    if recent:
        console.print("\n[bold]Recent[/bold]")
        from datetime import datetime
        for note in recent:
            mtime = datetime.fromtimestamp(note.path.stat().st_mtime).strftime("%Y-%m-%d")
            console.print(f"  [dim]{mtime}[/dim]  [cyan]{note.title}[/cyan]")

    # Stale notes (brief)
    stale = vault.stale(cfg.stale_days)
    if stale:
        console.print(f"\n[bold]Stale[/bold] [dim](>{cfg.stale_days}d)[/dim]")
        for note in stale[:limit]:
            console.print(f"  [dim]{note.path.relative_to(root)}[/dim]")
        if len(stale) > limit:
            console.print(f"  [dim]…and {len(stale) - limit} more (run [bold]jot stale[/bold])[/dim]")

    # Upcoming agenda
    today = date.today()
    horizon = date.fromordinal(today.toordinal() + 7)
    agenda_items = []
    for note in vault.all_notes():
        if note.due and today <= note.due <= horizon:
            agenda_items.append((note.due, "due", note.title))
        if note.scheduled and today <= note.scheduled <= horizon:
            agenda_items.append((note.scheduled, "scheduled", note.title))

    if agenda_items:
        agenda_items.sort()
        console.print("\n[bold]Upcoming (7d)[/bold]")
        for d, kind, title in agenda_items[:limit]:
            console.print(f"  [dim]{d.isoformat()}[/dim]  {title}  [dim]({kind})[/dim]")


@click.command("report")
@click.option("--since", default=None, metavar="YYYY-MM-DD", help="Start date (default: 30 days ago).")
@click.option("--until", default=None, metavar="YYYY-MM-DD", help="End date (default: today).")
def cmd_report(since: str | None, until: str | None) -> None:
    """Show notes modified in a date range."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    today = date.today()
    start = date.fromisoformat(since) if since else today - timedelta(days=30)
    end = date.fromisoformat(until) if until else today

    from datetime import datetime
    notes = [
        n for n in vault.all_notes()
        if start <= date.fromtimestamp(n.path.stat().st_mtime) <= end
    ]
    notes.sort(key=lambda n: n.path.stat().st_mtime, reverse=True)

    console.print(f"[bold]Notes modified {start} → {end}[/bold]  [dim]({len(notes)} total)[/dim]\n")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Modified", style="dim")
    table.add_column("Words", justify="right", style="dim")

    for note in notes:
        mtime = datetime.fromtimestamp(note.path.stat().st_mtime).strftime("%Y-%m-%d")
        words = len(note.body.split())
        table.add_row(str(note.path.relative_to(root)), mtime, str(words))

    console.print(table)


@click.command("review")
def cmd_review() -> None:
    """Show notes that are drafts or have no tags (worth reviewing)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    candidates = []
    for note in vault.all_notes():
        reasons = []
        if note.status == "draft":
            reasons.append("draft")
        if not note.tags:
            reasons.append("no tags")
        if not note.body.strip():
            reasons.append("empty")
        if reasons:
            candidates.append((note, reasons))

    if not candidates:
        console.print("[green]Nothing needs review.[/green]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Flags", style="yellow")

    for note, reasons in sorted(candidates, key=lambda x: x[0].title):
        table.add_row(str(note.path.relative_to(root)), ", ".join(reasons))

    console.print(table)
    console.print(f"\n[dim]{len(candidates)} note(s) to review[/dim]")
