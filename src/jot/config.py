"""Config — load/save ~/.jot/config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

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
        return cls(
            vault=data.get("vault", ""),
            editor=data.get("editor", ""),
            no_open=data.get("noOpen", False),
            stale_days=data.get("staleDays", 30),
            dashboard_limit=data.get("dashboardLimit", 5),
            templates=data.get("templates", ""),
            queries=data.get("queries", ""),
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

    def require_vault(self) -> Path:
        """Return vault path or raise with a friendly message."""
        p = self.vault_path
        if p is None:
            raise click_error(
                "No vault configured. Run [bold]jot config init[/bold] to set one up."
            )
        return p


def click_error(msg: str) -> SystemExit:
    """Import click lazily to avoid circular import in config module."""
    import click
    raise click.ClickException(msg)
