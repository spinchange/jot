"""jot rename / merge / split / dedupe / related"""

from __future__ import annotations

import re
from pathlib import Path

import click
from rich.console import Console

from jot.config import Config
from jot.vault import Vault

console = Console()


def _replace_resolved_wikilinks(text: str, vault: Vault, target_note, new_name: str) -> str:
    pattern = re.compile(r"\[\[([^\]|#\n]+?)(\|[^\]\n]+)?\]\]")

    def replace(match: re.Match[str]) -> str:
        link_target = match.group(1).strip()
        if not vault.resolves_to(link_target, target_note):
            return match.group(0)
        return f"[[{new_name}{match.group(2) or ''}]]"

    return pattern.sub(replace, text)


@click.command("rename")
@click.argument("old_title")
@click.argument("new_title")
@click.option("--dry-run", is_flag=True)
def cmd_rename(old_title: str, new_title: str, dry_run: bool) -> None:
    """Rename a note and update all inbound wikilinks."""
    # Validate new_title against characters illegal in Windows filenames.
    illegal_chars = set('<>:"/\\|?*') | {chr(c) for c in range(0x00, 0x20)}
    found = sorted({ch for ch in new_title if ch in illegal_chars}, key=ord)
    if found:
        readable = ", ".join(repr(ch) for ch in found)
        raise click.UsageError(
            f"Title contains characters not allowed in note filenames: {readable}. "
            "Remove < > : \" / \\ | ? * and ASCII control characters (0x00–0x1f)."
        )

    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    note = vault.resolve(old_title)
    if not note:
        raise click.ClickException(f"Note not found: {old_title!r}")

    new_stem = new_title.lower().replace(" ", "-")
    new_path = note.path.parent / f"{new_stem}.md"

    if new_path.exists():
        raise click.ClickException(f"A note already exists at {new_path.relative_to(root)}")

    # Find all notes that link to old_title
    bl = vault.backlinks(note)

    console.print(f"  Rename: [cyan]{note.path.relative_to(root)}[/cyan] → [cyan]{new_path.relative_to(root)}[/cyan]")
    if bl:
        console.print(f"  Update {len(bl)} backlink(s):")
        for src in bl:
            console.print(f"    [dim]{src.path.relative_to(root)}[/dim]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    # Update title frontmatter to match new name whenever the field exists,
    # then save before renaming (rename() moves the file, doesn't write data).
    if "title" in note._data:
        note._data["title"] = new_title
        note.save()
    note.path.rename(new_path)
    note.path = new_path

    # Update every inbound link that previously resolved to this note.
    for src in bl:
        text = src.path.read_text(encoding="utf-8")
        new_text = _replace_resolved_wikilinks(text, vault, note, new_title)
        if new_text != text:
            src.path.write_text(new_text, encoding="utf-8")

    console.print(f"\n[green]Renamed[/green] and updated {len(bl)} backlink(s).")


@click.command("merge")
@click.argument("source_title")
@click.argument("target_title")
@click.option("--dry-run", is_flag=True)
def cmd_merge(source_title: str, target_title: str, dry_run: bool) -> None:
    """Merge SOURCE into TARGET (appends content, redirects links, deletes source)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    src = vault.resolve(source_title)
    if not src:
        raise click.ClickException(f"Source not found: {source_title!r}")

    tgt = vault.resolve(target_title)
    if not tgt:
        raise click.ClickException(f"Target not found: {target_title!r}")

    if src.path == tgt.path:
        raise click.ClickException("Source and target are the same note.")

    bl = vault.backlinks(src)
    console.print(f"  Merge [cyan]{src.path.relative_to(root)}[/cyan] → [cyan]{tgt.path.relative_to(root)}[/cyan]")
    console.print(f"  Append {len(src.body.splitlines())} line(s) to target")
    console.print(f"  Redirect {len(bl)} backlink(s)")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    # Append source body to target
    with tgt.path.open("a", encoding="utf-8") as f:
        f.write(f"\n\n---\n\n*Merged from [[{src.title}]]:*\n\n{src.body}")

    # Redirect all backlinks pointing to source → target
    for link_src in bl:
        text = link_src.path.read_text(encoding="utf-8")
        pattern = re.compile(
            r"\[\[" + re.escape(source_title) + r"(\|[^\]]+)?\]\]",
            re.IGNORECASE,
        )
        text = pattern.sub(lambda m: f"[[{tgt.title}{m.group(1) or ''}]]", text)
        link_src.path.write_text(text, encoding="utf-8")

    src.path.unlink()
    console.print(f"\n[green]Merged[/green] and deleted {src.path.relative_to(root)}")


@click.command("split")
@click.argument("title")
@click.argument("heading")
@click.option("--dry-run", is_flag=True)
def cmd_split(title: str, heading: str, dry_run: bool) -> None:
    """Split a section (by heading text) out of a note into a new note."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    # Find the heading in the body
    lines = note.body.splitlines(keepends=True)
    heading_pattern = re.compile(r"^#{1,6}\s+" + re.escape(heading) + r"\s*$", re.IGNORECASE)

    split_line = None
    for i, line in enumerate(lines):
        if heading_pattern.match(line):
            split_line = i
            break

    if split_line is None:
        raise click.ClickException(f"Heading {heading!r} not found in {title!r}")

    # Find the end of the section (next same-or-higher-level heading, or EOF)
    _heading_match = re.match(r"^(#+)", lines[split_line])
    if not _heading_match:
        raise click.UsageError(
            f"Line {split_line} is not a heading: {lines[split_line]!r}"
        )
    heading_level = len(_heading_match.group(1))
    end_line = len(lines)
    for i in range(split_line + 1, len(lines)):
        m = re.match(r"^(#+)\s", lines[i])
        if m and len(m.group(1)) <= heading_level:
            end_line = i
            break

    section_lines = lines[split_line:end_line]
    remaining_lines = lines[:split_line] + lines[end_line:]

    new_stem = heading.lower().replace(" ", "-")
    new_path = root / f"{new_stem}.md"
    new_title_text = heading

    console.print(f"  Split section [cyan]{heading!r}[/cyan] ({len(section_lines)} lines) from [cyan]{note.path.relative_to(root)}[/cyan]")
    console.print(f"  New note: [cyan]{new_path.relative_to(root)}[/cyan]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    from datetime import date
    today = date.today().isoformat()
    new_path.write_text(
        f"---\ntitle: {new_title_text}\ndate: {today}\n---\n\n" + "".join(section_lines),
        encoding="utf-8",
    )

    # Replace section in original with a wikilink
    remaining_body = "".join(remaining_lines).rstrip("\n") + f"\n\n[[{new_title_text}]]\n"
    note.body = remaining_body
    note.save()

    console.print(f"\n[green]Split complete.[/green] Link added to original.")


@click.command("dedupe")
@click.option("--dry-run", is_flag=True)
def cmd_dedupe(dry_run: bool) -> None:
    """Find and report notes with duplicate titles or stems."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    # Group by normalized title
    by_title: dict[str, list] = {}
    for note in vault.all_notes():
        key = note.title.lower().strip()
        by_title.setdefault(key, []).append(note)

    dupes = {k: v for k, v in by_title.items() if len(v) > 1}

    if not dupes:
        console.print("[green]No duplicate titles found.[/green]")
        return

    for title_key, notes in sorted(dupes.items()):
        console.print(f"\n[yellow]Duplicate:[/yellow] {title_key!r}")
        for note in notes:
            console.print(f"  [dim]{note.path.relative_to(root)}[/dim]")

    console.print(f"\n[dim]{len(dupes)} duplicate group(s). Use [bold]jot merge[/bold] or [bold]jot rename[/bold] to resolve.[/dim]")


@click.command("related")
@click.argument("title")
@click.option("--limit", default=5, show_default=True)
def cmd_related(title: str, limit: int) -> None:
    """Show notes most related to a given note (shared tags + common links)."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root)

    note = vault.resolve(title)
    if not note:
        raise click.ClickException(f"Note not found: {title!r}")

    my_tags = set(t.lower() for t in note.tags)
    my_links = set(t.lower() for t in note.wikilink_targets)
    bl = {n.stem.lower() for n in vault.backlinks(note)}

    scores: dict[str, float] = {}
    for other in vault.all_notes():
        if other.path == note.path:
            continue
        other_tags = set(t.lower() for t in other.tags)
        other_links = set(t.lower() for t in other.wikilink_targets)

        score = (
            len(my_tags & other_tags) * 2      # shared tags (weighted)
            + len(my_links & other_links)       # shared outbound links
            + (1 if other.stem.lower() in bl else 0)  # links back to us
        )
        if score > 0:
            scores[other.stem] = score

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:limit]

    if not ranked:
        console.print("[dim]No related notes found.[/dim]")
        return

    for stem, score in ranked:
        related_note = vault.get(stem)
        if related_note:
            console.print(f"  [cyan]{related_note.path.relative_to(root)}[/cyan]  [dim]score {score}[/dim]")
