"""git_util — lightweight git helpers for auto-commit support."""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(path: Path) -> bool:
    """Return True if *path* is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception:
        return False


def git_commit(vault_root: Path, message: str) -> None:
    """Stage all changes and commit with *message*.

    Silently does nothing if the vault is not a git repo or there is nothing
    to commit.  Never raises — exceptions are swallowed and a dim warning is
    printed if git fails.
    """
    try:
        if not is_git_repo(vault_root):
            return

        # Stage everything
        add = subprocess.run(
            ["git", "-C", str(vault_root), "add", "-A"],
            capture_output=True,
            text=True,
        )
        if add.returncode != 0:
            import click
            click.echo(f"[dim]git warning: {add.stderr.strip()}[/dim]", err=True)
            return

        # Commit — silently skip if nothing to commit
        commit = subprocess.run(
            ["git", "-C", str(vault_root), "commit", "-m", message],
            capture_output=True,
            text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout + commit.stderr:
            import click
            click.echo(f"[dim]git warning: {commit.stderr.strip()}[/dim]", err=True)
    except Exception as exc:
        import click
        click.echo(f"[dim]git warning: {exc}[/dim]", err=True)
