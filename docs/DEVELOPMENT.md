# jot — Development and Status

This document tracks the current status, recent changes, and historical development log of the `jot` tool.

## Current Build Status (v0.5.0)

`jot` is in a fully functional state with 189 passing tests. All core commands are implemented and tested. The MCP server exposes vault operations to AI models.

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
| **template** | Note scaffolding | `template` (list/apply/show) |
| **query** | Structured vault queries | `query run` `query save` `query ls` `query exec` |
| **mcp** | AI model integration | `mcp` (FastMCP server over stdio) |
| **config** | User settings | `config` (show/init/path) |
| **publish** | Export to markdown or HTML | `publish` |

---

## Development Log

### 2026-04-11 — Interactive stale, touch, batch, SSG link styles, HTML export

- **`jot stale --interactive` (`-i`):** Steps through stale notes one by one. Per-note prompt: `(o)pen (t)ouch (d)elete (s)kip (q)uit`. Open delegates to configured editor.
- **`Note.touch()`:** New method — updates `modified` frontmatter field to today and saves. Used by `--interactive` and `--batch touch`.
- **`jot stale --batch touch|delete`:** Non-interactive batch action. `touch` updates modified dates on all stale notes; `delete` prompts once then removes all. Mutually exclusive with `--interactive`.
- **`jot publish --ssg hugo|eleventy|jekyll`:** SSG-specific link style for markdown output. `hugo` = no extension, `eleventy`/`jekyll` = `.html`. Default unchanged (`.md` links).
- **`jot publish --format html`:** Standalone HTML export via optional `markdown` package (`pip install jot[html]`). Writes `.html` files with minimal embedded CSS. Wikilinks resolve to `.html` hrefs. Mutually exclusive with `--ssg`.
- **Test count:** 170 → 189 (19 new tests).
- **Version bump:** 0.4.0 → 0.5.0.

### 2026-04-09 — MCP tests, optional dep fix, version bump, MCP wiring

- **MCP tests:** 40 new tests covering all six MCP tools (`vault_search`, `vault_read`, `vault_write`, `vault_list`, `vault_query`, `vault_backlinks`). Total test count: 164.
- **Optional dependency:** Moved `mcp>=1.0` from hard `dependencies` to `[project.optional-dependencies]`. Install with `pip install jot[mcp]`. Graceful error if `mcp` not installed.
- **MCP wiring:** Registered `jot mcp` with Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`) and Claude Code (`claude mcp add --scope user`).
- **Vault configured:** `~\Documents\yanpvault-nova-chris` set as the active vault.
- **Version bump:** 0.1.0 → 0.4.0.

### 2026-04-08 — Git integration, pipeable output, query DSL, MCP server (parallel worktree session)

Four features developed simultaneously in separate git worktrees and merged to master:

- **Git integration (`ws-git-integration`):** `rename`, `merge`, and `split` auto-commit to git after each operation. Pass `--no-git` to suppress. Rollback safety on failure.
- **Pipeable output (`ws-pipeable-output`):** `--format [rich|plain|json]` flag on `list`, `search`, `recent`, and `stale`. `plain` emits one filepath per line (xargs-safe); `json` emits structured arrays.
- **Query DSL (`ws-query-system`):** New `jot query` subcommand group. `query run` supports `--tag`, `--status`, `--search`, `--folder`, `--has-link`, `--limit`, `--sort`, and `--format`. `query save` / `query ls` / `query exec` for named saved queries.
- **MCP server (`ws-mcp-server`):** `jot mcp` starts a FastMCP stdio server exposing six vault tools to any MCP-compatible AI client.
- **Session ended with Bun crash** — `git_util.py` was lost before the worktree commit and recovered in a follow-up commit.

### 2026-03-29 — author field + frontmatter indentation fix

- **author field:** Semantically distinct from `source` (human | ai | mixed). `author` carries the specific agent/human name for precise attribution.
- **YAML Indentation:** Implemented `_IndentedDumper` to ensure frontmatter lists are indented under their keys, matching the Obsidian/YANP standard.

### 2026-03-28 — Project Start and Core Build

- **Session 1:** Full parity with the original 33 commands from `minimal-notes`, plus the `publish` command. Implemented core classes (`Vault`, `Note`, `Config`).
- **Session 2:** YANP spec compliance fix. Updated `Vault.resolve()` to ensure wikilinks correctly resolve via the `title` frontmatter field, not just filenames.
- **Session 3:** Bug fixes for note renaming and title management. Added support for capturing content from stdin via the `capture` command.
- **Testing Suite:** Comprehensive test suite written (124 tests at the time), covering CLI, vault logic, note properties, and frontmatter parsing.
- **Encoding Fix:** Reconfigured stdout to UTF-8 to correctly render em-dashes and other special characters on Windows Terminal.

---

## Future Roadmap

1. ~~**Stale Fix:** Interactive mode for `jot stale` to help clean up or refresh old notes.~~ ✓ Done (v0.5.0)
2. ~~**Export:** Additional export formats for more complex site generation workflows.~~ ✓ Done (v0.5.0 — SSG link styles + HTML)
3. **TUI Dashboard:** A persistent terminal UI for real-time vault status.
4. **CI/CD:** Automated testing pipelines for cross-platform validation.
