"""jot list / search / find / pick / recent / stale / preview"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich import box

from jot.config import Config
from jot.vault import Vault

console = Console()

FormatChoice = Literal["rich", "plain", "json"]


def _render_notes(notes: list, root: Path, fmt: FormatChoice) -> None:
    """Render a list of notes in the requested format.

    rich  — coloured Rich table (default, existing behaviour)
    plain — one filepath per line to stdout, no ANSI
    json  — JSON array of {path, title, tags, status} objects to stdout
    """
    if fmt == "json":
        data = [
            {
                "path": str(note.path.relative_to(root)),
                "title": note.title,
                "tags": note.tags,
                "status": note.status or "",
            }
            for note in notes
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if fmt == "plain":
        for note in notes:
            click.echo(str(note.path.relative_to(root)))
        return

    # fmt == "rich" (default)
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Tags", style="dim")
    table.add_column("Status", style="dim")

    for note in notes:
        rel = str(note.path.relative_to(root))
        tags_str = " ".join(f"#{t}" for t in note.tags[:5])
        table.add_row(rel, tags_str, note.status or "")

    console.print(table)
    console.print(f"[dim]{len(notes)} note(s)[/dim]")


@click.command("list")
@click.option("--tag", "-t", default=None, help="Filter by tag.")
@click.option("--folder", "-f", default=None, help="Filter by subfolder.")
@click.option("--status", "-s", default=None, help="Filter by frontmatter status.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "plain", "json"]),
    default="rich",
    show_default=True,
    help="Output format.",
)
def cmd_list(tag: str | None, folder: str | None, status: str | None, fmt: FormatChoice) -> None:
    """List notes in the vault."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.all_notes()

    if tag:
        tag_lower = tag.lower()
        notes = [n for n in notes if tag_lower in [t.lower() for t in n.tags]]
    if folder:
        folder_lower = folder.lower()
        notes = [n for n in notes if folder_lower in str(n.path.relative_to(root)).lower()]
    if status:
        notes = [n for n in notes if n.status == status]

    notes = sorted(notes, key=lambda n: str(n.path.relative_to(root)))

    if not notes:
        if fmt == "rich":
            console.print("[dim]No notes found.[/dim]")
        elif fmt == "json":
            click.echo("[]")
        return

    _render_notes(notes, root, fmt)


@click.command("search")
@click.argument("query")
@click.option("--case-sensitive", is_flag=True)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "plain", "json"]),
    default="rich",
    show_default=True,
    help="Output format.",
)
def cmd_search(query: str, case_sensitive: bool, fmt: FormatChoice) -> None:
    """Full-text search across all notes."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    results = vault.search(query, case_sensitive=case_sensitive)
    results = sorted(results, key=lambda n: n.title)

    if not results:
        if fmt == "rich":
            console.print("[dim]No results.[/dim]")
        elif fmt == "json":
            click.echo("[]")
        return

    if fmt == "json":
        data = [
            {
                "path": str(note.path.relative_to(root)),
                "title": note.title,
                "tags": note.tags,
                "status": note.status or "",
            }
            for note in results
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if fmt == "plain":
        for note in results:
            click.echo(str(note.path.relative_to(root)))
        return

    # rich
    for note in results:
        rel = str(note.path.relative_to(root))
        console.print(f"[cyan]{rel}[/cyan]  [dim]{note.title}[/dim]")
    console.print(f"\n[dim]{len(results)} result(s)[/dim]")


@click.command("find")
@click.argument("pattern")
def cmd_find(pattern: str) -> None:
    """Find notes by filename glob pattern."""
    cfg = Config.load()
    root = cfg.require_vault()

    import fnmatch
    if "." not in pattern:
        pattern = pattern + "*.md"
    elif not pattern.endswith(".md"):
        pattern = pattern + ".md"

    matches = sorted(root.rglob("*.md"), key=lambda p: str(p.relative_to(root)))
    matches = [p for p in matches if fnmatch.fnmatch(p.name, pattern)]

    if not matches:
        console.print("[dim]No matches.[/dim]")
        return

    for path in matches:
        console.print(str(path.relative_to(root)))


@click.command("recent")
@click.argument("n", default=10, type=int, required=False)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "plain", "json"]),
    default="rich",
    show_default=True,
    help="Output format.",
)
def cmd_recent(n: int, fmt: FormatChoice) -> None:
    """Show the N most recently modified notes."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.recent(n)

    if not notes:
        if fmt == "rich":
            console.print("[dim]No notes.[/dim]")
        elif fmt == "json":
            click.echo("[]")
        return

    if fmt == "json":
        data = [
            {
                "path": str(note.path.relative_to(root)),
                "title": note.title,
                "tags": note.tags,
                "status": note.status or "",
            }
            for note in notes
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if fmt == "plain":
        for note in notes:
            click.echo(str(note.path.relative_to(root)))
        return

    # rich
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Modified", style="dim")

    from datetime import datetime
    for note in notes:
        mtime = note.path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(str(note.path.relative_to(root)), dt)

    console.print(table)


def _interactive_stale(notes: list, root: Path, cfg: "Config") -> None:
    """Step through stale notes one by one, prompting for an action on each."""
    from datetime import datetime
    from jot.commands.create import _open_in_editor

    total = len(notes)
    for i, note in enumerate(notes, 1):
        mtime = note.path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        rel = str(note.path.relative_to(root))
        console.print(
            f"\n[bold]{i}/{total}[/bold]  [cyan]{rel}[/cyan]  [dim]last modified {dt}[/dim]"
        )
        raw = click.prompt(
            "  (o)pen  (t)ouch  (d)elete  (s)kip  (q)uit",
            default="s",
        ).strip().lower()

        if raw in ("o", "open"):
            _open_in_editor(note.path, cfg)
        elif raw in ("t", "touch"):
            note.touch()
            console.print("  [green]Touched.[/green] Modified date updated to today.")
        elif raw in ("d", "delete"):
            if click.confirm(f"  Delete {rel}?", default=False):
                note.path.unlink()
                console.print("  [red]Deleted.[/red]")
        elif raw in ("q", "quit"):
            console.print("[dim]Quit.[/dim]")
            break
        # else: skip
    else:
        console.print("\n[dim]All stale notes reviewed.[/dim]")


@click.command("stale")
@click.option("--days", default=None, type=int, help="Override stale threshold (days).")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "plain", "json"]),
    default="rich",
    show_default=True,
    help="Output format.",
)
@click.option("--interactive", "-i", is_flag=True, help="Review stale notes one by one.")
@click.option(
    "--batch",
    type=click.Choice(["touch", "delete"]),
    default=None,
    metavar="ACTION",
    help="Batch action on all stale notes: touch (update modified dates) or delete (remove files).",
)
def cmd_stale(days: int | None, fmt: FormatChoice, interactive: bool, batch: str | None) -> None:
    """List notes not modified recently."""
    if interactive and batch:
        raise click.UsageError("--interactive and --batch are mutually exclusive.")

    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    threshold = days if days is not None else cfg.stale_days
    notes = vault.stale(threshold)

    if not notes:
        if fmt == "rich":
            console.print(f"[dim]No stale notes (threshold: {threshold} days).[/dim]")
        elif fmt == "json":
            click.echo("[]")
        return

    if batch == "touch":
        for note in notes:
            note.touch()
        console.print(f"[green]Touched[/green] {len(notes)} note(s) — modified dates updated to today.")
        return

    if batch == "delete":
        if click.confirm(f"Delete {len(notes)} stale note(s)?", default=False):
            for note in notes:
                note.path.unlink()
            console.print(f"[red]Deleted[/red] {len(notes)} note(s).")
        else:
            console.print("[dim]Cancelled.[/dim]")
        return

    if interactive:
        _interactive_stale(notes, root, cfg)
        return

    if fmt == "json":
        data = [
            {
                "path": str(note.path.relative_to(root)),
                "title": note.title,
                "tags": note.tags,
                "status": note.status or "",
            }
            for note in notes
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if fmt == "plain":
        for note in notes:
            click.echo(str(note.path.relative_to(root)))
        return

    # rich
    from datetime import datetime
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Last modified", style="dim")

    for note in notes:
        mtime = note.path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        table.add_row(str(note.path.relative_to(root)), dt)

    console.print(table)
    console.print(f"[dim]{len(notes)} stale note(s) (>{threshold} days)[/dim]")


@click.command("preview")
@click.argument("title")
def cmd_preview(title: str) -> None:
    """Print a note's content to the terminal."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    syntax = Syntax(
        note.path.read_text(encoding="utf-8"),
        "markdown",
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
    )
    console.print(f"[bold]{note.path.relative_to(root)}[/bold]\n")
    console.print(syntax)


@click.command("pick")
@click.argument("query", required=False, default="")
def cmd_pick(query: str) -> None:
    """Fuzzy-pick a note and print its path (pipe-friendly)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.all_notes()
    if query:
        q = query.lower()
        notes = [n for n in notes if q in n.stem.lower() or q in n.title.lower()]

    notes = sorted(notes, key=lambda n: n.title)

    if not notes:
        console.print("[dim]No matches.[/dim]", err=True)
        raise SystemExit(1)

    if len(notes) == 1:
        click.echo(str(notes[0].path))
        return

    # Interactive selection via numbered list
    for i, note in enumerate(notes, 1):
        console.print(f"[dim]{i:3}.[/dim] {note.title}  [dim]{note.path.relative_to(root)}[/dim]")

    choice = click.prompt("\nPick", type=int)
    if 1 <= choice <= len(notes):
        click.echo(str(notes[choice - 1].path))
    else:
        console.print("[red]Invalid choice.[/red]", err=True)
        raise SystemExit(1)
