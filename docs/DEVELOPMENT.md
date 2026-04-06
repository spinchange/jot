# jot — Development and Status

This document tracks the current status, recent changes, and historical development log of the `jot` tool.

## Current Build Status (v0.1.0)

`jot` is in a fully functional state, with parity across all 34 core commands as specified in the vault documentation. It is extensively tested and validated against real-world vault data.

### Feature Coverage

| Module | Core Functionality | Commands |
|--------|---------------------|----------|
| **create** | Periodic & generic note creation | `new` `open` `daily` `weekly` `monthly` |
| **find** | Search and discovery | `list` `search` `find` `recent` `stale` `preview` `pick` |
| **capture** | Quick intake | `capture` (with stdin pipe support) |
| **links** | Vault-wide link analysis | `links` `backlinks` `unresolved` `repair-links` `create-unresolved` `graph` `orphans` |
| **tags** | Frontmatter & inline metadata | `tags` `props` (show/set/unset/add/remove) |
| **organize** | Note refactoring | `rename` `merge` `split` `dedupe` `related` |
| **tasks** | Checklist management | `tasks` `agenda` |
| **views** | Vault-wide reporting | `dashboard` `report` `review` |
| **template** | Note scaffolding & queries | `template` (list/apply/show) `query` (list/run/save) |
| **config** | User settings | `config` (show/init/path) |
| **publish** | Export to markdown | `publish` |

---

## Development Log

### 2026-03-29 — author field + frontmatter indentation fix

- **author field:** Semantically distinct from `source` (human | ai | mixed). `author` carries the specific agent/human name for precise attribution.
- **YAML Indentation:** Implemented `_IndentedDumper` to ensure frontmatter lists are indented under their keys, matching the Obsidian/YANP standard.
- **Vault Docs Updated:** Relevant specification documents in the vault were updated to reflect these changes.

### 2026-03-28 — Project Start and Core Build

- **Session 1:** Full parity with the original 33 commands from `minimal-notes`, plus the `publish` command. Implemented core classes (`Vault`, `Note`, `Config`).
- **Session 2:** YANP spec compliance fix. Updated `Vault.resolve()` to ensure wikilinks correctly resolve via the `title` frontmatter field, not just filenames.
- **Session 3:** Bug fixes for note renaming and title management. Added support for capturing content from stdin via the `capture` command.
- **Testing Suite:** Comprehensive test suite written (116 tests total), covering CLI, vault logic, note properties, and frontmatter parsing.
- **Encoding Fix:** Reconfigured stdout to UTF-8 to correctly render em-dashes and other special characters on Windows Terminal.

---

## Future Roadmap

1. **Stale Fix:** Interactive mode for `jot stale` to help clean up or refresh old notes.
2. **Export:** Additional export formats for more complex site generation workflows.
3. **TUI Dashboard:** A persistent terminal UI for real-time vault status.
4. **CI/CD:** Automated testing pipelines for cross-platform validation.
5. **Renaming:** Potential rename from `jot` to `note` for a more seamless CLI experience.
