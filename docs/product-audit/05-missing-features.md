# 5. Missing features — prioritized

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## Tier 1 — Blocking (must fix before meaningful use)

| # | Feature | Impact | Cost | Notes |
|---|---------|--------|------|-------|
| 1 | **`embed_note` + auto-embed on create/update** | Critical | Simple | Unblocks `mode="notes"` search entirely |
| 2 | **MCP tool completeness** (get_source, list_notes, list_sources, update_note) | Critical | Simple | Without these, MCP-driven workflow is crippled |
| 3 | **MCP tool descriptions enriched** (workflow guidance in docstrings) | Critical | Simple | The LLM needs to understand the intended flow |
| 4 | **MCP setup documentation** (Claude Desktop, Cursor, generic) | Critical | Simple | Zero users can connect today without guessing |
| 5 | **CLI** (`egovault ingest <url/file>`, `egovault search "query"`, `egovault status`) | Critical | Simple | No human-facing surface exists. Owner confirmed this is an oversight. |

## Tier 2 — High value (first wave after Tier 1)

| # | Feature | Impact | Cost | Notes |
|---|---------|--------|------|-------|
| 6 | **Delete operations** (delete source, delete note, purge chunks) | High | Simple | Cannot clean up the vault today |
| 7 | **Quick Start end-to-end** ("ingest your first video in 3 commands") | High | Simple | Current Quick Start stops at `pytest` |
| 8 | **Health check at startup** (Ollama running? Model pulled? Config valid?) | High | Simple | Cryptic errors on first run otherwise |
| 9 | **`embedding.dims` fix** (extract from semantic cache spec, do first) | High | Simple | Cross-cutting fix buried in an optimization spec |
| 10 | **Internal LLM path (Priority B)** | High | Medium | One-click ingest → note. Low marginal cost if done with Tier 1. |

## Tier 3 — Medium value (second wave)

| # | Feature | Impact | Cost | Notes |
|---|---------|--------|------|-------|
| 11 | **`ingest_web`** (article web extraction) | Medium | Medium | Most common source type for devs. Not specced yet. See section 11. |
| 12 | **Example data / seed vault** | Medium | Simple | Empty vault is confusing for first run |
| 13 | **Configuration wizard** (interactive CLI for first setup) | Medium | Simple | user.yaml + install.yaml creation guided |
| 14 | **README beta disclaimer** | Low | Trivial | Honest about current state without removing aspirational content |
| 15 | **Extraction provider** (see section 11) | Medium | Medium | Tiered architecture: builtin → markitdown → chandra. Unlocks DOCX/EPUB/PPTX/web ingestion. |
| 16 | **`suggest_tags`** via MCP | Medium | Simple | Semantic search on `notes_vec` for tag consistency. One query + ranking. |
| 17 | **`export_bundle`** (selective vault export) | Medium | Simple | Filter notes by tags/date/type → ZIP/markdown/JSON. All read logic exists. |

## Tier 4 — Future brainstorming sessions

| # | Topic | Notes |
|---|-------|-------|
| 18 | Workflow deduplication (shared `_embed_pipeline`) | Low priority cleanup |
| 19 | Re-ingestion / source update path | Design needed |
| 20 | Large format handling redesign (see section 8) | Needs dedicated brainstorming |
| 21 | `ingest_text` (plain text / copy-paste) | Low priority, partially covered by MCP |
| 22 | Extraction provider — tiered architecture (see section 11) | Dedicated brainstorming: `superpowers:brainstorming` |
| 23 | Provider coherence — unified API key design (see section 12) | Architectural decision: one key for all external services |
| 24 | `import_notes` (Notion, Obsidian, Bear) | Adoption enabler. Needs frontmatter parsing design. |
| 25 | `merge_notes` / `link_notes` | Vault maintenance tools. Low priority. |
| 26 | Structural chunker (paragraph/heading-aware) | Improves chunk quality. See section 4.4. |
| 27 | `ingest_image` (OCR-based, requires Tier 2 extraction) | Depends on chandra or equivalent. No CPU fallback. |
| 28 | `ingest_playlist` (batch YouTube) | Loop on `ingest_youtube` with partial failure handling. |
