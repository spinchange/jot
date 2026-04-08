"""jot links / backlinks / unresolved / repair-links / create-unresolved / graph / orphans"""

from __future__ import annotations

import re
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from jot.config import Config
from jot.vault import Vault

console = Console()


@click.command("links")
@click.argument("title")
def cmd_links(title: str) -> None:
    """List all outbound wikilinks from a note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    links = note.wikilinks
    if not links:
        console.print("[dim]No outbound links.[/dim]")
        return

    for target, display in links:
        resolved = vault.resolve(target)
        status = "[green]✓[/green]" if resolved else "[red]✗[/red]"
        label = f"{target}" + (f" → {display}" if display else "")
        console.print(f"  {status}  {label}")

    console.print(f"\n[dim]{len(links)} link(s)[/dim]")


@click.command("backlinks")
@click.argument("title")
def cmd_backlinks(title: str) -> None:
    """List all notes that link to a given note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    bl = vault.backlinks(note)
    if not bl:
        console.print("[dim]No backlinks.[/dim]")
        return

    for src in sorted(bl, key=lambda n: n.title):
        console.print(f"  [cyan]{src.path.relative_to(root)}[/cyan]  [dim]{src.title}[/dim]")

    console.print(f"\n[dim]{len(bl)} backlink(s)[/dim]")


@click.command("unresolved")
def cmd_unresolved() -> None:
    """List all unresolved wikilinks in the vault."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    pairs = vault.unresolved_links()
    if not pairs:
        console.print("[green]No unresolved links.[/green]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("In note", style="cyan")
    table.add_column("Broken link", style="red")

    for note, link in sorted(pairs, key=lambda x: (str(x[0].path), x[1])):
        table.add_row(str(note.path.relative_to(root)), link)

    console.print(table)
    console.print(f"[dim]{len(pairs)} unresolved link(s)[/dim]")


@click.command("repair-links")
@click.argument("old_name")
@click.argument("new_name")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
def cmd_repair_links(old_name: str, new_name: str, dry_run: bool) -> None:
    """Replace all wikilinks from OLD_NAME to NEW_NAME across the vault."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    old_lower = old_name.lower()
    pattern = re.compile(
        r"\[\[" + re.escape(old_name) + r"(\|[^\]]+)?\]\]",
        re.IGNORECASE,
    )

    to_update = []
    for note in vault.all_notes():
        text = note.path.read_text(encoding="utf-8")
        new_text = pattern.sub(lambda m: f"[[{new_name}{m.group(1) or ''}]]", text)
        if new_text != text:
            console.print(f"  [cyan]{note.path.relative_to(root)}[/cyan]")
            to_update.append((note.path, text, new_text))

    updated = len(to_update)
    if not dry_run and to_update:
        snapshot = {path: original for path, original, _ in to_update}
        try:
            for path, _, new_text in to_update:
                path.write_text(new_text, encoding="utf-8")
        except Exception as exc:
            for path, original in snapshot.items():
                path.write_text(original, encoding="utf-8")
            raise click.ClickException("Operation failed — all changes have been rolled back.") from exc

    if updated == 0:
        console.print(f"[dim]No links to [[{old_name}]] found.[/dim]")
    elif dry_run:
        console.print(f"\n[yellow]Dry run:[/yellow] would update {updated} note(s).")
    else:
        console.print(f"\n[green]Updated[/green] {updated} note(s).")


@click.command("create-unresolved")
@click.option("--dry-run", is_flag=True)
def cmd_create_unresolved(dry_run: bool) -> None:
    """Create stub notes for every unresolved wikilink."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    from datetime import date

    pairs = vault.unresolved_links()
    # Deduplicate link names
    names = sorted({link for _, link in pairs})

    if not names:
        console.print("[green]No unresolved links — nothing to create.[/green]")
        return

    for name in names:
        stem = name.lower().replace(" ", "-")
        path = root / f"{stem}.md"
        console.print(f"  [cyan]{stem}.md[/cyan]")
        if not dry_run:
            today = date.today().isoformat()
            path.write_text(
                f"---\ntitle: {name}\ndate: {today}\nstatus: draft\n---\n\n# {name}\n",
                encoding="utf-8",
            )

    if dry_run:
        console.print(f"\n[yellow]Dry run:[/yellow] would create {len(names)} stub(s).")
    else:
        console.print(f"\n[green]Created[/green] {len(names)} stub note(s).")


@click.command("graph")
@click.option("--format", "fmt", default="mermaid", type=click.Choice(["mermaid"]), show_default=True)
def cmd_graph(fmt: str) -> None:
    """Output a link graph in Mermaid format."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    lines = ["graph TD"]
    for note in vault.all_notes():
        src_id = _node_id(note.stem)
        src_label = note.title
        lines.append(f'    {src_id}["{src_label}"]')
        for target in note.wikilink_targets:
            resolved = vault.resolve(target)
            if resolved:
                dst_id = _node_id(resolved.stem)
                lines.append(f"    {src_id} --> {dst_id}")

    click.echo("\n".join(lines))


def _node_id(stem: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", stem)


@click.command("orphans")
def cmd_orphans() -> None:
    """List notes with no inbound or outbound links."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    orph = vault.orphans()
    if not orph:
        console.print("[green]No orphans.[/green]")
        return

    for note in sorted(orph, key=lambda n: n.title):
        console.print(f"  [dim]{note.path.relative_to(root)}[/dim]")

    console.print(f"\n[dim]{len(orph)} orphan(s)[/dim]")
