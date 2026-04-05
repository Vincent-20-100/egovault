# 2. Critical gap: MCP-driven note creation flow

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 2.1 Design intent (validated by owner)

```
User's LLM (Claude, GPT, Cursor...)
    ↓ connects via MCP
EgoVault MCP server
    ↓ LLM calls tools autonomously
search → read source/chunks → draft note → create_note → finalize_source
```

EgoVault does NOT summarize. The LLM does. EgoVault provides atomic tools. This is a deliberate architectural choice — not a missing feature.

## 2.2 What is broken today (Priority A — blocking)

| Gap | Impact | Fix |
|-----|--------|-----|
| **`embed_note` does not exist** | `notes_vec` is never populated. `search(mode="notes")` returns 0 results forever. The note-level RAG promised in README is dead. | Create `tools/text/embed_note.py` OR integrate embedding into `create_note` post-save hook. Also wire it into the API `PATCH /notes/{uid}` flow (re-embed on body change). |
| **`create_note` MCP tool doesn't trigger `embed_note`** | Even after fix above, MCP-created notes won't be searchable at note level unless embedding is automatic. | Make note embedding automatic on creation and on update (in `create_note.py` and `update_note.py`). |
| **MCP tool descriptions are too terse** | The LLM doesn't know the expected workflow. It sees 12 isolated tools but no guidance on sequencing. Example: `create_note` docstring says "Validate and create a note" — doesn't mention it should be called after reading source content. | Enrich every `@mcp.tool()` docstring with usage context. Add a `get_workflow_guide` tool or a system prompt resource that describes the intended MCP workflow. |
| **No MCP setup documentation** | A developer cannot connect EgoVault to Claude Desktop, Cursor, Windsurf, or any MCP client without guessing. The README says "point it to `mcp/server.py`" — insufficient. | Write setup guides per client (Claude Desktop JSON config, Cursor config, generic stdio). Add to README Quick Start. |
| **`get_source` not exposed via MCP** | The LLM can search and find chunks, but cannot read the full source record (title, URL, transcript). It's blind to the context it needs to write a good note. | Add `get_source(uid)` to `mcp/server.py`. |
| **`list_notes` / `list_sources` not exposed via MCP** | The LLM cannot browse. It can only search semantically. "Show me my last 10 notes" or "list sources tagged X" is impossible. | Add `list_notes(limit, offset, filters)` and `list_sources(limit, offset, filters)` to MCP. |
| **No `update_note` via MCP** | `update_note.py` exists as a tool but is not exposed in `mcp/server.py`. The LLM can create but not edit notes. | Expose `update_note` in MCP server. |

## 2.3 Internal LLM path (Priority B — future work)

**Description:** The API/frontend could generate notes autonomously without MCP, using a configured LLM provider (`infrastructure/llm_provider.py`). This would enable a "one-click ingest" experience: `POST /ingest/youtube` → source + note, no MCP needed.

**Implementation sketch:**
- Implement `summarize.py` (currently empty stub) using `llm_provider`
- Add an optional `auto_generate_note: bool` parameter to ingest workflows
- If enabled: after `rag_ready`, call `summarize` → `create_note` → `embed_note` → `finalize_source`
- Human-in-the-loop: the note is created with a `draft` status, user validates before `vaulted`
- Falls back gracefully if no LLM configured (same as today — stops at `rag_ready`)

**Depends on:** all Priority A fixes (especially `embed_note`).

**Priority assessment:** If fixing Priority A gaps is quick (estimated: 1-2 sessions), Priority B can be bundled in the same plan since `summarize.py` already exists as a stub and `llm_provider.py` is already implemented. The marginal cost is low. If Priority A is complex, defer B.

**Recommended position in roadmap:** after CLI (users need a surface to trigger it), before frontend (frontend will want a "generate note" button).
