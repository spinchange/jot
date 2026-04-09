# jot

Plain-text markdown notes with wikilinks, tags, tasks, and a one-command publish pipeline — all driven from your terminal.

jot is the reference CLI for **YANP** (Yet Another Note Project) vaults: a plain-text knowledge protocol any tool can speak, including your terminal, your editor, and your AI.

---

## Requirements and Install

- Python 3.10+
- Dependencies are declared in `pyproject.toml`

```sh
# Editable install (development)
pip install -e .

# Or install with pipx for an isolated global CLI
pipx install .
```

> **PyPI name:** `jot-notes` — the CLI command is still `jot`.

---

## Quickstart

```sh
# 1. Point jot at your vault directory
jot config init

# 2. Create a note
jot new "Project Ideas"

# 3. Create today's daily note
jot daily

# 4. List all notes
jot list

# 5. Full-text search
jot search "machine learning"

# 6. See your open tasks across the entire vault
jot tasks --open

# 7. Run a structured query and pipe the results
jot query run --tag project --status active --format plain | xargs grep "TODO"

# 8. Let an AI model access your vault via MCP
jot mcp
```

---

## Command Reference

### Create

| Command | Description |
|---|---|
| `jot new <title>` | Create a new note and open it in your editor |
| `jot open <title>` | Open an existing note (fuzzy match on title) |
| `jot daily` | Open (or create) today's daily note |
| `jot weekly` | Open (or create) this week's weekly note |
| `jot monthly` | Open (or create) this month's monthly note |
| `jot capture <text>` | Append a quick thought to today's daily note without opening an editor |

### Find

| Command | Description |
|---|---|
| `jot list` | List all notes; filter with `--tag`, `--folder`, `--status` |
| `jot search <query>` | Full-text grep across the vault |
| `jot find <pattern>` | Filename/path glob search |
| `jot recent [N]` | Show the N most recently modified notes |
| `jot stale [N]` | Show notes not modified in `staleDays` days |
| `jot preview <title>` | Print a note to stdout with syntax highlighting |
| `jot pick` | Interactive fuzzy picker (requires `fzf`) |

`list`, `search`, `recent`, and `stale` all accept `--format [rich|plain|json]` for scriptable output (see [Pipeable Output](#pipeable-output)).

### Links

| Command | Description |
|---|---|
| `jot links <title>` | Show all wikilinks inside a note |
| `jot backlinks <title>` | Show all notes that link to a note |
| `jot unresolved` | List wikilinks that point to no existing note |
| `jot orphans` | List notes with no inbound or outbound links |
| `jot repair-links <old> <new>` | Rewrite wikilinks after a rename |
| `jot create-unresolved` | Stub out all unresolved link targets |
| `jot graph` | Dump a Mermaid link graph to stdout |

### Tags

| Command | Description |
|---|---|
| `jot tags` | List all tags and their note counts |
| `jot props get <title> <key>` | Read a frontmatter field from a note |
| `jot props set <title> <key> <value>` | Write a frontmatter field |

### Organize

| Command | Description |
|---|---|
| `jot rename <old> <new>` | Rename a note and update all inbound wikilinks |
| `jot merge <source> <target>` | Append source note into target and delete source |
| `jot split <title> <heading>` | Extract a heading section into its own note |
| `jot dedupe` | Report notes with duplicate titles or aliases |
| `jot related <title>` | Show notes sharing the most tags or links |

`rename`, `merge`, and `split` auto-commit to git when the vault is a git repo. Pass `--no-git` to suppress.

### Tasks

| Command | Description |
|---|---|
| `jot tasks [title]` | List GFM checkbox tasks from one note or the whole vault |
| `jot tasks --open` | Show only uncompleted tasks |
| `jot tasks --done` | Show only completed tasks |
| `jot agenda` | Show tasks due today or overdue |

### Views

| Command | Description |
|---|---|
| `jot dashboard` | Overview: recent notes, stale notes, open tasks |
| `jot report` | Vault statistics (note count, tag count, link count) |
| `jot review` | Notes modified in the last 7 days |

### Query

A structured query DSL for filtering, sorting, and composing saved queries.

| Command | Description |
|---|---|
| `jot query run` | Ad-hoc query with filters, sort, limit, and output format |
| `jot query save <name>` | Save a named query to `queries.json` |
| `jot query ls` | List saved queries |
| `jot query exec <name>` | Run a saved query by name |

```sh
# Find active project notes, newest first, as JSON
jot query run --tag project --status active --sort date --format json

# Only notes that link to "Meeting Notes", limited to 10
jot query run --has-link "Meeting Notes" --limit 10

# Save a query for daily use
jot query save inbox --folder inbox --status ""
jot query exec inbox --format plain | xargs -I{} jot open {}

# Full filter reference
jot query run --tag TAG --status STATUS --search TEXT --folder FOLDER \
              --has-link TARGET --limit N --sort (title|date|path) \
              --format (rich|plain|json)
```

### Publish

| Command | Description |
|---|---|
| `jot publish [--output DIR]` | Transform wikilinks to relative markdown links for SSG output |
| `jot publish --clean` | Delete output directory before publishing |
| `jot publish --dry-run` | Preview what would be written without touching disk |

> Quartz users: wikilinks are natively supported — you don't need `publish`.
> Hugo / Eleventy / Jekyll users: run `jot publish` before your site build.

### MCP Server

```sh
jot mcp
```

Starts an [MCP](https://modelcontextprotocol.io) server that exposes your vault to AI models (Claude, GPT-4, etc.). Any MCP-compatible client can then read and write your notes.

**Available tools:**

| Tool | Description |
|---|---|
| `vault_search(query)` | Full-text search; returns path, title, tags, status, snippet |
| `vault_read(path)` | Read a note by vault-relative path; returns frontmatter + body |
| `vault_write(path, body, frontmatter)` | Create or update a note |
| `vault_list(tag, status, folder)` | Filtered note listing |
| `vault_query(tag, status, search, folder, has_link, limit)` | Structured query |
| `vault_backlinks(path)` | Notes that link to the given note |

You can also run the server directly with the `jot-mcp` entry point installed by `pyproject.toml`.

**Claude Desktop** — add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac):
```json
{
  "mcpServers": {
    "jot": {
      "command": "/path/to/python",
      "args": ["-m", "jot.mcp_server"]
    }
  }
}
```

**Claude Code** — run once to register globally:
```sh
claude mcp add --scope user jot -- /path/to/python -m jot.mcp_server
```

Replace `/path/to/python` with the path to the Python interpreter where jot is installed.

### Config

| Command | Description |
|---|---|
| `jot config init` | Interactive first-run setup |
| `jot config show` | Print current configuration |
| `jot config path` | Print the path to `~/.jot/config.json` |

---

## Pipeable Output

`list`, `search`, `recent`, `stale`, and `query run` all accept `--format`:

| Format | Behaviour |
|---|---|
| `rich` (default) | Coloured table in the terminal |
| `plain` | One vault-relative filepath per line, no ANSI — xargs-safe |
| `json` | JSON array of `{path, title, tags, status}` objects |

```sh
# Open every note tagged "inbox" in your editor
jot list --tag inbox --format plain | xargs -I{} jot open {}

# Pipe query results into another tool
jot query run --status draft --format json | jq '.[].path'

# Feed stale notes to a script
jot stale --format plain | while read f; do echo "Review: $f"; done
```

---

## Git Integration

When your vault is a git repository, `rename`, `merge`, and `split` auto-commit after each operation:

```sh
jot rename "Old Title" "New Title"
# → auto-commits: "jot rename: Old Title → New Title"

jot merge "Draft" "Final"
# → auto-commits: "jot merge: Draft → Final"

jot split "Big Note" "Section Heading"
# → auto-commits: "jot split: 'Section Heading' out of Big Note"

# Suppress auto-commit for any of the above
jot rename "Old" "New" --no-git
```

---

## Note Format (YANP)

jot uses **YANP** (Yet Another Note Protocol): plain Markdown with an optional YAML frontmatter block. The spec is published at [spinchange.github.io/yanp](https://spinchange.github.io/yanp/) — any tool that parses YANP can interoperate with a jot vault.

```markdown
---
title: My Note
aliases:
  - my note
  - mnote
tags:
  - project
  - ideas
created: 2024-01-15
modified: 2024-03-20
due: 2024-04-01
scheduled: 2024-03-25
status: active
author: alice
---

Body text here. Link to another note with [[Other Note]] or [[Other Note|custom label]].

Inline tags also work: #project #ideas
```

### Frontmatter Fields

| Field | Type | Description |
|---|---|---|
| `title` | string | Display name; defaults to filename stem if absent |
| `aliases` | list of strings | Alternative names for wikilink resolution |
| `tags` | list of strings | Hierarchical tags (e.g. `project/active`) |
| `created` | date (`YYYY-MM-DD`) | Creation date; set automatically by `jot new` |
| `modified` | date (`YYYY-MM-DD`) | Last-modified date; updated on save |
| `due` | date (`YYYY-MM-DD`) | Task due date; surfaced by `jot agenda` |
| `scheduled` | date (`YYYY-MM-DD`) | Scheduled start date |
| `status` | string | Arbitrary status string; filterable with `jot list --status` |
| `author` | string | Note author |

### Wikilink Syntax

```
[[Note Title]]               — links to the note whose title or alias matches
[[Note Title|Display Text]]  — same, but renders with custom label
```

Inline tags (`#tagname`, `#category/sub`) are also scanned and indexed alongside frontmatter tags.

---

## Configuration

Config lives at `~/.jot/config.json`. Run `jot config init` to create it interactively.

```json
{
  "vault": "/home/alice/notes",
  "editor": "code",
  "noOpen": false,
  "staleDays": 30,
  "dashboardLimit": 10,
  "templates": "/home/alice/notes/_templates",
  "queries": "/home/alice/notes/_queries",
  "author": "alice",
  "hostname": "mymachine"
}
```

### Config Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `vault` | string (path) | _(required)_ | Absolute path to your notes directory |
| `editor` | string | auto-detected | Editor command (`code`, `nvim`, `vim`, etc.) |
| `noOpen` | boolean | `false` | If `true`, suppress opening the editor after note creation |
| `staleDays` | integer | `30` | Notes unmodified longer than this appear in `jot stale` |
| `dashboardLimit` | integer | `10` | Max notes shown in each `jot dashboard` section |
| `templates` | string (path) | _(optional)_ | Directory of Markdown templates for `jot template` |
| `queries` | string (path) | _(optional)_ | Path to `queries.json` for `jot query` saved queries |
| `author` | string | `$USER` / `$USERNAME` | Default author written into new notes |
| `hostname` | string | system hostname | Machine identifier written into new notes |
| `ignoreFolders` | list of strings | `[]` | Subfolders excluded from vault indexing |
