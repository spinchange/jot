"""jot tasks / agenda"""

from __future__ import annotations

from datetime import date

import click
from rich.console import Console
from rich.table import Table
from rich import box

from jot.config import Config
from jot.vault import Vault

console = Console()


@click.command("tasks")
@click.argument("title", required=False)
@click.option("--open", "open_only", is_flag=True, help="Show only uncompleted tasks.")
@click.option("--done", "done_only", is_flag=True, help="Show only completed tasks.")
def cmd_tasks(title: str | None, open_only: bool, done_only: bool) -> None:
    """List GFM checkbox tasks from a note or the entire vault."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    if title:
        note = vault.resolve(title)
        if not note:
            raise click.ClickException(f"Note not found: {title!r}")
        notes = [note]
    else:
        notes = vault.all_notes()

    total = 0
    for note in sorted(notes, key=lambda n: n.title):
        tasks = note.tasks
        if open_only:
            tasks = [(d, t) for d, t in tasks if not d]
        elif done_only:
            tasks = [(d, t) for d, t in tasks if d]

        if not tasks:
            continue

        if not title:
            console.print(f"\n[bold]{note.path.relative_to(root)}[/bold]")

        for done, text in tasks:
            mark = "[green]✓[/green]" if done else "[dim]○[/dim]"
            style = "dim" if done else ""
            console.print(f"  {mark}  [{style}]{text}[/{style}]" if style else f"  {mark}  {text}")
            total += 1

    if total == 0:
        console.print("[dim]No tasks found.[/dim]")
    else:
        console.print(f"\n[dim]{total} task(s)[/dim]")


@click.command("agenda")
@click.option("--days", default=7, show_default=True, help="Look-ahead window in days.")
def cmd_agenda(days: int) -> None:
    """Show notes with due or scheduled dates in the upcoming window."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    today = date.today()
    horizon = date.fromordinal(today.toordinal() + days)

    items: list[tuple[date, str, str, str]] = []  # (date, kind, title, path)

    for note in vault.all_notes():
        rel = str(note.path.relative_to(root))
        if note.due and today <= note.due <= horizon:
            items.append((note.due, "due", note.title, rel))
        if note.scheduled and today <= note.scheduled <= horizon:
            items.append((note.scheduled, "scheduled", note.title, rel))

    if not items:
        console.print(f"[dim]Nothing due or scheduled in the next {days} day(s).[/dim]")
        return

    items.sort(key=lambda x: x[0])

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Date")
    table.add_column("Type", style="dim")
    table.add_column("Note", style="cyan")

    for d, kind, title, rel in items:
        diff = (d - today).days
        date_str = d.isoformat()
        if diff == 0:
            date_str = f"[bold red]{date_str} (today)[/bold red]"
        elif diff == 1:
            date_str = f"[yellow]{date_str} (tomorrow)[/yellow]"
        table.add_row(date_str, kind, title)

    console.print(table)
