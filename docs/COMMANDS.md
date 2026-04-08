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
- `jot search [QUERY]`: Full-text search across all notes.
- `jot find [PATTERN]`: Find notes by filename glob pattern.
- `jot recent [N]`: Show the N most recently modified notes (default: 10).
- `jot stale`: List notes not modified recently.
- `jot preview [TITLE]`: Print a note's content to the terminal with syntax highlighting.
- `jot pick [QUERY]`: Fuzzy-pick a note and print its path (useful for piping).

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

- `jot rename [OLD_TITLE] [NEW_TITLE]`: Rename a note and update all inbound wikilinks.
- `jot merge [SOURCE_TITLE] [TARGET_TITLE]`: Merge source note into target note and update links.
- `jot split [TITLE] [HEADING]`: Split a section out of a note into a new note.
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

## Templates & Queries

- `jot template list`: List available templates.
- `jot template apply [TEMPLATE_NAME] [NOTE_TITLE]`: Create a note from a template.
- `jot template show [TEMPLATE_NAME]`: Print a template's content.
- `jot query list`: List saved queries.
- `jot query run [NAME]`: Run a saved query by name.
- `jot query save [NAME]`: Save a query for later reuse.

## Configuration

- `jot config show`: Print current configuration.
- `jot config path`: Print the path to the config file.
- `jot config init`: Interactive first-run setup.

## Publish

- `jot publish`: Transform wikilinks to relative links and write to an output directory.
  - `--output, -o [DIR]`: Output directory (default: `./dist`).
  - `--clean`: Delete output directory before publishing.
