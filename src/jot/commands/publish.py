"""jot publish — transform wikilinks to relative links for SSG output."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import click
from rich.console import Console

from jot.config import Config
from jot.note import _WIKILINK_RE
from jot.vault import Vault

console = Console()


@click.command("publish")
@click.option("--output", "-o", default="./dist", show_default=True, metavar="DIR", help="Output directory.")
@click.option("--clean", is_flag=True, help="Delete output directory before publishing.")
@click.option("--dry-run", is_flag=True)
def cmd_publish(output: str, clean: bool, dry_run: bool) -> None:
    """Transform wikilinks to relative markdown links and write to OUTPUT dir.

    The vault source is never modified.
    Quartz users: wikilinks are natively supported — you don't need this command.
    Hugo/Eleventy/Jekyll users: run this before building your site.
    """
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    out_dir = Path(output).expanduser().resolve()

    if clean and out_dir.exists() and not dry_run:
        shutil.rmtree(out_dir)
        console.print(f"[yellow]Cleaned[/yellow] {out_dir}")

    notes = vault.all_notes()
    transformed = 0
    copied = 0

    for note in notes:
        rel = note.path.relative_to(root)
        out_path = out_dir / rel

        text = note.path.read_text(encoding="utf-8")
        new_text = _transform_wikilinks(text, note, vault, root)

        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(new_text, encoding="utf-8")

        if new_text != text:
            transformed += 1
        copied += 1

    # Copy non-.md files (assets etc.) unchanged
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix == ".md":
            continue
        rel = path.relative_to(root)
        out_path = out_dir / rel
        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out_path)

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would write {copied} note(s) ({transformed} with wikilink transforms) to {out_dir}")
    else:
        console.print(f"[green]Published[/green] {copied} note(s) ({transformed} transformed) → {out_dir}")


def _transform_wikilinks(text: str, note, vault: Vault, root: Path) -> str:
    def replace(m: re.Match) -> str:
        target_name = m.group(1).strip()
        display = m.group(2)

        resolved = vault.resolve(target_name)
        if resolved is None:
            # Unresolved — leave as plain text with display or target name
            return display or target_name

        # Compute relative path from note to resolved note
        try:
            rel = _relative_link(note.path, resolved.path)
        except ValueError:
            rel = str(resolved.path)

        link_text = display or resolved.title
        return f"[{link_text}]({rel})"

    return _WIKILINK_RE.sub(replace, text)


def _relative_link(from_path: Path, to_path: Path) -> str:
    """Compute a relative URL from from_path's directory to to_path."""
    return Path(os.path.relpath(to_path, from_path.parent)).as_posix()
