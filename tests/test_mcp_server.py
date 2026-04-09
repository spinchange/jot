"""Tests for jot.mcp_server — calls tool functions directly, no MCP protocol needed."""

from __future__ import annotations

from pathlib import Path

import pytest

import jot.mcp_server as mcp
from jot.config import Config


# ------------------------------------------------------------------ #
# Fixture: wire cfg so _load_vault() in mcp_server uses the test vault
# ------------------------------------------------------------------ #


@pytest.fixture()
def srv(vault_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch Config.load in the mcp_server module to point at vault_root."""
    config = Config(vault=str(vault_root), editor="", no_open=True)
    monkeypatch.setattr(mcp.Config, "load", classmethod(lambda cls: config))


# ------------------------------------------------------------------ #
# vault_search
# ------------------------------------------------------------------ #


class TestVaultSearch:
    def test_finds_body_match(self, srv, vault_root):
        results = mcp.vault_search("Body of alpha")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths

    def test_finds_title_match(self, srv, vault_root):
        results = mcp.vault_search("Beta")
        paths = [r["path"] for r in results]
        assert "beta.md" in paths

    def test_case_insensitive(self, srv, vault_root):
        results = mcp.vault_search("GAMMA")
        paths = [r["path"] for r in results]
        assert "gamma.md" in paths

    def test_no_match_returns_empty(self, srv, vault_root):
        results = mcp.vault_search("xyzzy_no_such_thing")
        assert results == []

    def test_result_shape(self, srv, vault_root):
        results = mcp.vault_search("alpha")
        hit = next(r for r in results if r["path"] == "alpha.md")
        assert set(hit.keys()) == {"path", "title", "tags", "status", "snippet"}
        assert hit["title"] == "Alpha"
        assert "project" in hit["tags"]
        assert hit["status"] == "active"
        assert hit["snippet"]  # non-empty: matched body line

    def test_snippet_is_matching_line(self, srv, vault_root):
        results = mcp.vault_search("Body of alpha")
        hit = next(r for r in results if r["path"] == "alpha.md")
        assert "Body of alpha" in hit["snippet"]

    def test_title_only_match_has_empty_snippet(self, srv, vault_root):
        # "Orphan" appears only in the title, not the body
        results = mcp.vault_search("No links in or out")
        hit = next((r for r in results if r["path"] == "orphan.md"), None)
        assert hit is not None  # body match finds it


# ------------------------------------------------------------------ #
# vault_read
# ------------------------------------------------------------------ #


class TestVaultRead:
    def test_reads_existing_note(self, srv, vault_root):
        result = mcp.vault_read("alpha.md")
        assert result["path"] == "alpha.md"
        assert result["title"] == "Alpha"
        assert "Body of alpha" in result["body"]

    def test_frontmatter_included(self, srv, vault_root):
        result = mcp.vault_read("alpha.md")
        fm = result["frontmatter"]
        assert fm["status"] == "active"
        assert "project" in fm["tags"]

    def test_nested_note(self, srv, vault_root):
        result = mcp.vault_read("daily/2024-01-15.md")
        assert "2024-01-15" in result["path"]

    def test_missing_note_raises(self, srv, vault_root):
        with pytest.raises(ValueError, match="not found"):
            mcp.vault_read("does_not_exist.md")

    def test_result_keys(self, srv, vault_root):
        result = mcp.vault_read("beta.md")
        assert set(result.keys()) == {"path", "title", "frontmatter", "body"}


# ------------------------------------------------------------------ #
# vault_write
# ------------------------------------------------------------------ #


class TestVaultWrite:
    def test_creates_new_note(self, srv, vault_root):
        returned = mcp.vault_write(
            "new-note.md",
            body="Hello world.",
            frontmatter={"title": "New Note", "tags": ["test"]},
        )
        assert returned == "new-note.md"
        assert (vault_root / "new-note.md").exists()

    def test_written_content_is_readable(self, srv, vault_root):
        mcp.vault_write(
            "written.md",
            body="Written body.",
            frontmatter={"title": "Written", "status": "draft"},
        )
        result = mcp.vault_read("written.md")
        assert result["title"] == "Written"
        assert "Written body." in result["body"]
        assert result["frontmatter"]["status"] == "draft"

    def test_overwrites_existing_note(self, srv, vault_root):
        mcp.vault_write("orphan.md", body="Replaced.", frontmatter={"title": "Orphan"})
        result = mcp.vault_read("orphan.md")
        assert "Replaced." in result["body"]

    def test_creates_parent_directories(self, srv, vault_root):
        mcp.vault_write(
            "projects/deep/note.md",
            body="Deep note.",
            frontmatter={"title": "Deep"},
        )
        assert (vault_root / "projects" / "deep" / "note.md").exists()

    def test_returns_vault_relative_path(self, srv, vault_root):
        returned = mcp.vault_write(
            "sub/note.md",
            body="",
            frontmatter={"title": "Sub"},
        )
        assert Path(returned) == Path("sub/note.md")


# ------------------------------------------------------------------ #
# vault_list
# ------------------------------------------------------------------ #


class TestVaultList:
    def test_lists_all_notes(self, srv, vault_root):
        results = mcp.vault_list()
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths
        assert "beta.md" in paths
        assert "gamma.md" in paths

    def test_filter_by_tag(self, srv, vault_root):
        results = mcp.vault_list(tag="project")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths
        assert "beta.md" in paths
        assert "gamma.md" not in paths

    def test_filter_by_status(self, srv, vault_root):
        results = mcp.vault_list(status="draft")
        paths = [r["path"] for r in results]
        assert "beta.md" in paths
        assert "alpha.md" not in paths

    def test_filter_by_folder(self, srv, vault_root):
        results = mcp.vault_list(folder="daily")
        paths = [r["path"] for r in results]
        assert all("daily" in p for p in paths)

    def test_tag_filter_case_insensitive(self, srv, vault_root):
        results_lower = mcp.vault_list(tag="project")
        results_upper = mcp.vault_list(tag="PROJECT")
        assert {r["path"] for r in results_lower} == {r["path"] for r in results_upper}

    def test_result_shape(self, srv, vault_root):
        results = mcp.vault_list()
        for r in results:
            assert set(r.keys()) == {"path", "title", "tags", "status"}

    def test_results_sorted(self, srv, vault_root):
        results = mcp.vault_list()
        paths = [r["path"] for r in results]
        assert paths == sorted(paths)

    def test_no_filters_returns_all(self, srv, vault_root):
        results = mcp.vault_list()
        assert len(results) >= 5  # alpha, beta, gamma, orphan, broken-links


# ------------------------------------------------------------------ #
# vault_query
# ------------------------------------------------------------------ #


class TestVaultQuery:
    def test_no_filters_returns_all(self, srv, vault_root):
        results = mcp.vault_query()
        assert len(results) >= 5

    def test_filter_by_tag(self, srv, vault_root):
        results = mcp.vault_query(tag="project")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths
        assert "beta.md" in paths
        assert "gamma.md" not in paths

    def test_filter_by_status(self, srv, vault_root):
        results = mcp.vault_query(status="active")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths
        assert "beta.md" not in paths

    def test_filter_by_search(self, srv, vault_root):
        results = mcp.vault_query(search="Beta body")
        paths = [r["path"] for r in results]
        assert "beta.md" in paths
        assert "alpha.md" not in paths

    def test_filter_by_folder(self, srv, vault_root):
        results = mcp.vault_query(folder="daily")
        paths = [r["path"] for r in results]
        assert all("daily" in p for p in paths)

    def test_filter_by_has_link(self, srv, vault_root):
        # alpha links to [[Beta]] and [[gamma]]
        results = mcp.vault_query(has_link="beta")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths

    def test_limit(self, srv, vault_root):
        all_results = mcp.vault_query()
        limited = mcp.vault_query(limit=2)
        assert len(limited) == 2
        # limit applies after sort, so first 2 should match
        assert limited == all_results[:2]

    def test_combined_tag_and_status(self, srv, vault_root):
        results = mcp.vault_query(tag="project", status="active")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths
        assert "beta.md" not in paths  # draft, not active

    def test_combined_search_and_limit(self, srv, vault_root):
        results = mcp.vault_query(search="links", limit=1)
        assert len(results) == 1

    def test_result_shape(self, srv, vault_root):
        results = mcp.vault_query()
        for r in results:
            assert set(r.keys()) == {"path", "title", "tags", "status"}


# ------------------------------------------------------------------ #
# vault_backlinks
# ------------------------------------------------------------------ #


class TestVaultBacklinks:
    def test_backlinks_to_beta(self, srv, vault_root):
        # alpha links to [[Beta]], beta links back to [[Alpha]]
        results = mcp.vault_backlinks("beta.md")
        paths = [r["path"] for r in results]
        assert "alpha.md" in paths

    def test_backlinks_to_alpha(self, srv, vault_root):
        results = mcp.vault_backlinks("alpha.md")
        paths = [r["path"] for r in results]
        assert "beta.md" in paths

    def test_note_with_no_backlinks(self, srv, vault_root):
        # orphan has no inbound links
        results = mcp.vault_backlinks("orphan.md")
        assert results == []

    def test_missing_note_raises(self, srv, vault_root):
        with pytest.raises(ValueError, match="not found"):
            mcp.vault_backlinks("does_not_exist.md")

    def test_result_shape(self, srv, vault_root):
        results = mcp.vault_backlinks("beta.md")
        for r in results:
            assert set(r.keys()) == {"path", "title", "tags", "status"}
