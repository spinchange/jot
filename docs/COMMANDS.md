# jot — Command Reference

This document provides a full list of commands available in `jot`.

## General Commands

- `jot --version`: Show the version and exit.
- `jot --help`: Show help messages and exit.

## Create & Open

- `jot new [TITLE]`: Create a new note with the specified title.
- `jot open [TITLE]`: Open an existing note (or create it if it doesn't exist).
- `jot daily [DATE]`: Open today's daily note (or a specific date: YYYY-MM-DD).
- `jot weekly [DATE]`: Open this week's weekly note (or a specific date: YYYY-MM-DD).
- `jot monthly [DATE]`: Open this month's monthly note (or a specific date: YYYY-MM-DD).

## Finding Notes

- `jot list`: List all notes in the vault.
  - `--tag, -t [TAG]`: Filter by tag.
  - `--folder, -f [FOLDER]`: Filter by subfolder.
  - `--status, -s [STATUS]`: Filter by frontmatter status.
  - `--format [rich|plain|json]`: Output format (default: `rich`).
- `jot search [QUERY]`: Full-text search across all notes.
  - `--format [rich|plain|json]`: Output format.
- `jot find [PATTERN]`: Find notes by filename glob pattern.
- `jot recent [N]`: Show the N most recently modified notes (default: 10).
  - `--format [rich|plain|json]`: Output format.
- `jot stale`: List notes not modified recently.
  - `--format [rich|plain|json]`: Output format.
- `jot preview [TITLE]`: Print a note's content to the terminal with syntax highlighting.
- `jot pick [QUERY]`: Fuzzy-pick a note and print its path (useful for piping).

`plain` format emits one vault-relative filepath per line (xargs-safe). `json` emits a JSON array of `{path, title, tags, status}` objects.

## Capture

- `jot capture [TEXT]`: Append a timestamped bullet to `inbox.md`.
  - `--daily, -d`: Append to today's daily note instead of inbox.
  - `--inbox, -i`: Append to `inbox.md` (default).
  - Can read from stdin: `echo "thought" | jot capture`.

## Links & Graph

- `jot links [TITLE]`: List all outbound wikilinks from a note.
- `jot backlinks [TITLE]`: List all notes that link to a given note.
- `jot unresolved`: List all unresolved wikilinks in the vault.
- `jot repair-links [OLD_NAME] [NEW_NAME]`: Replace all wikilinks from `OLD_NAME` to `NEW_NAME` across the vault.
- `jot create-unresolved`: Create stub notes for every unresolved wikilink.
- `jot graph`: Output a link graph in Mermaid format.
- `jot orphans`: List notes with no inbound or outbound links.

## Tags & Properties

- `jot tags [TITLE]`: Show tags for a note, or list all tags vault-wide if no title is provided.
- `jot props show [TITLE]`: Show all frontmatter fields for a note.
- `jot props set [TITLE] [KEY] [VALUE]`: Set a frontmatter field on a note.
- `jot props unset [TITLE] [KEY]`: Remove a frontmatter field from a note.
- `jot props add [TITLE] [KEY] [VALUE]`: Append a value to a list frontmatter field.
- `jot props remove [TITLE] [KEY] [VALUE]`: Remove a value from a list frontmatter field.

## Organization

- `jot rename [OLD_TITLE] [NEW_TITLE]`: Rename a note and update all inbound wikilinks. Auto-commits to git.
  - `--no-git`: Suppress auto-commit.
- `jot merge [SOURCE_TITLE] [TARGET_TITLE]`: Merge source note into target note and update links. Auto-commits to git.
  - `--no-git`: Suppress auto-commit.
- `jot split [TITLE] [HEADING]`: Split a section out of a note into a new note. Auto-commits to git.
  - `--no-git`: Suppress auto-commit.
- `jot dedupe`: Find and report notes with duplicate titles or stems.
- `jot related [TITLE]`: Show notes most related to a given note (shared tags + common links).

## Tasks & Agenda

- `jot tasks [TITLE]`: List GFM checkbox tasks from a note or the entire vault.
  - `--open`: Show only uncompleted tasks.
  - `--done`: Show only completed tasks.
- `jot agenda`: Show notes with due or scheduled dates in the upcoming window (default: 7 days).

## Views & Reports

- `jot dashboard`: Show a summary dashboard of the vault.
- `jot report`: Show notes modified in a date range.
  - `--since [DATE]`
  - `--until [DATE]`
- `jot review`: Show notes that are drafts, have no tags, or are empty.

## Query

Structured query DSL for filtering, sorting, and saving reusable queries.

- `jot query run`: Run an ad-hoc query against the vault.
  - `--tag [TAG]`: Filter by tag.
  - `--status [STATUS]`: Filter by status.
  - `--search [TEXT]`: Full-text filter.
  - `--folder [FOLDER]`: Filter by subfolder.
  - `--has-link [TARGET]`: Only notes that wikilink to TARGET.
  - `--limit [N]`: Return at most N results.
  - `--sort [title|date|path]`: Sort order.
  - `--format [rich|plain|json]`: Output format.
- `jot query save [NAME]`: Save current filter flags as a named query.
- `jot query ls`: List all saved queries.
- `jot query exec [NAME]`: Run a saved query by name.

## Templates

- `jot template list`: List available templates.
- `jot template apply [TEMPLATE_NAME] [NOTE_TITLE]`: Create a note from a template.
- `jot template show [TEMPLATE_NAME]`: Print a template's content.

## MCP Server

- `jot mcp`: Start the MCP server for AI model vault access (requires `pip install jot[mcp]`).

Starts a FastMCP stdio server exposing six vault tools to any MCP-compatible client (Claude Desktop, Claude Code, etc.):

| Tool | Description |
|---|---|
| `vault_search(query)` | Full-text search; returns path, title, tags, status, snippet |
| `vault_read(path)` | Read a note by vault-relative path; returns frontmatter + body |
| `vault_write(path, body, frontmatter)` | Create or update a note |
| `vault_list(tag, status, folder)` | Filtered note listing |
| `vault_query(tag, status, search, folder, has_link, limit)` | Structured query |
| `vault_backlinks(path)` | Notes that link to the given note |

## Configuration

- `jot config show`: Print current configuration.
- `jot config path`: Print the path to the config file (`~/.jot/config.json`).
- `jot config init`: Interactive first-run setup.

### Config Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `vault` | string (path) | _(required)_ | Absolute path to your notes directory |
| `editor` | string | auto-detected | Editor command (`code`, `nvim`, etc.) |
| `noOpen` | boolean | `false` | Suppress opening the editor after note creation |
| `staleDays` | integer | `30` | Notes unmodified longer than this appear in `jot stale` |
| `dashboardLimit` | integer | `5` | Max notes shown per section in `jot dashboard` |
| `templates` | string (path) | _(optional)_ | Directory of Markdown templates for `jot template` |
| `queries` | string (path) | _(optional)_ | Path to `queries.json` for saved queries |
| `author` | string | `$USER` / `$USERNAME` | Default author written into new notes |
| `hostname` | string | system hostname | Machine identifier written into new notes |
| `ignoreFolders` | list of strings | `[]` | Subfolders excluded from vault indexing |

## Publish

- `jot publish`: Transform wikilinks to relative markdown links and write to an output directory.
  - `--output, -o [DIR]`: Output directory (default: `./dist`).
  - `--clean`: Delete output directory before publishing.
  - `--dry-run`: Preview what would be written without touching disk.
