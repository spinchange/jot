"""Tests for jot.note — Note class."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from jot.note import Note


def write_note(tmp_path: Path, name: str, content: str) -> Note:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return Note.load(p)


class TestTitle:
    def test_title_from_frontmatter(self, tmp_path):
        n = write_note(tmp_path, "some-file.md", "---\ntitle: My Title\n---\n\nBody.")
        assert n.title == "My Title"

    def test_title_falls_back_to_stem(self, tmp_path):
        n = write_note(tmp_path, "some-file.md", "# heading\n\nBody.")
        assert n.title == "some-file"

    def test_stem_property(self, tmp_path):
        n = write_note(tmp_path, "my-note.md", "Body.")
        assert n.stem == "my-note"


class TestAliases:
    def test_aliases_list(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\naliases:\n  - Alias One\n  - Two\n---\n\nBody.")
        assert n.aliases == ["Alias One", "Two"]

    def test_aliases_empty_when_absent(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Body.")
        assert n.aliases == []

    def test_aliases_string_coerced_to_list(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\naliases: Single\n---\n\nBody.")
        assert n.aliases == ["Single"]


class TestTags:
    def test_frontmatter_tags_only(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntags:\n  - python\n  - notes\n---\n\nBody.")
        assert "python" in n.tags
        assert "notes" in n.tags

    def test_inline_tags_only(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Body with #python and #notes tags.")
        assert "python" in n.tags
        assert "notes" in n.tags

    def test_merged_tags_deduplicated(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntags:\n  - python\n---\n\nAlso #python and #notes.")
        tags = n.tags
        assert tags.count("python") == 1
        assert "notes" in tags

    def test_inline_tags_excluded_from_code_spans(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Use `#notag` in code. Real #realtag.")
        assert "notag" not in n.tags
        assert "realtag" in n.tags

    def test_inline_tags_excluded_from_code_fences(self, tmp_path):
        n = write_note(tmp_path, "note.md", "```\n#notag\n```\n\n#realtag")
        assert "notag" not in n.tags
        assert "realtag" in n.tags

    def test_hierarchical_tags(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Body #topic/subtopic here.")
        assert "topic/subtopic" in n.tags

    def test_tags_empty_when_none(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Plain body, no tags.")
        assert n.tags == []


class TestWikilinks:
    def test_simple_wikilink(self, tmp_path):
        n = write_note(tmp_path, "note.md", "See [[Other Note]] for details.")
        assert ("Other Note", None) in n.wikilinks

    def test_wikilink_with_display(self, tmp_path):
        n = write_note(tmp_path, "note.md", "See [[Other Note|click here]].")
        assert ("Other Note", "click here") in n.wikilinks

    def test_multiple_wikilinks(self, tmp_path):
        n = write_note(tmp_path, "note.md", "[[A]] and [[B|bee]] and [[C]].")
        targets = n.wikilink_targets
        assert targets == {"A", "B", "C"}

    def test_no_wikilinks(self, tmp_path):
        n = write_note(tmp_path, "note.md", "No links here.")
        assert n.wikilinks == []
        assert n.wikilink_targets == set()


class TestTasks:
    def test_open_task(self, tmp_path):
        n = write_note(tmp_path, "note.md", "- [ ] Buy milk\n- [ ] Walk dog\n")
        tasks = n.tasks
        assert len(tasks) == 2
        assert all(not done for done, _ in tasks)
        assert tasks[0][1] == "Buy milk"

    def test_done_task(self, tmp_path):
        n = write_note(tmp_path, "note.md", "- [x] Done task\n- [X] Also done\n")
        tasks = n.tasks
        assert all(done for done, _ in tasks)

    def test_mixed_tasks(self, tmp_path):
        n = write_note(tmp_path, "note.md", "- [ ] Open\n- [x] Done\n")
        done_states = [done for done, _ in n.tasks]
        assert done_states == [False, True]

    def test_no_tasks(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Plain paragraph.")
        assert n.tasks == []


class TestDates:
    def test_date_parsed(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ndate: 2024-06-15\n---\n\nBody.")
        assert n.date == date(2024, 6, 15)

    def test_due_date_parsed(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ndue: 2024-12-31\n---\n\nBody.")
        assert n.due == date(2024, 12, 31)

    def test_scheduled_date_parsed(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\nscheduled: 2025-01-01\n---\n\nBody.")
        assert n.scheduled == date(2025, 1, 1)

    def test_missing_date_returns_none(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Body.")
        assert n.date is None
        assert n.due is None


class TestProps:
    def test_set_prop(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntitle: T\n---\n\nBody.")
        n.set_prop("status", "active")
        assert n.get_prop("status") == "active"

    def test_unset_prop(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntitle: T\nstatus: draft\n---\n\nBody.")
        removed = n.unset_prop("status")
        assert removed is True
        assert n.get_prop("status") is None

    def test_unset_nonexistent_returns_false(self, tmp_path):
        n = write_note(tmp_path, "note.md", "Body.")
        assert n.unset_prop("nonexistent") is False

    def test_save_round_trip(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntitle: T\n---\n\nBody.")
        n.set_prop("status", "active")
        n.save()
        n2 = Note.load(n.path)
        assert n2.get_prop("status") == "active"
        assert n2.body == "\nBody."


class TestStatusLog:
    def test_status_log_empty_when_absent(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\nstatus: draft\n---\n\nBody.")
        assert n.status_log == []

    def test_append_status_log(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\nstatus: draft\n---\n\nBody.")
        n.append_status_log("active · 2026-03-29 14:32 · Nova · claude")
        assert len(n.status_log) == 1
        assert "active" in n.status_log[0]

    def test_status_log_append_only(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\nstatus: draft\n---\n\nBody.")
        n.append_status_log("draft · 2026-03-28 10:00 · Luna · claude")
        n.append_status_log("active · 2026-03-29 14:32 · Nova · chris")
        assert len(n.status_log) == 2
        assert n.status_log[0].startswith("draft")
        assert n.status_log[1].startswith("active")

    def test_status_log_round_trip(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\nstatus: draft\n---\n\nBody.")
        n.append_status_log("active · 2026-03-29 14:32 · Nova · claude")
        n.save()
        n2 = Note.load(n.path)
        assert n2.status_log == ["active · 2026-03-29 14:32 · Nova · claude"]


class TestTouch:
    def test_touch_sets_modified_to_today(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntitle: A\n---\n\nBody.")
        n.touch()
        assert n._data["modified"] == date.today().isoformat()

    def test_touch_persists_on_disk(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntitle: A\n---\n\nBody.")
        n.touch()
        n2 = Note.load(n.path)
        assert n2._data.get("modified") == date.today().isoformat()

    def test_touch_overwrites_old_modified(self, tmp_path):
        n = write_note(tmp_path, "note.md", "---\ntitle: A\nmodified: 2020-01-01\n---\n\nBody.")
        n.touch()
        assert n._data["modified"] == date.today().isoformat()
