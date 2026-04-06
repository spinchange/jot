# jot — YANP Vault CLI

`jot` is a powerful, yet lightweight Command Line Interface (CLI) for managing a "Yet Another Note-taking Protocol" (YANP) compliant markdown vault. It supports plain markdown notes, wikilinks, frontmatter-based metadata, task management, and static site generation (SSG) publishing.

## Features

- **Wikilinks:** Support for `[[Note Title]]` and `[[Note Title|Display Text]]` with case-insensitive, vault-wide resolution.
- **Frontmatter:** Built-in support for YAML frontmatter for metadata (title, tags, date, status, author, etc.).
- **Tags:** Merged view of frontmatter tags and inline `#tag` and `#tag/subtag` patterns.
- **Task Management:** Extract GFM checkbox tasks from individual notes or the entire vault.
- **Agenda:** Track due and scheduled dates across all notes.
- **Capture:** Quick timestamped bullet capture to `inbox.md` or daily notes, including stdin pipe support.
- **Periodic Notes:** Easy creation and access to daily, weekly, and monthly notes.
- **Organization:** Command-line tools for `rename` (with backlink repair), `merge`, `split`, and `dedupe`.
- **Templates:** Create new notes from flexible templates with variable substitution (`{{title}}`, `{{date}}`, etc.).
- **Views:** Dashboard summary of vault stats, recent notes, stale notes, and upcoming agenda.
- **Publish:** Transform wikilinks into relative markdown links for use with static site generators.

## Installation

`jot` requires Python 3.10 or higher.

```bash
# Clone the repository
git clone https://github.com/spinchange/jot.git
cd jot

# Install in editable mode
pip install -e .
```

## Getting Started

### 1. Configuration

Initialize your vault configuration:

```bash
jot config init
```

This will guide you through setting your vault directory, preferred editor, and other settings. Configuration is stored in `~/.jot/config.json`.

### 2. Basic Commands

- **Create a new note:** `jot new "My New Note"`
- **Open an existing note:** `jot open "My Note"`
- **List all notes:** `jot list`
- **Search vault content:** `jot search "search query"`
- **Quick capture:** `echo "thought" | jot capture`
- **View dashboard:** `jot dashboard`

### 3. Periodic Notes

- **Daily note:** `jot daily`
- **Weekly note:** `jot weekly`
- **Monthly note:** `jot monthly`

## Documentation

For more detailed information, see:

- [Architecture](./docs/ARCHITECTURE.md)
- [Command Reference](./docs/COMMANDS.md)
- [Development Log](./docs/DEVELOPMENT.md)

## Testing

`jot` comes with a comprehensive test suite using `pytest`.

```bash
pytest
```

## Specification Compliance

`jot` is built to comply with the **Yet Another Note-taking Protocol (YANP)** specification for markdown-based personal knowledge management. It ensures consistent frontmatter handling and vault-wide wikilink resolution.

---
License: MIT (or as specified in the project)
