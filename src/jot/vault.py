"""Vault — indexes all notes in a YANP vault directory."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from jot.note import Note

_DAILY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WEEKLY_RE = re.compile(r"^\d{4}-W\d{2}$")
_MONTHLY_RE = re.compile(r"^\d{4}-\d{2}$")

RESERVED_FOLDERS = {"daily", "weekly", "monthly", "assets", "templates"}
INBOX_NAME = "inbox"


class Vault:
    def __init__(self, root: Path) -> None:
        self.root = root
        # name → Note (lowercase stem as key)
        self._by_stem: dict[str, Note] = {}
        # alias → Note
        self._by_alias: dict[str, Note] = {}

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls, root: Path) -> "Vault":
        v = cls(root)
        for path in sorted(root.rglob("*.md")):
            try:
                note = Note.load(path)
            except Exception:
                continue
            key = note.stem.lower()
            v._by_stem[key] = note
            v._by_alias[note.title.lower()] = note
            for alias in note.aliases:
                v._by_alias[alias.lower()] = note
        return v

    def reload(self) -> None:
        self._by_stem.clear()
        self._by_alias.clear()
        for path in sorted(self.root.rglob("*.md")):
            try:
                note = Note.load(path)
            except Exception:
                continue
            key = note.stem.lower()
            self._by_stem[key] = note
            self._by_alias[note.title.lower()] = note
            for alias in note.aliases:
                self._by_alias[alias.lower()] = note

    # ------------------------------------------------------------------ #
    # Lookup
    # ------------------------------------------------------------------ #

    def resolve(self, name: str) -> Note | None:
        """Resolve a wikilink name to a Note (by stem or alias, case-insensitive)."""
        key = name.strip().lower()
        return self._by_stem.get(key) or self._by_alias.get(key)

    def get(self, stem: str) -> Note | None:
        return self._by_stem.get(stem.lower())

    def all_notes(self) -> list[Note]:
        return list(self._by_stem.values())

    def note_path(self, stem: str, subfolder: str | None = None) -> Path:
        """Return the canonical path for a new or existing note."""
        existing = self.resolve(stem)
        if existing:
            return existing.path
        filename = stem.lower().replace(" ", "-") + ".md"
        if subfolder:
            return self.root / subfolder / filename
        return self.root / filename

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def search(self, query: str, case_sensitive: bool = False) -> list[Note]:
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        results = []
        for note in self._by_stem.values():
            if pattern.search(note.title) or pattern.search(note.body):
                results.append(note)
        return results

    def find_by_tag(self, tag: str) -> list[Note]:
        tag_lower = tag.lower()
        return [n for n in self._by_stem.values() if tag_lower in [t.lower() for t in n.tags]]

    # ------------------------------------------------------------------ #
    # Link analysis
    # ------------------------------------------------------------------ #

    def backlinks(self, target: Note) -> list[Note]:
        """Notes that link to target."""
        target_keys = {target.stem.lower()} | {a.lower() for a in target.aliases}
        results = []
        for note in self._by_stem.values():
            if note.path == target.path:
                continue
            for link_target in note.wikilink_targets:
                if link_target.strip().lower() in target_keys:
                    results.append(note)
                    break
        return results

    def unresolved_links(self) -> list[tuple[Note, str]]:
        """Return (note, unresolved_link_name) pairs."""
        results = []
        for note in self._by_stem.values():
            for target in note.wikilink_targets:
                if self.resolve(target) is None:
                    results.append((note, target))
        return results

    def orphans(self) -> list[Note]:
        """Notes with no inbound or outbound links."""
        linked_to: set[str] = set()
        for note in self._by_stem.values():
            for target in note.wikilink_targets:
                resolved = self.resolve(target)
                if resolved:
                    linked_to.add(resolved.stem.lower())

        results = []
        for note in self._by_stem.values():
            has_out = bool(note.wikilink_targets)
            has_in = note.stem.lower() in linked_to
            if not has_out and not has_in:
                results.append(note)
        return results

    # ------------------------------------------------------------------ #
    # Time-based queries
    # ------------------------------------------------------------------ #

    def recent(self, n: int = 10) -> list[Note]:
        """Most recently modified notes."""
        return sorted(
            self._by_stem.values(),
            key=lambda n: n.path.stat().st_mtime,
            reverse=True,
        )[:n]

    def stale(self, days: int = 30) -> list[Note]:
        """Notes not modified in `days` days, excluding reserved folders."""
        cutoff = date.today() - timedelta(days=days)
        results = []
        for note in self._by_stem.values():
            parts = note.path.relative_to(self.root).parts
            if parts[0].lower() in RESERVED_FOLDERS:
                continue
            mtime = date.fromtimestamp(note.path.stat().st_mtime)
            if mtime < cutoff:
                results.append(note)
        return sorted(results, key=lambda n: n.path.stat().st_mtime)

    # ------------------------------------------------------------------ #
    # Periodic note paths
    # ------------------------------------------------------------------ #

    def daily_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        return self.root / "daily" / f"{d.isoformat()}.md"

    def weekly_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        iso = d.isocalendar()
        return self.root / "weekly" / f"{iso.year}-W{iso.week:02d}.md"

    def monthly_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        return self.root / "monthly" / f"{d.year}-{d.month:02d}.md"

    # ------------------------------------------------------------------ #
    # Inbox
    # ------------------------------------------------------------------ #

    @property
    def inbox(self) -> Path:
        return self.root / "inbox.md"

    # ------------------------------------------------------------------ #
    # Stats
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        notes = self.all_notes()
        total_words = sum(len(n.body.split()) for n in notes)
        all_tags: set[str] = set()
        for n in notes:
            all_tags.update(n.tags)
        return {
            "total_notes": len(notes),
            "total_words": total_words,
            "total_tags": len(all_tags),
            "orphans": len(self.orphans()),
            "unresolved": len(self.unresolved_links()),
        }
