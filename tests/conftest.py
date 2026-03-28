"""Shared fixtures for jot tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jot.config import Config


# ------------------------------------------------------------------ #
# Temp vault builder
# ------------------------------------------------------------------ #


def make_note(root: Path, rel: str, content: str) -> Path:
    """Write a note at root/rel, creating parent dirs as needed."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture()
def vault_root(tmp_path: Path) -> Path:
    """A small but representative YANP vault."""

    make_note(tmp_path, "alpha.md", """\
---
title: Alpha
date: 2024-01-01
tags:
  - project
  - important
status: active
---

# Alpha

Body of alpha. Links to [[Beta]] and [[gamma]].

#inline-tag

- [ ] open task
- [x] done task
""")

    make_note(tmp_path, "beta.md", """\
---
title: Beta
aliases:
  - B Note
date: 2024-02-01
tags:
  - project
status: draft
---

# Beta

Beta body. Links back to [[Alpha|see alpha]].
""")

    make_note(tmp_path, "gamma.md", """\
---
title: Gamma
date: 2024-03-01
due: 2099-12-31
---

# Gamma

Gamma has no outbound links.

- [ ] gamma task
""")

    make_note(tmp_path, "orphan.md", """\
---
title: Orphan
---

No links in or out.
""")

    make_note(tmp_path, "broken-links.md", """\
---
title: Broken Links
---

Links to [[NonExistent]] and [[AlsoMissing]].
""")

    make_note(tmp_path, "daily/2024-01-15.md", """\
---
date: 2024-01-15
tags:
  - daily
---

# Daily Note - 2024-01-15
""")

    make_note(tmp_path, "inbox.md", "# Inbox\n\n")

    return tmp_path


@pytest.fixture()
def cfg(vault_root: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Config pointing at vault_root, with a patched config dir."""
    config = Config(vault=str(vault_root), editor="", no_open=True)

    # Patch Config.load to return our test config
    monkeypatch.setattr("jot.config.Config.load", classmethod(lambda cls: config))

    return config
