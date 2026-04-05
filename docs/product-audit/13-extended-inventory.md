# 13. Extended tools & workflows inventory

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 13.1 Summary of all identified tools

This section consolidates all tools discussed across the audit, including those from sections 4, 11, and 12.

### Vault tools (`tools/vault/`)

| Tool | Status | Priority | Description |
|------|--------|----------|-------------|
| `create_note` | Implemented | — | Create a note from LLM/user input |
| `update_note` | Implemented (not in MCP) | High | Edit an existing note |
| `search` | Implemented | — | Semantic search on chunks and notes |
| `finalize_source` | Implemented | — | Mark source as vaulted |
| `delete_source` / `delete_note` | Missing | High | CRUD completeness. Purge chunks + embeddings. |
| `suggest_tags` | Missing | Medium | Semantic similarity on `notes_vec` for tag suggestions |
| `export_bundle` | Missing | Medium | Selective export (tags/date/type → ZIP/markdown/JSON) |
| `import_notes` | Missing | Low-Medium | Import .md from other tools (Notion, Obsidian, Bear) |
| `merge_notes` | Missing | Low | Consolidate 2+ notes into one |
| `link_notes` | Missing | Low | Explicit inter-note relationships (wiki-links) |

### Text tools (`tools/text/`)

| Tool | Status | Priority | Description |
|------|--------|----------|-------------|
| `chunk` | Implemented | — | Word-based splitting with fixed window |
| `embed` | Implemented | — | Embed a text string via provider |
| `summarize` | Stub | B — future | LLM-powered summarization for internal path |
| `embed_note` | Missing | A — blocking | Embed note body into `notes_vec` |
| structural chunker | Missing | Low | Paragraph/heading-aware chunking (improves quality) |
| `rechunk_source` | Missing | Low | Re-chunk an existing source with new settings |

### Media tools (`tools/media/`)

| Tool | Status | Priority | Description |
|------|--------|----------|-------------|
| `transcribe` | Implemented | — | Audio/video → text via configured engine |
| `compress` | Implemented | — | Audio compression |
| `fetch_subtitles` | Implemented | — | YouTube subtitle extraction |
| `extract_audio` | Implemented | — | Video → audio extraction |

### Export tools (`tools/export/`)

| Tool | Status | Priority | Description |
|------|--------|----------|-------------|
| `typst` | Implemented | — | Single note → .typ document |
| `mermaid` | Implemented | — | Tag/note graph → Mermaid diagram |

## 13.2 Summary of all identified workflows

| Workflow | Status | Priority | Extraction tier needed | Notes |
|----------|--------|----------|----------------------|-------|
| `ingest_youtube` | Implemented | — | N/A (subtitles/transcription) | — |
| `ingest_audio` | Implemented | — | N/A (transcription) | — |
| `ingest_pdf` | Implemented | — | Tier 0 (pypdf). Upgradeable to Tier 1-2. | See section 11. |
| `ingest_web` | Missing | Medium | Tier 0 (`bs4`) or Tier 1 (markitdown) | HTML articles. Most common source type. |
| `ingest_docx` | Missing | Medium | Tier 0 (`python-docx`) or Tier 1 (markitdown) | Word documents. |
| `ingest_epub` | Missing | Low-Medium | Tier 0 (`ebooklib`) or Tier 1 (markitdown) | Ebooks. |
| `ingest_pptx` | Missing | Low | Tier 0 (`python-pptx`) or Tier 1 (markitdown) | Presentations (often low text density). |
| `ingest_image` | Missing | Low | Tier 2 only (chandra) | No CPU fallback. Screenshots, whiteboard photos. |
| `ingest_text` | Missing | Low | N/A (direct input) | Plain text / copy-paste. Partially covered by MCP. |
| `ingest_playlist` | Missing | Low | N/A | Batch `ingest_youtube` with partial failure handling. |
| `ingest_document` | Missing (design Q) | Medium | Auto-detect | Unified workflow for PDF/DOCX/EPUB/PPTX. See 10.10. |

## 13.3 Prioritized implementation sequence

```
Already done:    ingest_youtube, ingest_audio, ingest_pdf
                     ↓
Tier 1 fixes:    embed_note, MCP completeness, CLI, delete ops
                     ↓
Extraction provider brainstorming (superpowers:brainstorming)
                     ↓
Quick wins:      ingest_web (Tier 0: bs4 fallback, Tier 1: markitdown)
                 ingest_docx (Tier 0: python-docx, Tier 1: markitdown)
                 suggest_tags, export_bundle
                     ↓
Medium effort:   ingest_epub, ingest_pptx, import_notes
                 structural chunker
                     ↓
Advanced:        ingest_image (Tier 2: chandra)
                 merge_notes, link_notes, ingest_playlist
```
