"""MCP server — exposes jot vault operations to AI models via the MCP protocol."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
    _mcp = FastMCP("jot")
    _MCP_AVAILABLE = True
except ImportError:
    _mcp = None  # type: ignore[assignment]
    _MCP_AVAILABLE = False

from jot.config import Config
from jot.vault import Vault
from jot import frontmatter as fm


def _tool(fn):  # type: ignore[return]
    """Decorator: register as MCP tool only when mcp is available."""
    if _MCP_AVAILABLE:
        return _mcp.tool()(fn)
    return fn


def _load_vault() -> tuple[Vault, Path]:
    cfg = Config.load()
    root = cfg.require_vault()
    vault = Vault.load(root, ignore=set(cfg.ignore_folders))
    return vault, root


# ------------------------------------------------------------------ #
# Tools
# ------------------------------------------------------------------ #


@_tool
def vault_search(query: str) -> list[dict[str, Any]]:
    """Full-text search across all notes.

    Returns a list of dicts with keys: path, title, tags, status, snippet.
    The snippet is the first line of the body that matches the query.
    """
    vault, root = _load_vault()
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []
    for note in vault.all_notes():
        if not (pattern.search(note.title) or pattern.search(note.body)):
            continue
        # Find first matching line for snippet
        snippet = ""
        for line in note.body.splitlines():
            if pattern.search(line):
                snippet = line.strip()
                break
        results.append({
            "path": str(note.path.relative_to(root)),
            "title": note.title,
            "tags": note.tags,
            "status": note.status or "",
            "snippet": snippet,
        })
    return results


@_tool
def vault_read(path: str) -> dict[str, Any]:
    """Read a note by its vault-relative path.

    Returns a dict with keys: path, title, frontmatter, body.
    Raises ValueError if the note does not exist.
    """
    vault, root = _load_vault()
    note_path = root / path
    if not note_path.exists():
        raise ValueError(f"Note not found: {path!r}")
    note = vault.resolve(note_path.stem)
    if note is None or note.path != note_path:
        # Load directly if resolve didn't find it (e.g. ignored folder)
        from jot.note import Note as _Note
        note = _Note.load(note_path)
    return {
        "path": str(note.path.relative_to(root)),
        "title": note.title,
        "frontmatter": {k: v for k, v in note._data.items()},
        "body": note.body,
    }


@_tool
def vault_write(path: str, body: str, frontmatter: dict[str, Any]) -> str:
    """Write or update a note at vault-relative *path*.

    Creates parent directories if needed. Returns the final path written.
    """
    vault, root = _load_vault()
    note_path = root / path
    note_path.parent.mkdir(parents=True, exist_ok=True)
    content = fm.dump(frontmatter, body)
    note_path.write_text(content, encoding="utf-8")
    return str(note_path.relative_to(root))


@_tool
def vault_list(
    tag: str | None = None,
    status: str | None = None,
    folder: str | None = None,
) -> list[dict[str, Any]]:
    """Return a filtered listing of notes.

    All filter params are optional. Returns list of {path, title, tags, status}.
    """
    vault, root = _load_vault()
    notes = vault.all_notes()

    if tag:
        tag_lower = tag.lower()
        notes = [n for n in notes if tag_lower in [t.lower() for t in n.tags]]
    if status:
        notes = [n for n in notes if n.status == status]
    if folder:
        folder_lower = folder.lower()
        notes = [n for n in notes if folder_lower in str(n.path.relative_to(root)).lower()]

    return [
        {
            "path": str(n.path.relative_to(root)),
            "title": n.title,
            "tags": n.tags,
            "status": n.status or "",
        }
        for n in sorted(notes, key=lambda n: str(n.path.relative_to(root)))
    ]


@_tool
def vault_query(
    tag: str | None = None,
    status: str | None = None,
    search: str | None = None,
    folder: str | None = None,
    has_link: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Structured query with all filter combinators.

    Returns list of {path, title, tags, status}.
    """
    vault, root = _load_vault()
    notes = vault.all_notes()

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

    notes = sorted(notes, key=lambda n: str(n.path.relative_to(root)))

    if limit is not None:
        notes = notes[:limit]

    return [
        {
            "path": str(n.path.relative_to(root)),
            "title": n.title,
            "tags": n.tags,
            "status": n.status or "",
        }
        for n in notes
    ]


@_tool
def vault_backlinks(path: str) -> list[dict[str, Any]]:
    """Return all notes that link to the note at vault-relative *path*.

    Returns list of {path, title, tags, status}.
    """
    vault, root = _load_vault()
    note_path = root / path
    if not note_path.exists():
        raise ValueError(f"Note not found: {path!r}")

    target = vault.resolve(note_path.stem)
    if target is None or target.path != note_path:
        raise ValueError(f"Note could not be resolved in vault: {path!r}")

    bl = vault.backlinks(target)
    return [
        {
            "path": str(n.path.relative_to(root)),
            "title": n.title,
            "tags": n.tags,
            "status": n.status or "",
        }
        for n in bl
    ]


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #


def main() -> None:
    """Start the MCP server (called by `jot mcp` and the jot-mcp entry point)."""
    if not _MCP_AVAILABLE:
        import sys
        print(
            "Error: the 'mcp' package is not installed.\n"
            "Install it with:  pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)
    _mcp.run()


if __name__ == "__main__":
    main()
