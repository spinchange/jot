"""Tests for jot.vault — Vault class."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from jot.vault import Vault


@pytest.fixture()
def vault(vault_root: Path) -> Vault:
    return Vault.load(vault_root)


class TestLoading:
    def test_loads_all_md_files(self, vault):
        stems = {n.stem for n in vault.all_notes()}
        assert "alpha" in stems
        assert "beta" in stems
        assert "gamma" in stems
        assert "orphan" in stems

    def test_ignores_non_md(self, vault_root, vault):
        (vault_root / "readme.txt").write_text("ignored")
        vault.reload()
        stems = {n.stem for n in vault.all_notes()}
        assert "readme" not in stems

    def test_loads_notes_in_subdirs(self, vault):
        stems = {n.stem for n in vault.all_notes()}
        assert "2024-01-15" in stems


class TestResolve:
    def test_resolve_by_stem(self, vault):
        note = vault.resolve("alpha")
        assert note is not None
        assert note.stem == "alpha"

    def test_resolve_by_title(self, vault):
        note = vault.resolve("Alpha")
        assert note is not None

    def test_resolve_case_insensitive(self, vault):
        assert vault.resolve("ALPHA") is not None
        assert vault.resolve("alpha") is not None

    def test_resolve_by_title_differs_from_stem(self, vault_root):
        # Create a note where title diverges from filename
        (vault_root / "my-long-filename.md").write_text(
            "---\ntitle: Short Title\n---\n\nBody.", encoding="utf-8"
        )
        vault = Vault.load(vault_root)
        note = vault.resolve("Short Title")
        assert note is not None
        assert note.stem == "my-long-filename"

    def test_resolve_by_title_case_insensitive(self, vault_root):
        (vault_root / "another-note.md").write_text(
            "---\ntitle: Fancy Note Title\n---\n\nBody.", encoding="utf-8"
        )
        vault = Vault.load(vault_root)
        assert vault.resolve("fancy note title") is not None

    def test_resolve_by_alias(self, vault):
        # beta.md has alias "B Note"
        note = vault.resolve("B Note")
        assert note is not None
        assert note.stem == "beta"

    def test_resolve_alias_case_insensitive(self, vault):
        assert vault.resolve("b note") is not None

    def test_resolve_missing_returns_none(self, vault):
        assert vault.resolve("does-not-exist") is None

    def test_resolve_prefers_title_over_alias_and_stem(self, vault_root):
        (vault_root / "title-note.md").write_text(
            "---\ntitle: Shared Name\n---\n\nBody.", encoding="utf-8"
        )
        (vault_root / "stem-note.md").write_text(
            "---\naliases:\n  - Shared Name\n---\n\nBody.", encoding="utf-8"
        )
        (vault_root / "shared-name.md").write_text("Body.", encoding="utf-8")

        vault = Vault.load(vault_root)
        note = vault.resolve("Shared Name")
        assert note is not None
        assert note.stem == "title-note"

    def test_resolve_conflict_uses_most_recently_modified_note(self, vault_root):
        older = vault_root / "older.md"
        newer = vault_root / "newer.md"
        older.write_text("---\ntitle: Clash\n---\n\nOld.", encoding="utf-8")
        newer.write_text("---\ntitle: Clash\n---\n\nNew.", encoding="utf-8")

        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_800_000_000, 1_800_000_000))

        vault = Vault.load(vault_root)
        note = vault.resolve("Clash")
        assert note is not None
        assert note.stem == "newer"


class TestSearch:
    def test_search_finds_in_body(self, vault):
        results = vault.search("Links back to")
        assert any(n.stem == "beta" for n in results)

    def test_search_finds_in_title(self, vault):
        results = vault.search("Alpha")
        assert any(n.stem == "alpha" for n in results)

    def test_search_case_insensitive_by_default(self, vault):
        results = vault.search("links back to")
        assert any(n.stem == "beta" for n in results)

    def test_search_case_sensitive(self, vault):
        # "links back to" lowercase won't match "Links back to" with case_sensitive
        results = vault.search("LINKS BACK TO", case_sensitive=True)
        assert len(results) == 0

    def test_search_no_results(self, vault):
        assert vault.search("zzznomatchzzz") == []

    def test_find_by_tag(self, vault):
        results = vault.find_by_tag("project")
        stems = {n.stem for n in results}
        assert "alpha" in stems
        assert "beta" in stems
        assert "gamma" not in stems


class TestBacklinks:
    def test_backlinks_found(self, vault):
        alpha = vault.resolve("alpha")
        bl = vault.backlinks(alpha)
        stems = {n.stem for n in bl}
        # beta links back to [[Alpha|see alpha]]
        assert "beta" in stems

    def test_no_backlinks(self, vault):
        orphan = vault.resolve("orphan")
        assert vault.backlinks(orphan) == []

    def test_backlinks_exclude_self(self, vault):
        alpha = vault.resolve("alpha")
        bl = vault.backlinks(alpha)
        assert alpha not in bl

    def test_backlinks_follow_resolution_rules(self, vault_root):
        (vault_root / "target-file.md").write_text(
            "---\ntitle: Target Title\naliases:\n  - Target Alias\n---\n\nBody.",
            encoding="utf-8",
        )
        (vault_root / "source.md").write_text(
            "Via title [[Target Title]], alias [[Target Alias]], and stem [[target-file]].",
            encoding="utf-8",
        )

        vault = Vault.load(vault_root)
        target = vault.resolve("Target Title")
        bl = vault.backlinks(target)
        assert {n.stem for n in bl} == {"source"}


class TestUnresolved:
    def test_unresolved_links_detected(self, vault):
        pairs = vault.unresolved_links()
        link_names = {link for _, link in pairs}
        assert "NonExistent" in link_names
        assert "AlsoMissing" in link_names

    def test_resolved_links_not_in_unresolved(self, vault):
        pairs = vault.unresolved_links()
        link_names = {link for _, link in pairs}
        # "Beta" and "gamma" are real notes
        assert "Beta" not in link_names
        assert "gamma" not in link_names


class TestOrphans:
    def test_orphan_detected(self, vault):
        orph = vault.orphans()
        stems = {n.stem for n in orph}
        assert "orphan" in stems

    def test_linked_notes_not_orphans(self, vault):
        orph = vault.orphans()
        stems = {n.stem for n in orph}
        assert "alpha" not in stems
        assert "beta" not in stems


class TestPeriodic:
    def test_daily_path(self, vault_root):
        from datetime import date
        vault = Vault.load(vault_root)
        d = date(2025, 6, 15)
        path = vault.daily_path(d)
        assert path == vault_root / "daily" / "2025-06-15.md"

    def test_weekly_path(self, vault_root):
        from datetime import date
        vault = Vault.load(vault_root)
        d = date(2025, 1, 6)  # Week 2 of 2025
        path = vault.weekly_path(d)
        assert "weekly" in str(path)
        assert "2025-W" in path.stem

    def test_monthly_path(self, vault_root):
        from datetime import date
        vault = Vault.load(vault_root)
        d = date(2025, 3, 15)
        path = vault.monthly_path(d)
        assert path == vault_root / "monthly" / "2025-03.md"

    def test_inbox_path(self, vault_root):
        vault = Vault.load(vault_root)
        assert vault.inbox == vault_root / "inbox.md"


class TestStats:
    def test_stats_shape(self, vault):
        stats = vault.stats()
        assert "total_notes" in stats
        assert "total_words" in stats
        assert "total_tags" in stats
        assert "orphans" in stats
        assert "unresolved" in stats
        assert stats["total_notes"] > 0
