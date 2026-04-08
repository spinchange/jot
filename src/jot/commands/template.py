"""jot template / query"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import click
from rich.console import Console

from jot.config import Config
from jot.vault import Vault

console = Console()


# ------------------------------------------------------------------ #
# template
# ------------------------------------------------------------------ #


@click.group("template")
def template_group() -> None:
    """Manage and apply note templates."""


@template_group.command("list")
def template_list() -> None:
    """List available templates."""
    cfg = Config.load()
    root = cfg.require_vault()
    templates_dir = Path(cfg.templates) if cfg.templates else root / "templates"

    if not templates_dir.exists():
        console.print("[dim]No templates directory found.[/dim]")
        return

    tmpl_files = sorted(templates_dir.glob("*.md"))
    if not tmpl_files:
        console.print("[dim]No templates found.[/dim]")
        return

    for f in tmpl_files:
        console.print(f"  [cyan]{f.stem}[/cyan]")


@template_group.command("apply")
@click.argument("template_name")
@click.argument("note_title")
@click.option("--no-open", is_flag=True)
def template_apply(template_name: str, note_title: str, no_open: bool) -> None:
    """Create a note from a template."""
    cfg = Config.load()
    root = cfg.require_vault()
    templates_dir = Path(cfg.templates) if cfg.templates else root / "templates"

    tmpl_path = templates_dir / f"{template_name}.md"
    if not tmpl_path.exists():
        # Try case-insensitive
        matches = [f for f in templates_dir.glob("*.md") if f.stem.lower() == template_name.lower()]
        if not matches:
            raise click.ClickException(f"Template not found: {template_name!r}")
        tmpl_path = matches[0]

    tmpl_text = tmpl_path.read_text(encoding="utf-8")

    # Substitute template variables: {{title}}, {{date}}, {{year}}, {{month}}, {{day}}
    today = date.today()
    stem = note_title.lower().replace(" ", "-")
    tmpl_text = _substitute(tmpl_text, {
        "title": note_title,
        "date": today.isoformat(),
        "year": str(today.year),
        "month": f"{today.month:02d}",
        "day": f"{today.day:02d}",
        "stem": stem,
    })

    vault = Vault.load(root, ignore=set(cfg.ignore_folders))
    existing = vault.resolve(note_title)
    if existing:
        console.print(f"[yellow]Already exists:[/yellow] {existing.path.relative_to(root)}")
        return

    path = root / f"{stem}.md"
    path.write_text(tmpl_text, encoding="utf-8")
    console.print(f"[green]Created[/green] {path.relative_to(root)} from template {template_name!r}")

    if not no_open and cfg.editor:
        import subprocess
        subprocess.Popen([cfg.editor, str(path)])


@template_group.command("show")
@click.argument("template_name")
def template_show(template_name: str) -> None:
    """Print a template's content."""
    cfg = Config.load()
    root = cfg.require_vault()
    templates_dir = Path(cfg.templates) if cfg.templates else root / "templates"
    tmpl_path = templates_dir / f"{template_name}.md"
    if not tmpl_path.exists():
        raise click.ClickException(f"Template not found: {template_name!r}")

    from rich.syntax import Syntax
    console.print(Syntax(tmpl_path.read_text(encoding="utf-8"), "markdown", theme="monokai"))


def _substitute(text: str, vars: dict) -> str:
    def replacer(m):
        key = m.group(1).strip()
        return vars.get(key, m.group(0))
    return re.sub(r"\{\{(\w+)\}\}", replacer, text)


# ------------------------------------------------------------------ #
# query
# ------------------------------------------------------------------ #


@click.group("query")
def query_group() -> None:
    """Run saved queries against the vault."""


@query_group.command("list")
def query_list() -> None:
    """List saved queries."""
    cfg = Config.load()
    queries = _load_queries(cfg)
    if not queries:
        console.print("[dim]No saved queries.[/dim]")
        return
    for name, q in queries.items():
        console.print(f"  [cyan]{name}[/cyan]  [dim]{q.get('description', '')}[/dim]")


@query_group.command("run")
@click.argument("name")
def query_run(name: str) -> None:
    """Run a saved query by name."""
    cfg = Config.load()
    queries = _load_queries(cfg)
    if name not in queries:
        raise click.ClickException(f"Query not found: {name!r}")

    q = queries[name]
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))

    notes = vault.all_notes()

    if "tag" in q:
        tag_lower = q["tag"].lower()
        notes = [n for n in notes if tag_lower in [t.lower() for t in n.tags]]
    if "status" in q:
        notes = [n for n in notes if n.status == q["status"]]
    if "search" in q:
        import re as _re
        pattern = _re.compile(_re.escape(q["search"]), _re.IGNORECASE)
        notes = [n for n in notes if pattern.search(n.body) or pattern.search(n.title)]

    notes = sorted(notes, key=lambda n: n.title)
    for note in notes:
        console.print(f"  [cyan]{note.path.relative_to(root)}[/cyan]  [dim]{note.title}[/dim]")
    console.print(f"\n[dim]{len(notes)} result(s)[/dim]")


@query_group.command("save")
@click.argument("name")
@click.option("--tag", default=None)
@click.option("--status", default=None)
@click.option("--search", default=None)
@click.option("--description", default="")
def query_save(name: str, tag: str | None, status: str | None, search: str | None, description: str) -> None:
    """Save a query for later reuse."""
    cfg = Config.load()
    queries = _load_queries(cfg)
    q: dict = {}
    if tag:
        q["tag"] = tag
    if status:
        q["status"] = status
    if search:
        q["search"] = search
    if description:
        q["description"] = description

    queries[name] = q
    _save_queries(cfg, queries)
    console.print(f"[green]Saved query[/green] {name!r}")


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
