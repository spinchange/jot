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
@click.option(
    "--ssg",
    type=click.Choice(["hugo", "eleventy", "jekyll"]),
    default=None,
    help="SSG link style: hugo=no extension, eleventy/jekyll=.html extension. Default: .md links.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["markdown", "html"]),
    default="markdown",
    show_default=True,
    help="Output format: markdown (SSG-ready) or html (standalone pages, requires jot[html]).",
)
def cmd_publish(output: str, clean: bool, dry_run: bool, ssg: str | None, fmt: str) -> None:
    """Transform wikilinks to relative links and write to OUTPUT dir.

    The vault source is never modified.
    Quartz users: wikilinks are natively supported — you don't need this command.
    Hugo users: run with --ssg hugo before building.
    Eleventy/Jekyll users: run with --ssg eleventy or --ssg jekyll before building.
    """
    if fmt == "html" and ssg is not None:
        raise click.UsageError("--ssg has no effect with --format html (HTML output always uses .html links).")

    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    out_dir = Path(output).expanduser().resolve()

    if clean and out_dir.exists() and not dry_run:
        shutil.rmtree(out_dir)
        console.print(f"[yellow]Cleaned[/yellow] {out_dir}")

    notes = vault.all_notes()

    if fmt == "html":
        _publish_html(notes, vault, root, out_dir, dry_run)
        return

    # markdown output (default)
    transformed = 0
    copied = 0

    for note in notes:
        rel = note.path.relative_to(root)
        out_path = out_dir / rel

        text = note.path.read_text(encoding="utf-8")
        new_text = _transform_wikilinks(text, note, vault, root, ssg=ssg)

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


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.6}}
a{{color:#0969da}}
pre{{background:#f6f8fa;padding:1rem;overflow:auto;border-radius:4px}}
code{{font-family:ui-monospace,monospace;font-size:.9em}}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _publish_html(notes: list, vault: Vault, root: Path, out_dir: Path, dry_run: bool) -> None:
    """Render notes to standalone HTML files."""
    try:
        import markdown as md_lib
    except ImportError:
        raise click.ClickException(
            "HTML export requires the 'markdown' package. Install with: pip install 'jot[html]'"
        )

    count = 0
    for note in notes:
        transformed_body = _transform_wikilinks(note.body, note, vault, root, ssg="eleventy")
        html_body = md_lib.markdown(transformed_body, extensions=["tables", "fenced_code"])
        html = _HTML_TEMPLATE.format(title=note.title, body=html_body)

        out_path = out_dir / note.path.relative_to(root).with_suffix(".html")
        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
        count += 1

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would write {count} HTML file(s) to {out_dir}")
    else:
        console.print(f"[green]Published[/green] {count} HTML file(s) → {out_dir}")


def _transform_wikilinks(text: str, note, vault: Vault, root: Path, ssg: str | None = None) -> str:
    def replace(m: re.Match) -> str:
        target_name = m.group(1).strip()
        display = m.group(2)

        resolved = vault.resolve(target_name)
        if resolved is None:
            # Unresolved — leave as plain text with display or target name
            return display or target_name

        # Compute relative path from note to resolved note
        try:
            rel = _relative_link(note.path, resolved.path, ssg=ssg)
        except ValueError:
            rel = str(resolved.path)

        link_text = display or resolved.title
        return f"[{link_text}]({rel})"

    return _WIKILINK_RE.sub(replace, text)


def _relative_link(from_path: Path, to_path: Path, ssg: str | None = None) -> str:
    """Compute a relative URL from from_path's directory to to_path.

    ssg=None      → .md extension (default, works with most SSGs that accept .md links)
    ssg="hugo"    → no extension (Hugo directory-bundle style)
    ssg="eleventy"
    ssg="jekyll"  → .html extension
    """
    rel = Path(os.path.relpath(to_path, from_path.parent))
    if ssg == "hugo":
        return rel.with_suffix("").as_posix()
    if ssg in ("eleventy", "jekyll"):
        return rel.with_suffix(".html").as_posix()
    return rel.as_posix()
