# 09 — MCP integration

EgoVault was designed **MCP-first**. The MCP server exposes every tool
individually so any MCP-compatible client (Claude Desktop, Claude Code,
Cursor, Windsurf, …) becomes your LLM front-end — no per-token bill, no
data leaves your machine for "intelligence" work.

> This chapter consolidates and supersedes the older `docs/mcp-setup.md` and
> `docs/mcp/CLIENT-SETUP.md`.

## How it works (10-second model)

```
You (in Claude Desktop) → "ingest this video"
        │
        │   Claude reads the MCP tool list, picks `ingest_youtube`, calls it.
        ▼
   mcp/server.py  → routes to tools/workflows
        │
        ▼
  vault.db + vault/  ← your data, on your machine
```

Your Claude/GPT subscription covers all reasoning. EgoVault provides storage,
search, and pipelines.

## Claude Desktop setup

### 1. Find your config file

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

The repo ships a `claude_desktop_config.json` template at the root — copy
relevant fields into your real file.

### 2. Add the EgoVault server

Merge into the `mcpServers` section:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "C:/Users/YourName/GitHub/Vincent-20-100/egovault/.venv/Scripts/python.exe",
      "args": ["C:/Users/YourName/GitHub/Vincent-20-100/egovault/mcp/server.py"],
      "cwd": "C:/Users/YourName/GitHub/Vincent-20-100/egovault"
    }
  }
}
```

On macOS/Linux, the `command` is `.venv/bin/python` and paths use forward slashes.

### 3. Restart Claude Desktop

Quit and relaunch. In a new conversation, ask: *"What MCP tools are available?"*
You should see the EgoVault tools.

If they don't appear:
- Check Claude Desktop logs (Help → Show logs)
- Try with absolute paths (no `~`, no relative)
- Verify the venv python by running it manually:
  `<venv-python> mcp/server.py --help`

## Claude Code setup

Claude Code does **NOT** read `claude_desktop_config.json`. It uses a
project-local `.mcp.json` (versioned) at the repo root:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "python",
      "args": ["mcp/server.py"],
      "cwd": "."
    }
  }
}
```

This file already exists in the EgoVault repo. Restart Claude Code in the
repo to pick it up.

You can also register an EgoVault MCP server **user-globally** via:

```bash
claude mcp add -s user egovault python <abs-path>/mcp/server.py
```

That makes the server available in any Claude Code session, not just inside
the EgoVault repo.

## Tools exposed by the MCP server

Snapshot of the 22+ tools (see `mcp/server.py` for the authoritative list):

### Ingest

- `ingest_youtube(url)`
- `ingest_audio(file_path, language="fr")`
- `ingest_pdf(file_path)`
- `ingest_text(content, title)`
- `ingest_web(url)`

### Retrieval

- `search(query, mode="chunks"|"notes", filters=None)` — raw top-K
- `curate(query, filters=None, limit=5)` — **Librarian** (the preferred entry point)

### Notes

- `generate_note_from_source(uid, template="standard")` — LLM drafts a note
- `create_note(content, source_uid=None)` — manual note creation
- `update_note(uid, fields)`
- `finalize_source(uid)` — mark a source as fully processed
- `get_note(uid)` / `list_notes(...)` / `get_source(uid)` / `list_sources(...)`

### Export

- `export_typst(uid, lang="fr", font=...)` — generate a Typst document from a note
- `export_mermaid(...)` — generate a Mermaid diagram

### Destructive (safety-gated)

These appear **only when `allow_destructive_ops: true`** in `user.yaml`:

- `delete_source(uid, hard=False)` / `restore_source(uid)`
- `delete_note(uid, hard=False)` / `restore_note(uid)`
- `purge_sources()` / `purge_notes()`

> **Safety principle:** the default config (`allow_destructive_ops: false`)
> means a runaway LLM cannot delete your vault. Flip it to `true` only for
> a specific session/task that needs deletion, then revert.

## The vault-usage rule for MCP clients

`.claude/rules/vault-usage.md` is shipped to instruct the LLM how to behave
when EgoVault is connected. Key directives:

- Before answering a knowledge question → call `curate()` first
- Use `search` only for verbatim quoting
- Tag conventions: kebab-case, French, no accents
- After a rich conversation → propose to ingest the URL or create a note

Claude Code and other MCP-aware clients honor this rule automatically when
loaded.

## Monitoring MCP runs

Every MCP call is tracked via a `run_id` (UUID4, propagated through
`contextvars`). See `workflow_runs` in `.system.db`:

```bash
egovault status                 # shows recent runs
# or via the FastAPI:
curl http://localhost:8000/monitoring/runs?limit=10
```

Token counts and provider for each LLM call are extracted from the response
and stored in `tool_logs` — useful to track Anthropic API spend.

## What's next

- [10 — Obsidian](10-obsidian.md): your notes as a graph
- [04 — Providers](04-providers.md): the MCP-only persona deep-dive
- [12 — Troubleshooting](12-troubleshooting.md): "MCP tools don't appear"
