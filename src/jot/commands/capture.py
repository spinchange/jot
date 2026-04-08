"""jot capture — append timestamped bullet to inbox or daily note."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from jot.config import Config
from jot.vault import Vault

console = Console()


@click.command("capture")
@click.argument("text", nargs=-1, required=False)
@click.option("--daily", "-d", "use_daily", is_flag=True, help="Append to today's daily note instead of inbox.")
@click.option("--inbox", "-i", "use_inbox", is_flag=True, help="Append to inbox.md (default).")
def cmd_capture(text: tuple[str, ...], use_daily: bool, use_inbox: bool) -> None:
    """Append a timestamped bullet to inbox.md (or today's daily note with --daily).

    If TEXT is omitted, reads from stdin.
    """
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    if text:
        content = " ".join(text)
    else:
        content = click.get_text_stream("stdin").read().strip()

    if not content:
        raise click.UsageError("Nothing to capture.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    bullet = f"- [{now}] {content}\n"

    if use_daily:
        path = vault.daily_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            today = datetime.today().strftime("%Y-%m-%d")
            path.write_text(
                f"---\ndate: {today}\ntags:\n  - daily\n---\n\n# Daily Note — {today}\n\n## Notes\n\n## Tasks\n",
                encoding="utf-8",
            )
        _append(path, bullet)
        console.print(f"[green]Captured[/green] → {path.relative_to(root)}")
    else:
        path = vault.inbox
        if not path.exists():
            path.write_text("# Inbox\n\n", encoding="utf-8")
        _append(path, bullet)
        console.print(f"[green]Captured[/green] → inbox.md")


def _append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text)
