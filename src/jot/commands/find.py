"""jot list / search / find / pick / recent / stale / preview"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich import box

from jot.config import Config
from jot.vault import Vault

console = Console()


@click.command("list")
@click.option("--tag", "-t", default=None, help="Filter by tag.")
@click.option("--folder", "-f", default=None, help="Filter by subfolder.")
@click.option("--status", "-s", default=None, help="Filter by frontmatter status.")
def cmd_list(tag: str | None, folder: str | None, status: str | None) -> None:
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
        console.print("[dim]No notes found.[/dim]")
        return

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


@click.command("search")
@click.argument("query")
@click.option("--case-sensitive", is_flag=True)
def cmd_search(query: str, case_sensitive: bool) -> None:
    """Full-text search across all notes."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    results = vault.search(query, case_sensitive=case_sensitive)
    results = sorted(results, key=lambda n: n.title)

    if not results:
        console.print("[dim]No results.[/dim]")
        return

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
def cmd_recent(n: int) -> None:
    """Show the N most recently modified notes."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.recent(n)

    if not notes:
        console.print("[dim]No notes.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Modified", style="dim")

    from datetime import datetime
    for note in notes:
        mtime = note.path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(str(note.path.relative_to(root)), dt)

    console.print(table)


@click.command("stale")
@click.option("--days", default=None, type=int, help="Override stale threshold (days).")
def cmd_stale(days: int | None) -> None:
    """List notes not modified recently."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    threshold = days if days is not None else cfg.stale_days
    notes = vault.stale(threshold)

    if not notes:
        console.print(f"[dim]No stale notes (threshold: {threshold} days).[/dim]")
        return

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
