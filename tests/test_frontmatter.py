"""Tests for jot.frontmatter — parse and dump."""

from __future__ import annotations

import pytest
from jot import frontmatter as fm


class TestParse:
    def test_valid_frontmatter(self):
        from datetime import date
        text = "---\ntitle: Hello\ndate: 2024-01-01\n---\n\nBody here."
        data, body = fm.parse(text)
        assert data["title"] == "Hello"
        # PyYAML coerces YYYY-MM-DD to datetime.date; accept either form
        assert data["date"] in ("2024-01-01", date(2024, 1, 1))
        assert body == "\nBody here."

    def test_no_frontmatter(self):
        text = "# Just a heading\n\nSome body."
        data, body = fm.parse(text)
        assert data == {}
        assert body == text

    def test_empty_frontmatter_block(self):
        text = "---\n\n---\n\nBody."
        data, body = fm.parse(text)
        assert data == {}
        assert body == "\nBody."

    def test_malformed_yaml_returns_empty(self):
        text = "---\nkey: [unclosed\n---\n\nBody."
        data, body = fm.parse(text)
        assert data == {}
        assert body == text

    def test_non_dict_yaml_returns_empty(self):
        # YAML that parses to a list is not valid frontmatter
        text = "---\n- item1\n- item2\n---\n\nBody."
        data, body = fm.parse(text)
        assert data == {}
        assert body == text

    def test_tags_as_list(self):
        text = "---\ntags:\n  - a\n  - b\n---\n\nBody."
        data, body = fm.parse(text)
        assert data["tags"] == ["a", "b"]

    def test_unknown_fields_preserved(self):
        text = "---\ncustom_field: custom_value\nother: 42\n---\n\nBody."
        data, body = fm.parse(text)
        assert data["custom_field"] == "custom_value"
        assert data["other"] == 42

    def test_body_preserves_leading_newline(self):
        text = "---\ntitle: T\n---\n\n\nDouble newline body."
        data, body = fm.parse(text)
        assert body.startswith("\n\n")


class TestDump:
    def test_round_trip(self):
        original = "---\ntitle: Hello\ndate: 2024-01-01\n---\n\nBody here."
        data, body = fm.parse(original)
        result = fm.dump(data, body)
        # Re-parse and verify content is preserved
        data2, body2 = fm.parse(result)
        assert data2["title"] == "Hello"
        assert body2 == body

    def test_empty_frontmatter_returns_body_only(self):
        body = "# Just body\n"
        result = fm.dump({}, body)
        assert result == body

    def test_dump_preserves_unknown_fields(self):
        data = {"title": "T", "my_custom": "value"}
        body = "\nBody.\n"
        result = fm.dump(data, body)
        data2, _ = fm.parse(result)
        assert data2["my_custom"] == "value"

    def test_dump_produces_valid_yaml_block(self):
        data = {"title": "Test", "tags": ["a", "b"]}
        body = "\nBody.\n"
        result = fm.dump(data, body)
        assert result.startswith("---\n")
        assert "\n---\n" in result

    def test_list_items_indented_under_key(self):
        data = {"tags": ["a", "b", "c"]}
        result = fm.dump(data, "")
        assert "  - a" in result
        assert "  - b" in result

    def test_author_field_preserved(self):
        data = {"source": "ai", "author": "claude"}
        body = "\nBody.\n"
        result = fm.dump(data, body)
        data2, _ = fm.parse(result)
        assert data2["author"] == "claude"
        assert data2["source"] == "ai"
