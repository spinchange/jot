"""Config — load/save ~/.jot/config.json."""

from __future__ import annotations

import json
import socket
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import click

CONFIG_DIR = Path.home() / ".jot"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    vault: str = ""
    editor: str = ""
    no_open: bool = False
    stale_days: int = 30
    dashboard_limit: int = 5
    templates: str = ""
    queries: str = ""
    author: str = ""
    hostname: str = ""
    ignore_folders: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Load / save
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data: dict[str, Any] = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        stale_days = data.get("staleDays", 30)
        if not isinstance(stale_days, int) or stale_days <= 0:
            click.echo(
                f"Warning: staleDays must be a positive integer (got {stale_days!r}) — defaulting to 30.",
                err=True,
            )
            stale_days = 30

        dashboard_limit = data.get("dashboardLimit", 5)
        if not isinstance(dashboard_limit, int) or dashboard_limit <= 0:
            click.echo(
                f"Warning: dashboardLimit must be a positive integer (got {dashboard_limit!r}) — defaulting to 5.",
                err=True,
            )
            dashboard_limit = 5

        return cls(
            vault=data.get("vault", ""),
            editor=data.get("editor", ""),
            no_open=data.get("noOpen", False),
            stale_days=stale_days,
            dashboard_limit=dashboard_limit,
            templates=data.get("templates", ""),
            queries=data.get("queries", ""),
            author=data.get("author", ""),
            hostname=data.get("hostname", ""),
            ignore_folders=data.get("ignoreFolders", []),
        )

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "vault": self.vault,
            "editor": self.editor,
            "noOpen": self.no_open,
            "staleDays": self.stale_days,
            "dashboardLimit": self.dashboard_limit,
            "templates": self.templates,
            "queries": self.queries,
            "author": self.author,
            "hostname": self.hostname,
            "ignoreFolders": self.ignore_folders,
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Vault path helper
    # ------------------------------------------------------------------ #

    @property
    def vault_path(self) -> Path | None:
        if self.vault:
            p = Path(self.vault).expanduser()
            return p if p.is_dir() else None
        return None

    def resolve_author(self) -> str:
        """Return configured author, falling back to OS username."""
        return (
            self.author
            or os.environ.get("USER")
            or os.environ.get("USERNAME", "unknown")
        )

    def resolve_hostname(self) -> str:
        """Return configured hostname, falling back to system hostname."""
        return self.hostname or socket.gethostname()

    def require_vault(self) -> Path:
        """Return vault path or raise a UsageError with a friendly message."""
        if not self.vault:
            raise click.UsageError(
                "No vault configured. Run 'jot config init' to set one up."
            )
        p = Path(self.vault).expanduser()
        if not p.is_dir():
            raise click.UsageError(
                f"Vault path {str(p)!r} does not exist or is not a directory. "
                "Run 'jot config init' to reconfigure."
            )
        return p
