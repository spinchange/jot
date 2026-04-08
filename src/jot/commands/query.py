"""jot query — full-featured query DSL for vault search."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import click
from rich.console import Console
from rich.table import Table
from rich import box

from jot.config import Config
from jot.vault import Vault
from jot.note import Note

console = Console()

FormatChoice = Literal["rich", "plain", "json"]


# ------------------------------------------------------------------ #
# Shared rendering
# ------------------------------------------------------------------ #


def _render_notes(notes: list[Note], root: Path, fmt: FormatChoice) -> None:
    """Render query results in the requested output format."""
    if fmt == "json":
        data = [
            {
                "path": str(note.path.relative_to(root)),
                "title": note.title,
                "tags": note.tags,
                "status": note.status or "",
            }
            for note in notes
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if fmt == "plain":
        for note in notes:
            click.echo(str(note.path.relative_to(root)))
        return

    # rich
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Note", style="cyan")
    table.add_column("Tags", style="dim")
    table.add_column("Status", style="dim")

    for note in notes:
        rel = str(note.path.relative_to(root))
        tags_str = " ".join(f"#{t}" for t in note.tags[:5])
        table.add_row(rel, tags_str, note.status or "")

    console.print(table)
    console.print(f"[dim]{len(notes)} result(s)[/dim]")


# ------------------------------------------------------------------ #
# Core filter + sort logic (shared by run / exec)
# ------------------------------------------------------------------ #


def _apply_filters(
    notes: list[Note],
    root: Path,
    tag: str | None,
    status: str | None,
    search: str | None,
    folder: str | None,
    has_link: str | None,
) -> list[Note]:
    if tag:
        tag_lower = tag.lower()
        notes = [n for n in notes if tag_lower in [t.lower() for t in n.tags]]
    if status:
        notes = [n for n in notes if n.status == status]
    if search:
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        notes = [n for n in notes if pattern.search(n.title) or pattern.search(n.body)]
    if folder:
        folder_lower = folder.lower()
        notes = [n for n in notes if folder_lower in str(n.path.relative_to(root)).lower()]
    if has_link:
        link_lower = has_link.lower()
        notes = [n for n in notes if any(link_lower in t.lower() for t in n.wikilink_targets)]
    return notes


def _apply_sort(notes: list[Note], root: Path, sort: str) -> list[Note]:
    if sort == "title":
        return sorted(notes, key=lambda n: n.title.lower())
    if sort == "date":
        return sorted(notes, key=lambda n: n.path.stat().st_mtime, reverse=True)
    # path (default)
    return sorted(notes, key=lambda n: str(n.path.relative_to(root)))


# ------------------------------------------------------------------ #
# Saved queries persistence
# ------------------------------------------------------------------ #


def _queries_path(cfg: Config) -> Path:
    if cfg.queries:
        return Path(cfg.queries)
    from jot.config import CONFIG_DIR
    return CONFIG_DIR / "queries.json"


def _load_queries(cfg: Config) -> dict:
    path = _queries_path(cfg)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_queries(cfg: Config, queries: dict) -> None:
    path = _queries_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queries, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ #
# query group
# ------------------------------------------------------------------ #


@click.group("query")
def query_group() -> None:
    """Run and manage structured vault queries."""


@query_group.command("run")
@click.option("--tag", "-t", default=None, help="Filter by tag.")
@click.option("--status", "-s", default=None, help="Filter by frontmatter status.")
@click.option("--search", default=None, help="Full-text search term.")
@click.option("--folder", "-f", default=None, help="Filter by subfolder.")
@click.option("--has-link", default=None, help="Only notes linking to TARGET.")
@click.option("--limit", "-n", default=None, type=int, help="Cap result count.")
@click.option(
    "--sort",
    type=click.Choice(["title", "date", "path"]),
    default="path",
    show_default=True,
    help="Sort order.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "plain", "json"]),
    default="rich",
    show_default=True,
    help="Output format.",
)
def query_run(
    tag: str | None,
    status: str | None,
    search: str | None,
    folder: str | None,
    has_link: str | None,
    limit: int | None,
    sort: str,
    fmt: FormatChoice,
) -> None:
    """Run an ad-hoc query against the vault."""
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.all_notes()
    notes = _apply_filters(notes, root, tag, status, search, folder, has_link)
    notes = _apply_sort(notes, root, sort)

    if limit is not None:
        notes = notes[:limit]

    if not notes:
        if fmt == "rich":
            console.print("[dim]No results.[/dim]")
        elif fmt == "json":
            click.echo("[]")
        return

    _render_notes(notes, root, fmt)


@query_group.command("save")
@click.argument("name")
@click.option("--tag", "-t", default=None)
@click.option("--status", "-s", default=None)
@click.option("--search", default=None)
@click.option("--folder", "-f", default=None)
@click.option("--has-link", default=None)
@click.option("--limit", "-n", default=None, type=int)
@click.option(
    "--sort",
    type=click.Choice(["title", "date", "path"]),
    default=None,
)
@click.option("--description", default="")
def query_save(
    name: str,
    tag: str | None,
    status: str | None,
    search: str | None,
    folder: str | None,
    has_link: str | None,
    limit: int | None,
    sort: str | None,
    description: str,
) -> None:
    """Save a named query for later reuse."""
    cfg = Config.load()
    queries = _load_queries(cfg)

    q: dict = {}
    if tag:
        q["tag"] = tag
    if status:
        q["status"] = status
    if search:
        q["search"] = search
    if folder:
        q["folder"] = folder
    if has_link:
        q["has_link"] = has_link
    if limit is not None:
        q["limit"] = limit
    if sort:
        q["sort"] = sort
    if description:
        q["description"] = description

    queries[name] = q
    _save_queries(cfg, queries)
    console.print(f"[green]Saved query[/green] {name!r}")


@query_group.command("ls")
def query_ls() -> None:
    """List saved queries."""
    cfg = Config.load()
    queries = _load_queries(cfg)
    if not queries:
        console.print("[dim]No saved queries.[/dim]")
        return
    for name, q in queries.items():
        desc = q.get("description", "")
        parts = []
        for k in ("tag", "status", "search", "folder", "has_link", "limit", "sort"):
            if k in q:
                parts.append(f"{k}={q[k]!r}")
        summary = ", ".join(parts)
        console.print(f"  [cyan]{name}[/cyan]  [dim]{desc}[/dim]  [dim dim]{summary}[/dim dim]")


@query_group.command("exec")
@click.argument("name")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "plain", "json"]),
    default=None,
    help="Override saved query output format.",
)
def query_exec(name: str, fmt: FormatChoice | None) -> None:
    """Run a saved query by name."""
    cfg = Config.load()
    queries = _load_queries(cfg)
    if name not in queries:
        raise click.ClickException(f"Query not found: {name!r}")

    q = queries[name]
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.all_notes()
    notes = _apply_filters(
        notes,
        root,
        tag=q.get("tag"),
        status=q.get("status"),
        search=q.get("search"),
        folder=q.get("folder"),
        has_link=q.get("has_link"),
    )

    sort = q.get("sort", "path")
    notes = _apply_sort(notes, root, sort)

    limit = q.get("limit")
    if limit is not None:
        notes = notes[:limit]

    effective_fmt: FormatChoice = fmt or "rich"

    if not notes:
        if effective_fmt == "rich":
            console.print("[dim]No results.[/dim]")
        elif effective_fmt == "json":
            click.echo("[]")
        return

    _render_notes(notes, root, effective_fmt)
