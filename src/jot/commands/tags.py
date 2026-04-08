"""jot tags / props"""

from __future__ import annotations

from datetime import datetime
import click
from rich.console import Console
from rich.table import Table
from rich import box

from jot.config import Config
from jot.vault import Vault

console = Console()


@click.command("tags")
@click.argument("title", required=False)
@click.option("--all", "show_all", is_flag=True, help="List all tags vault-wide with counts.")
def cmd_tags(title: str | None, show_all: bool) -> None:
    """Show tags for a note, or list all tags vault-wide."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    if show_all or not title:
        # Vault-wide tag index
        tag_counts: dict[str, int] = {}
        for note in vault.all_notes():
            for tag in note.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            console.print("[dim]No tags found.[/dim]")
            return

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Tag", style="cyan")
        table.add_column("Count", justify="right", style="dim")

        for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0])):
            table.add_row(f"#{tag}", str(count))

        console.print(table)
        console.print(f"[dim]{len(tag_counts)} unique tag(s)[/dim]")
        return

    # Single note
    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    tags = note.tags
    if not tags:
        console.print("[dim]No tags.[/dim]")
        return

    for tag in tags:
        console.print(f"  [cyan]#{tag}[/cyan]")


# ------------------------------------------------------------------ #
# props
# ------------------------------------------------------------------ #


@click.group("props")
def props_group() -> None:
    """Show or edit frontmatter properties of a note."""


@props_group.command("show")
@click.argument("title")
def props_show(title: str) -> None:
    """Show all frontmatter fields for a note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    if not note._data:
        console.print("[dim]No frontmatter.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column(style="bold cyan")
    table.add_column()

    for k, v in note._data.items():
        table.add_row(k, str(v))

    console.print(table)


@props_group.command("set")
@click.argument("title")
@click.argument("key")
@click.argument("value")
def props_set(title: str, key: str, value: str) -> None:
    """Set a frontmatter field on a note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    # Attempt to coerce common types
    coerced = _coerce(value)
    note.set_prop(key, coerced)

    if key == "status":
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        hostname = cfg.resolve_hostname()
        author = cfg.resolve_author()
        note.append_status_log(f"{coerced} · {ts} · {hostname} · {author}")

    note.save()
    console.print(f"[green]Set[/green] {key} = {coerced!r}")


@props_group.command("unset")
@click.argument("title")
@click.argument("key")
def props_unset(title: str, key: str) -> None:
    """Remove a frontmatter field from a note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    if note.unset_prop(key):
        note.save()
        console.print(f"[green]Removed[/green] {key}")
    else:
        console.print(f"[dim]Field not present: {key}[/dim]")


@props_group.command("add")
@click.argument("title")
@click.argument("key")
@click.argument("value")
def props_add(title: str, key: str, value: str) -> None:
    """Append a value to a list frontmatter field (creates list if needed)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    existing = note.get_prop(key)
    if existing is None:
        note.set_prop(key, [value])
    elif isinstance(existing, list):
        existing.append(value)
    else:
        note.set_prop(key, [existing, value])

    note.save()
    console.print(f"[green]Added[/green] {value!r} to {key}")


@props_group.command("remove")
@click.argument("title")
@click.argument("key")
@click.argument("value")
def props_remove(title: str, key: str, value: str) -> None:
    """Remove a value from a list frontmatter field."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    existing = note.get_prop(key)
    if isinstance(existing, list) and value in existing:
        existing.remove(value)
        note.save()
        console.print(f"[green]Removed[/green] {value!r} from {key}")
    else:
        console.print(f"[dim]{value!r} not found in {key}[/dim]")


def _coerce(value: str):
    """Try to parse value as int, float, bool, or leave as str."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
