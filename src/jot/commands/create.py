"""jot new / open / daily / weekly / monthly"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import click
from rich.console import Console

from jot.config import Config
from jot.vault import Vault
from jot.note import Note

console = Console()


def _open_in_editor(path: Path, cfg: Config) -> None:
    if cfg.no_open:
        return
    editor = cfg.editor
    if not editor:
        console.print(f"[dim]No editor configured. File at:[/dim] {path}")
        return
    try:
        subprocess.Popen([editor, str(path)])
    except FileNotFoundError:
        console.print(f"[yellow]Editor not found:[/yellow] {editor}")
        console.print(f"[dim]File at:[/dim] {path}")


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _create_note(path: Path, title: str | None = None, template_text: str | None = None) -> None:
    """Write a minimal note stub if the file doesn't exist."""
    if path.exists():
        return
    _ensure_dir(path)
    stem = path.stem
    heading = title or stem.replace("-", " ").title()
    if template_text:
        path.write_text(template_text, encoding="utf-8")
    else:
        today = date.today().isoformat()
        content = f"---\ntitle: {heading}\ndate: {today}\n---\n\n# {heading}\n"
        path.write_text(content, encoding="utf-8")


# ------------------------------------------------------------------ #
# Commands
# ------------------------------------------------------------------ #


@click.command("new")
@click.argument("title")
@click.option("--no-open", is_flag=True, help="Don't open in editor.")
def cmd_new(title: str, no_open: bool) -> None:
    """Create a new note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    existing = vault.resolve(title)
    if existing:
        console.print(f"[yellow]Already exists:[/yellow] {existing.path.relative_to(root)}")
        if not no_open:
            _open_in_editor(existing.path, cfg)
        return

    stem = title.lower().replace(" ", "-")
    path = root / f"{stem}.md"
    _create_note(path, title=title)
    console.print(f"[green]Created[/green] {path.relative_to(root)}")
    if not no_open:
        _open_in_editor(path, cfg)


@click.command("open")
@click.argument("title")
def cmd_open(title: str) -> None:
    """Open an existing note (or create it if absent)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    note = vault.resolve(title)
    if note:
        path = note.path
    else:
        stem = title.lower().replace(" ", "-")
        path = root / f"{stem}.md"
        _create_note(path, title=title)
        console.print(f"[green]Created[/green] {path.relative_to(root)}")

    _open_in_editor(path, cfg)


@click.command("daily")
@click.argument("date_str", required=False, metavar="[DATE]")
@click.option("--no-open", is_flag=True)
def cmd_daily(date_str: str | None, no_open: bool) -> None:
    """Open today's daily note (or a specific date: YYYY-MM-DD)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            raise click.BadParameter(f"Date must be YYYY-MM-DD, got: {date_str}")
    else:
        d = date.today()

    path = vault.daily_path(d)
    if not path.exists():
        _ensure_dir(path)
        heading = f"Daily Note — {d.isoformat()}"
        path.write_text(
            f"---\ndate: {d.isoformat()}\ntags:\n  - daily\n---\n\n# {heading}\n\n## Notes\n\n## Tasks\n",
            encoding="utf-8",
        )
        console.print(f"[green]Created[/green] {path.relative_to(root)}")
    else:
        console.print(f"[dim]Opening[/dim] {path.relative_to(root)}")

    if not no_open:
        _open_in_editor(path, cfg)


@click.command("weekly")
@click.argument("date_str", required=False, metavar="[DATE]")
@click.option("--no-open", is_flag=True)
def cmd_weekly(date_str: str | None, no_open: bool) -> None:
    """Open this week's weekly note (or a specific date: YYYY-MM-DD)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            raise click.BadParameter(f"Date must be YYYY-MM-DD, got: {date_str}")
    else:
        d = date.today()

    path = vault.weekly_path(d)
    iso = d.isocalendar()
    week_label = f"{iso.year}-W{iso.week:02d}"

    if not path.exists():
        _ensure_dir(path)
        path.write_text(
            f"---\ndate: {d.isoformat()}\ntags:\n  - weekly\n---\n\n# Week {week_label}\n\n## Goals\n\n## Review\n",
            encoding="utf-8",
        )
        console.print(f"[green]Created[/green] {path.relative_to(root)}")
    else:
        console.print(f"[dim]Opening[/dim] {path.relative_to(root)}")

    if not no_open:
        _open_in_editor(path, cfg)


@click.command("monthly")
@click.argument("date_str", required=False, metavar="[DATE]")
@click.option("--no-open", is_flag=True)
def cmd_monthly(date_str: str | None, no_open: bool) -> None:
    """Open this month's monthly note (or a specific date: YYYY-MM-DD)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            raise click.BadParameter(f"Date must be YYYY-MM-DD, got: {date_str}")
    else:
        d = date.today()

    path = vault.monthly_path(d)
    month_label = d.strftime("%B %Y")

    if not path.exists():
        _ensure_dir(path)
        path.write_text(
            f"---\ndate: {d.isoformat()}\ntags:\n  - monthly\n---\n\n# {month_label}\n\n## Goals\n\n## Review\n",
            encoding="utf-8",
        )
        console.print(f"[green]Created[/green] {path.relative_to(root)}")
    else:
        console.print(f"[dim]Opening[/dim] {path.relative_to(root)}")

    if not no_open:
        _open_in_editor(path, cfg)
