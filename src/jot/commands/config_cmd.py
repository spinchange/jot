"""jot config — show / init / path"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from jot.config import Config, CONFIG_FILE, CONFIG_DIR

console = Console()


@click.group("config")
def config_group():
    """Show or edit jot configuration."""


@config_group.command("show")
def config_show():
    """Print current configuration."""
    cfg = Config.load()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("vault", cfg.vault or "[dim](not set)[/dim]")
    table.add_row("editor", cfg.editor or "[dim](not set)[/dim]")
    table.add_row("noOpen", str(cfg.no_open))
    table.add_row("staleDays", str(cfg.stale_days))
    table.add_row("dashboardLimit", str(cfg.dashboard_limit))
    table.add_row("templates", cfg.templates or "[dim](not set)[/dim]")
    table.add_row("queries", cfg.queries or "[dim](not set)[/dim]")
    console.print(table)


@config_group.command("path")
def config_path():
    """Print the path to the config file."""
    console.print(str(CONFIG_FILE))


@config_group.command("init")
def config_init():
    """Interactive first-run setup."""
    cfg = Config.load()

    console.print("[bold]jot config init[/bold]\n")

    vault = click.prompt(
        "Vault path",
        default=cfg.vault or str(CONFIG_DIR / "vault"),
    )
    editor = click.prompt(
        "Editor command",
        default=cfg.editor or _default_editor(),
    )
    stale_days = click.prompt("Stale threshold (days)", default=cfg.stale_days, type=int)
    dashboard_limit = click.prompt(
        "Dashboard recent-notes limit", default=cfg.dashboard_limit, type=int
    )

    cfg.vault = vault
    cfg.editor = editor
    cfg.stale_days = stale_days
    cfg.dashboard_limit = dashboard_limit
    cfg.save()

    console.print(f"\n[green]Saved[/green] {CONFIG_FILE}")

    # Create vault dir if it doesn't exist
    import pathlib
    vp = pathlib.Path(vault).expanduser()
    if not vp.exists():
        if click.confirm(f"Create vault directory {vp}?", default=True):
            vp.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created[/green] {vp}")


def _default_editor() -> str:
    import os, shutil
    for candidate in ("code", "nvim", "vim", "nano", "notepad"):
        if shutil.which(candidate):
            return candidate
    return os.environ.get("EDITOR", "notepad")
