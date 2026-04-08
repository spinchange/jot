# jot — Architecture

This document describes the internal structure and design of the `jot` tool.

## Directory Structure

```text
jot/
├── pyproject.toml
├── src/
│   └── jot/
│       ├── __init__.py
│       ├── __main__.py          # Allows `python -m jot`
│       ├── cli.py               # Main CLI entry point, click group definitions
│       ├── config.py            # Config handling (dataclass, JSON load/save)
│       ├── vault.py             # Vault class — vault indexing and wikilink resolution
│       ├── note.py              # Note class — represents a single .md file
│       ├── frontmatter.py       # YAML parsing and writing utilities
│       └── commands/            # Individual CLI command modules
│           ├── __init__.py
│           ├── create.py        # new, open, daily, weekly, monthly
│           ├── find.py          # list, search, find, pick, recent, stale, preview
│           ├── capture.py       # capture
│           ├── links.py         # links, backlinks, unresolved, repair-links, etc.
│           ├── tags.py          # tags, props
│           ├── organize.py      # rename, merge, split, dedupe, related
│           ├── tasks.py         # tasks, agenda
│           ├── views.py         # dashboard, report, review
│           ├── template.py      # template, query
│           ├── config_cmd.py    # config (show/init/path)
│           └── publish.py       # publish
```

## Core Components

### `Config` (`config.py`)

- **Dataclass** representing user settings.
- **Location:** Config is stored at `~/.jot/config.json`.
- **Fields:** `vault`, `editor`, `no_open`, `stale_days`, `dashboard_limit`, `templates`, `queries`.
- **Load/Save:** Handled via `Config.load()` and `Config.save()`.

### `Note` (`note.py`)

- **Representation:** Represents a single `.md` file in the vault.
- **Metadata:** Parsed from YAML frontmatter using `frontmatter.py`.
- **Properties:** Includes `title` (from frontmatter or filename stem), `tags` (union of frontmatter and inline `#tag` patterns), `aliases`, `wikilinks`, and GFM tasks.
- **Operations:** Supports loading, saving, and modifying properties/frontmatter fields.

### `Vault` (`vault.py`)

- **Indexing:** Indexes all `.md` files under the vault root on load.
- **Lookup:** Provides `resolve(name)` for case-insensitive lookup by title, stem, or alias.
- **Analysis:** Performs link analysis (backlinks, unresolved links, orphans) and vault-wide search.
- **Stats:** Computes word counts, tag counts, and other metrics.

## Key Design Decisions

- **CLI Framework:** Built using `click` for command parsing and `rich` for high-quality terminal output (tables, panels, syntax highlighting).
- **Frontmatter Handling:** Uses `PyYAML` to parse and write frontmatter blocks. Custom `_IndentedDumper` ensures compatibility with tools like Obsidian by indenting list items under their keys.
- **Wikilink Format:** Supports standard `[[Note Title]]` and `[[Note Title|Display Text]]`. Resolution is vault-wide and ignores directory nesting.
- **Tag Merging:** Automatically merges tags defined in YAML frontmatter with inline `#tag` and `#tag/subword` patterns found in the body, excluding those within code blocks.
- **Publish Workflow:** The `publish` command performs a safe transformation of wikilinks to standard markdown relative links, writing results to a separate directory without modifying the source vault.

## Dependencies

- **click:** CLI command structure and arguments.
- **PyYAML:** YAML frontmatter parsing and dumping.
- **rich:** Terminal formatting, tables, and color output.
- **Standard Library:** All other functionality uses Python standard libraries.
