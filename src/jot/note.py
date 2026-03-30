"""Note — represents a single .md file in a YANP vault."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from jot import frontmatter as fm

# Matches [[Title]] and [[Title|Display]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|#\n]+?)(?:\|([^\]\n]+))?\]\]")

# Inline tag: #word or #word/subword, not inside code spans or fences
_INLINE_TAG_RE = re.compile(r"(?<![`\w])#([\w][\w/.-]*)")

# Code block / code span strippers used before inline-tag scan
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_CODE_SPAN_RE = re.compile(r"`[^`\n]+`")


class Note:
    def __init__(self, path: Path, data: dict[str, Any], body: str) -> None:
        self.path = path
        self._data = data      # raw frontmatter dict (mutable, preserves unknown fields)
        self.body = body

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls, path: Path) -> "Note":
        text = path.read_text(encoding="utf-8")
        data, body = fm.parse(text)
        return cls(path, data, body)

    # ------------------------------------------------------------------ #
    # Identity
    # ------------------------------------------------------------------ #

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def title(self) -> str:
        return self._data.get("title") or self.stem

    @property
    def aliases(self) -> list[str]:
        raw = self._data.get("aliases") or []
        if isinstance(raw, str):
            return [raw]
        return list(raw)

    # ------------------------------------------------------------------ #
    # Tags (merged inline + frontmatter)
    # ------------------------------------------------------------------ #

    @property
    def tags(self) -> list[str]:
        fm_tags: list[str] = self._data.get("tags") or []
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]

        # Strip code blocks/spans before scanning for inline tags
        clean_body = _CODE_FENCE_RE.sub("", self.body)
        clean_body = _CODE_SPAN_RE.sub("", clean_body)
        inline_tags = [m.group(1).rstrip(".,;:!?").lower() for m in _INLINE_TAG_RE.finditer(clean_body)]

        seen: dict[str, str] = {}
        for t in list(fm_tags) + inline_tags:
            key = t.lower()
            if key not in seen:
                seen[key] = t
        return list(seen.values())

    # ------------------------------------------------------------------ #
    # Links
    # ------------------------------------------------------------------ #

    @property
    def wikilinks(self) -> list[tuple[str, str | None]]:
        """Return list of (target_name, display_text_or_None) for every wikilink in body."""
        return [(m.group(1).strip(), m.group(2)) for m in _WIKILINK_RE.finditer(self.body)]

    @property
    def wikilink_targets(self) -> set[str]:
        return {name for name, _ in self.wikilinks}

    # ------------------------------------------------------------------ #
    # Frontmatter accessors
    # ------------------------------------------------------------------ #

    @property
    def date(self) -> date | None:
        raw = self._data.get("date")
        if isinstance(raw, date):
            return raw
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None
        return None

    @property
    def status(self) -> str | None:
        return self._data.get("status")

    @property
    def author(self) -> str | None:
        return self._data.get("author")

    @property
    def hostname(self) -> str | None:
        return self._data.get("hostname")

    @property
    def due(self) -> date | None:
        raw = self._data.get("due")
        if isinstance(raw, date):
            return raw
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None
        return None

    @property
    def scheduled(self) -> date | None:
        raw = self._data.get("scheduled")
        if isinstance(raw, date):
            return raw
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None
        return None

    def get_prop(self, key: str) -> Any:
        return self._data.get(key)

    def set_prop(self, key: str, value: Any) -> None:
        self._data[key] = value

    def unset_prop(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    # ------------------------------------------------------------------ #
    # Tasks (GFM checkboxes)
    # ------------------------------------------------------------------ #

    @property
    def tasks(self) -> list[tuple[bool, str]]:
        """Return list of (done, text) for every GFM checkbox in body."""
        results = []
        for line in self.body.splitlines():
            m = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.*)", line)
            if m:
                done = m.group(1).lower() == "x"
                results.append((done, m.group(2)))
        return results

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        self.path.write_text(fm.dump(self._data, self.body), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return f"Note({self.path.name!r})"
