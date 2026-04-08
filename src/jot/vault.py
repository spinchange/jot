"""Vault — indexes all notes in a YANP vault directory."""

from __future__ import annotations

import re
from collections import defaultdict
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
        self._notes: list[Note] = []
        self._by_stem: dict[str, list[Note]] = defaultdict(list)
        self._by_title: dict[str, list[Note]] = defaultdict(list)
        self._by_alias: dict[str, list[Note]] = defaultdict(list)
        self._ignored: frozenset[str] = RESERVED_FOLDERS

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls, root: Path, ignore: set[str] | None = None) -> "Vault":
        v = cls(root)
        v._ignored = RESERVED_FOLDERS | frozenset(s.lower() for s in (ignore or set()))
        v.reload()
        return v

    def reload(self) -> None:
        self._notes.clear()
        self._by_stem.clear()
        self._by_title.clear()
        self._by_alias.clear()
        for path in sorted(self.root.rglob("*.md")):
            try:
                note = Note.load(path)
            except Exception:
                continue
            self._notes.append(note)
            self._by_stem[note.stem.lower()].append(note)
            self._by_title[note.title.lower()].append(note)
            for alias in note.aliases:
                self._by_alias[alias.lower()].append(note)

        # Deterministic conflict handling: most recently modified note wins.
        for mapping in (self._by_stem, self._by_title, self._by_alias):
            for notes in mapping.values():
                notes.sort(key=lambda n: (n.path.stat().st_mtime, str(n.path)), reverse=True)

    # ------------------------------------------------------------------ #
    # Lookup
    # ------------------------------------------------------------------ #

    def resolve(self, name: str) -> Note | None:
        """Resolve a wikilink name using YANP precedence: title, alias, then stem."""
        key = name.strip().lower()
        if not key:
            return None
        return (
            self._first(self._by_title.get(key))
            or self._first(self._by_alias.get(key))
            or self._first(self._by_stem.get(key))
        )

    def get(self, stem: str) -> Note | None:
        return self._first(self._by_stem.get(stem.lower()))

    def all_notes(self) -> list[Note]:
        return list(self._notes)

    def resolves_to(self, name: str, target: Note) -> bool:
        resolved = self.resolve(name)
        return resolved is not None and resolved.path == target.path

    @staticmethod
    def _first(notes: list[Note] | None) -> Note | None:
        if not notes:
            return None
        return notes[0]

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
        for note in self._notes:
            if pattern.search(note.title) or pattern.search(note.body):
                results.append(note)
        return results

    def find_by_tag(self, tag: str) -> list[Note]:
        tag_lower = tag.lower()
        return [n for n in self._notes if tag_lower in [t.lower() for t in n.tags]]

    # ------------------------------------------------------------------ #
    # Link analysis
    # ------------------------------------------------------------------ #

    def backlinks(self, target: Note) -> list[Note]:
        """Notes that link to target."""
        results = []
        for note in self._notes:
            if note.path == target.path:
                continue
            for link_target in note.wikilink_targets:
                if self.resolves_to(link_target, target):
                    results.append(note)
                    break
        return results

    def unresolved_links(self) -> list[tuple[Note, str]]:
        """Return (note, unresolved_link_name) pairs."""
        results = []
        for note in self._notes:
            for target in note.wikilink_targets:
                if self.resolve(target) is None:
                    results.append((note, target))
        return results

    def orphans(self) -> list[Note]:
        """Notes with no inbound or outbound links."""
        linked_to: set[Path] = set()
        for note in self._notes:
            for target in note.wikilink_targets:
                resolved = self.resolve(target)
                if resolved:
                    linked_to.add(resolved.path)

        results = []
        for note in self._notes:
            has_out = bool(note.wikilink_targets)
            has_in = note.path in linked_to
            if not has_out and not has_in:
                results.append(note)
        return results

    # ------------------------------------------------------------------ #
    # Time-based queries
    # ------------------------------------------------------------------ #

    def recent(self, n: int = 10) -> list[Note]:
        """Most recently modified notes."""
        return sorted(
            self._notes,
            key=lambda n: n.path.stat().st_mtime,
            reverse=True,
        )[:n]

    def stale(self, days: int = 30) -> list[Note]:
        """Notes not modified in `days` days, excluding reserved folders."""
        cutoff = date.today() - timedelta(days=days)
        results = []
        for note in self._notes:
            parts = note.path.relative_to(self.root).parts
            if parts[0].lower() in self._ignored:
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
