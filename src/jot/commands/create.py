"""jot new / open / daily / weekly / monthly"""

from __future__ import annotations

import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import click
from rich.console import Console

from jot.config import Config
from jot.vault import Vault
from jot.note import Note

console = Console()

_DAILY_TEMPLATE = (
    "---\n"
    "title: {heading}\n"
    "tags:\n"
    "  - daily\n"
    "author: {author}\n"
    "hostname: {hostname}\n"
    "date: {date}\n"
    "status: draft\n"
    "status_log:\n"
    "  - {status_entry}\n"
    "---\n"
    "\n"
    "# {heading}\n"
    "\n"
    "## Notes\n"
    "\n"
    "## Tasks\n"
)

_WEEKLY_TEMPLATE = (
    "---\n"
    "title: {heading}\n"
    "tags:\n"
    "  - weekly\n"
    "author: {author}\n"
    "hostname: {hostname}\n"
    "date: {date}\n"
    "status: draft\n"
    "status_log:\n"
    "  - {status_entry}\n"
    "---\n"
    "\n"
    "# {heading}\n"
    "\n"
    "## Goals\n"
    "\n"
    "## Review\n"
)

_MONTHLY_TEMPLATE = (
    "---\n"
    "title: {heading}\n"
    "tags:\n"
    "  - monthly\n"
    "author: {author}\n"
    "hostname: {hostname}\n"
    "date: {date}\n"
    "status: draft\n"
    "status_log:\n"
    "  - {status_entry}\n"
    "---\n"
    "\n"
    "# {heading}\n"
    "\n"
    "## Goals\n"
    "\n"
    "## Review\n"
)


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


def _create_note(path: Path, title: str | None = None, template_text: str | None = None, cfg: Config | None = None) -> None:
    """Write a canonical note stub if the file doesn't exist."""
    if path.exists():
        return
    _ensure_dir(path)
    stem = path.stem
    heading = title or stem.replace("-", " ").title()
    if template_text:
        path.write_text(template_text, encoding="utf-8")
    else:
        if cfg is None:
            cfg = Config.load()
        today = date.today().isoformat()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        author = cfg.resolve_author()
        hostname = cfg.resolve_hostname()
        status_entry = f"draft · {ts} · {hostname} · {author}"
        content = (
            f"---\n"
            f"title: {heading}\n"
            f"tags: []\n"
            f"author: {author}\n"
            f"hostname: {hostname}\n"
            f"date: {today}\n"
            f"status: draft\n"
            f"status_log:\n"
            f"  - {status_entry}\n"
            f"---\n\n# {heading}\n"
        )
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
    _create_note(path, title=title, cfg=cfg)
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
        _create_note(path, title=title, cfg=cfg)
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
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        author = cfg.resolve_author()
        hostname = cfg.resolve_hostname()
        status_entry = f"draft · {ts} · {hostname} · {author}"
        path.write_text(
            _DAILY_TEMPLATE.format(
                heading=heading,
                author=author,
                hostname=hostname,
                date=d.isoformat(),
                status_entry=status_entry,
            ),
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
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        author = cfg.resolve_author()
        hostname = cfg.resolve_hostname()
        status_entry = f"draft · {ts} · {hostname} · {author}"
        heading = f"Week {week_label}"
        path.write_text(
            _WEEKLY_TEMPLATE.format(
                heading=heading,
                author=author,
                hostname=hostname,
                date=d.isoformat(),
                status_entry=status_entry,
            ),
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
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        author = cfg.resolve_author()
        hostname = cfg.resolve_hostname()
        status_entry = f"draft · {ts} · {hostname} · {author}"
        path.write_text(
            _MONTHLY_TEMPLATE.format(
                heading=month_label,
                author=author,
                hostname=hostname,
                date=d.isoformat(),
                status_entry=status_entry,
            ),
            encoding="utf-8",
        )
        console.print(f"[green]Created[/green] {path.relative_to(root)}")
    else:
        console.print(f"[dim]Opening[/dim] {path.relative_to(root)}")

    if not no_open:
        _open_in_editor(path, cfg)
