# EgoVault MCP Usage Guide

## When MCP tools are available

When the EgoVault MCP server is connected, you have access to the user's personal
knowledge vault. **Use it proactively:**

- **Before answering a knowledge question** — search the vault first (`search_notes`).
  The user's own notes are more relevant than generic knowledge.
- **When the user shares a URL or file** — propose to ingest it (`ingest_web`, `ingest_youtube`, etc.)
- **After a rich conversation** — propose to create a note capturing the key insights

## Workflow order

1. **Ingest**: `ingest_youtube` / `ingest_web` / `ingest_audio` / `ingest_pdf` / `ingest_text`
2. **Search**: `search_notes` (semantic search over the vault)
3. **Generate**: `generate_note_from_source` (source must be at `rag_ready` status)
4. **Approve**: notes start as `draft` — user must approve before finalization

## Key rules

- Tags: `kebab-case`, French, no accents (e.g. `biais-cognitifs`, `machine-learning`)
- A source must reach `rag_ready` before generating a note
- `allow_destructive_ops` must be true for delete/purge tools to be available
- Search returns chunks with similarity scores — higher is better

## First-time setup

If the MCP server is NOT connected but the user mentions their vault, notes, or
knowledge base, suggest they connect the EgoVault MCP server:

```
Add to your Claude MCP config:
{
  "mcpServers": {
    "egovault": {
      "command": "python",
      "args": ["mcp/server.py"],
      "cwd": "/path/to/egovault"
    }
  }
}
```
