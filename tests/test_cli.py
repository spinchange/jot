"""CLI smoke tests via click.testing.CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from jot.cli import cli
from jot.config import Config


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def cli_cfg(vault_root: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Patch Config.load to return a config pointing at vault_root, with no_open=True."""
    config = Config(vault=str(vault_root), editor="", no_open=True)
    monkeypatch.setattr("jot.config.Config.load", classmethod(lambda cls: config))
    # Patch every command module that calls Config.load
    for mod in [
        "jot.commands.create",
        "jot.commands.find",
        "jot.commands.capture",
        "jot.commands.links",
        "jot.commands.tags",
        "jot.commands.organize",
        "jot.commands.tasks",
        "jot.commands.views",
        "jot.commands.template",
        "jot.commands.config_cmd",
        "jot.commands.publish",
    ]:
        try:
            monkeypatch.setattr(f"{mod}.Config.load", classmethod(lambda cls: config))
        except AttributeError:
            pass
    return config


class TestTopLevel:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "jot" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_unknown_command(self, runner):
        result = runner.invoke(cli, ["notacommand"])
        assert result.exit_code != 0


class TestConfigCmd:
    def test_config_path(self, runner):
        result = runner.invoke(cli, ["config", "path"])
        assert result.exit_code == 0
        assert "config.json" in result.output

    def test_config_show(self, runner):
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0


class TestList:
    def test_list_all(self, runner, cli_cfg):
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "alpha" in result.output.lower()

    def test_list_by_tag(self, runner, cli_cfg):
        result = runner.invoke(cli, ["list", "--tag", "project"])
        assert result.exit_code == 0
        assert "alpha" in result.output.lower()
        # orphan has no project tag
        assert "orphan" not in result.output.lower()

    def test_list_by_status(self, runner, cli_cfg):
        result = runner.invoke(cli, ["list", "--status", "draft"])
        assert result.exit_code == 0
        assert "beta" in result.output.lower()


class TestSearch:
    def test_search_finds_match(self, runner, cli_cfg):
        result = runner.invoke(cli, ["search", "Links back"])
        assert result.exit_code == 0
        assert "beta" in result.output.lower()

    def test_search_no_results(self, runner, cli_cfg):
        result = runner.invoke(cli, ["search", "zzznomatchzzz"])
        assert result.exit_code == 0
        assert "No results" in result.output


class TestRecent:
    def test_recent(self, runner, cli_cfg):
        result = runner.invoke(cli, ["recent"])
        assert result.exit_code == 0

    def test_recent_n(self, runner, cli_cfg):
        result = runner.invoke(cli, ["recent", "3"])
        assert result.exit_code == 0


class TestPreview:
    def test_preview_existing(self, runner, cli_cfg):
        result = runner.invoke(cli, ["preview", "alpha"])
        assert result.exit_code == 0
        assert "Alpha" in result.output

    def test_preview_missing(self, runner, cli_cfg):
        result = runner.invoke(cli, ["preview", "nonexistent"])
        assert result.exit_code != 0


class TestNew:
    def test_new_creates_file(self, runner, cli_cfg, vault_root):
        result = runner.invoke(cli, ["new", "Brand New Note"])
        assert result.exit_code == 0
        assert (vault_root / "brand-new-note.md").exists()

    def test_new_existing_note(self, runner, cli_cfg):
        result = runner.invoke(cli, ["new", "Alpha"])
        assert result.exit_code == 0
        assert "Already exists" in result.output


class TestCapture:
    def test_capture_to_inbox(self, runner, cli_cfg, vault_root):
        result = runner.invoke(cli, ["capture", "My captured thought"])
        assert result.exit_code == 0
        inbox = (vault_root / "inbox.md").read_text(encoding="utf-8")
        assert "My captured thought" in inbox

    def test_capture_to_daily(self, runner, cli_cfg, vault_root):
        result = runner.invoke(cli, ["capture", "--daily", "Daily thought"])
        assert result.exit_code == 0

    def test_capture_empty_fails(self, runner, cli_cfg):
        result = runner.invoke(cli, ["capture", ""])
        assert result.exit_code != 0

    def test_capture_from_stdin(self, runner, cli_cfg, vault_root):
        result = runner.invoke(cli, ["capture"], input="piped thought\n")
        assert result.exit_code == 0
        inbox = (vault_root / "inbox.md").read_text(encoding="utf-8")
        assert "piped thought" in inbox


class TestLinks:
    def test_links_command(self, runner, cli_cfg):
        result = runner.invoke(cli, ["links", "alpha"])
        assert result.exit_code == 0
        assert "Beta" in result.output or "gamma" in result.output.lower()

    def test_backlinks_command(self, runner, cli_cfg):
        result = runner.invoke(cli, ["backlinks", "alpha"])
        assert result.exit_code == 0
        assert "beta" in result.output.lower()

    def test_unresolved_command(self, runner, cli_cfg):
        result = runner.invoke(cli, ["unresolved"])
        assert result.exit_code == 0
        assert "NonExistent" in result.output

    def test_orphans_command(self, runner, cli_cfg):
        result = runner.invoke(cli, ["orphans"])
        assert result.exit_code == 0
        assert "orphan" in result.output.lower()


class TestTags:
    def test_tags_vault_wide(self, runner, cli_cfg):
        result = runner.invoke(cli, ["tags"])
        assert result.exit_code == 0
        assert "project" in result.output

    def test_tags_single_note(self, runner, cli_cfg):
        result = runner.invoke(cli, ["tags", "alpha"])
        assert result.exit_code == 0
        assert "project" in result.output


class TestProps:
    def test_props_show(self, runner, cli_cfg):
        result = runner.invoke(cli, ["props", "show", "alpha"])
        assert result.exit_code == 0
        assert "title" in result.output

    def test_props_set_and_show(self, runner, cli_cfg, vault_root):
        runner.invoke(cli, ["props", "set", "gamma", "priority", "high"])
        result = runner.invoke(cli, ["props", "show", "gamma"])
        assert result.exit_code == 0
        assert "priority" in result.output


class TestTasks:
    def test_tasks_vault_wide(self, runner, cli_cfg):
        result = runner.invoke(cli, ["tasks"])
        assert result.exit_code == 0
        assert "task" in result.output.lower()

    def test_tasks_single_note(self, runner, cli_cfg):
        result = runner.invoke(cli, ["tasks", "alpha"])
        assert result.exit_code == 0
        assert "open task" in result.output
        assert "done task" in result.output

    def test_tasks_open_only(self, runner, cli_cfg):
        result = runner.invoke(cli, ["tasks", "alpha", "--open"])
        assert result.exit_code == 0
        assert "open task" in result.output
        assert "done task" not in result.output


class TestDashboard:
    def test_dashboard(self, runner, cli_cfg):
        result = runner.invoke(cli, ["dashboard"])
        assert result.exit_code == 0
        assert "Notes" in result.output


class TestReport:
    def test_report_default(self, runner, cli_cfg):
        result = runner.invoke(cli, ["report"])
        assert result.exit_code == 0

    def test_report_with_dates(self, runner, cli_cfg):
        result = runner.invoke(cli, ["report", "--since", "2020-01-01", "--until", "2099-12-31"])
        assert result.exit_code == 0


class TestReview:
    def test_review(self, runner, cli_cfg):
        result = runner.invoke(cli, ["review"])
        assert result.exit_code == 0
        # beta is draft, so should appear
        assert "beta" in result.output.lower()


class TestPublish:
    def test_publish_dry_run(self, runner, cli_cfg, tmp_path):
        out = tmp_path / "dist"
        result = runner.invoke(cli, ["publish", "--output", str(out), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert not out.exists()

    def test_publish_transforms_wikilinks(self, runner, cli_cfg, vault_root, tmp_path):
        out = tmp_path / "dist"
        result = runner.invoke(cli, ["publish", "--output", str(out)])
        assert result.exit_code == 0
        alpha_out = out / "alpha.md"
        assert alpha_out.exists()
        content = alpha_out.read_text(encoding="utf-8")
        # Wikilinks should be replaced with markdown links
        assert "[[" not in content
        assert "[" in content  # some link exists


class TestRenameRepairLinks:
    def test_repair_links_dry_run(self, runner, cli_cfg):
        result = runner.invoke(cli, ["repair-links", "NonExistent", "New Name", "--dry-run"])
        assert result.exit_code == 0

    def test_rename_dry_run(self, runner, cli_cfg):
        result = runner.invoke(cli, ["rename", "orphan", "renamed-orphan", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_rename_updates_title_frontmatter(self, runner, cli_cfg, vault_root):
        # Note with title that differs from stem
        (vault_root / "old-stem.md").write_text(
            "---\ntitle: Old Title\n---\n\nBody.", encoding="utf-8"
        )
        result = runner.invoke(cli, ["rename", "old-stem", "New Title"])
        assert result.exit_code == 0
        new_path = vault_root / "new-title.md"
        assert new_path.exists()
        assert not (vault_root / "old-stem.md").exists()
        content = new_path.read_text(encoding="utf-8")
        assert "New Title" in content
        assert "Old Title" not in content

    def test_rename_no_title_field_leaves_no_title(self, runner, cli_cfg, vault_root):
        # Note with no title frontmatter — rename should not inject one
        (vault_root / "bare-note.md").write_text("Just a body.", encoding="utf-8")
        result = runner.invoke(cli, ["rename", "bare-note", "Renamed Bare"])
        assert result.exit_code == 0
        new_path = vault_root / "renamed-bare.md"
        assert new_path.exists()
        content = new_path.read_text(encoding="utf-8")
        assert "title:" not in content


class TestGraphOrphans:
    def test_graph_output(self, runner, cli_cfg):
        result = runner.invoke(cli, ["graph"])
        assert result.exit_code == 0
        assert "graph TD" in result.output

    def test_create_unresolved_dry_run(self, runner, cli_cfg):
        result = runner.invoke(cli, ["create-unresolved", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


class TestAgenda:
    def test_agenda(self, runner, cli_cfg):
        result = runner.invoke(cli, ["agenda", "--days", "36500"])
        assert result.exit_code == 0
        # gamma has due: 2099-12-31 — should appear with 100-year window
        assert "gamma" in result.output.lower() or "Gamma" in result.output
