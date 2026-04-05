# 4. Tools audit

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 4.1 Existing tools — assessment

All implemented tools have clear responsibilities, Pydantic contracts, and `@loggable` decorators. No tool overlaps.

## 4.2 Missing tools

| Tool | Priority | Rationale |
|------|----------|-----------|
| **`embed_note`** (or auto-embed in `create_note`) | A — blocking | `notes_vec` is never populated. Note-level search is dead. |
| **`delete_source` / `delete_note`** | High | Cannot delete anything. Accumulation without cleanup is an anti-pattern. `pending_deletion` status exists but nothing implements it. |
| **`list_sources` / `list_notes`** (as MCP tools) | High | LLM cannot browse, only search. Basic CRUD read operations missing from MCP. |
| **`get_source`** (as MCP tool) | High | LLM is blind to source metadata and transcripts. |
| **`update_note`** (as MCP tool) | High | Tool exists but not exposed in MCP. LLM can create but not edit. |
| **`summarize`** | B — future | Empty stub. Needed for internal LLM path. Not needed for MCP-first design. |
| **`suggest_tags`** | Medium | Query `notes_vec` with source/note content to propose existing tags by semantic similarity. Helps the LLM (or user) stay consistent with vault taxonomy. Useful via MCP before `create_note`. |
| **`export_bundle`** | Medium | Export a selection of notes (by tags, date range, source_type, note_type) to markdown bundle / ZIP / JSON. Currently only single-note export exists (Typst, Mermaid). |
| **`import_notes`** | Medium | Import existing .md files (Notion export, other Obsidian vaults, Bear) → parse frontmatter → `create_note` + `embed_note`. Essential for adoption — nobody starts from zero. |
| **`merge_notes`** | Low | Combine 2+ notes on the same topic into one consolidated note, preserving linked sources. |
| **`link_notes`** | Low | Create explicit relationships between notes beyond shared tags. Wiki-links style, native to Obsidian. |

## 4.4 Current tool limitations

| Tool | Limitation | Impact |
|------|-----------|--------|
| **`chunk_text`** (`tools/text/chunk.py`) | Word-based split with fixed window. No awareness of paragraph/section/chapter boundaries. Cuts mid-sentence. | Chunk quality degrades on structured documents. A structural chunker (respecting paragraph and heading boundaries) would improve both embedding quality and RAG retrieval. |
| **`_extract_pdf_text`** (`workflows/ingest_pdf.py`) | Uses `pypdf` — text layer only. Returns empty string on scanned PDFs, ignores images, loses table structure. | See section 11 for tiered extraction architecture. |

## 4.5 Rechunk capability (missing)

If `system.yaml:chunking.size` changes, all existing sources retain their old chunk boundaries. There is no way to re-chunk a source without deleting and re-ingesting it. A `rechunk_source(uid)` tool would delete old chunks, re-split the stored transcript, and re-embed — avoiding full re-ingestion.

**Priority:** Low. Only becomes relevant once chunk quality improvements (structural chunking) are implemented.

## 4.6 Tools needing enriched MCP descriptions

Every MCP tool docstring should include:
- **What it does** (current — adequate)
- **When to use it** (missing — e.g., "Call this after reading source content to create a structured note")
- **What to call next** (missing — e.g., "After create_note, call finalize_source to mark the source as vaulted")

This is critical for LLM-driven orchestration. Without guidance, the LLM will use tools in random order.
