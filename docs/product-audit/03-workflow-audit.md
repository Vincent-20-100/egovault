# 3. Workflow audit

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 3.1 Current state

All 3 workflows (`ingest_youtube`, `ingest_audio`, `ingest_pdf`) follow the same pattern:

```
register source → extract text → chunk → embed chunks → rag_ready
```

They are well-structured but stop before note creation (by design — see section 2.1).

## 3.2 Issues

| Issue | Severity | Notes |
|-------|----------|-------|
| **Significant code duplication** | Low (future brainstorm) | Steps 2-3 (chunk + embed loop) are identical across all three workflows. A shared `_embed_pipeline()` would reduce maintenance. Not blocking — address in a cleanup pass. |
| **`LargeFormatError` raised after success** | Medium (see section 8) | The pipeline succeeds (source = `rag_ready`, chunks created), then raises an exception. This is a flow control issue. |
| **No `ingest_web` workflow** | Medium | Web articles are the most common source for developers. Mentioned as "coming soon" in README, not specced. See section 11 for extraction strategy. |
| **No `ingest_docx` / `ingest_epub` / `ingest_pptx`** | Medium | Common document formats with no ingestion path. Trivial to add once extraction provider exists (see section 11). Could be unified into a single `ingest_document` workflow. |
| **No `ingest_image` workflow** | Low-Medium | Screenshots, whiteboard photos, slides as images. Requires OCR (Tier 2 extraction). No fallback possible without OCR. |
| **No `ingest_text` workflow** | Low | For plain text / copy-paste. Partially covered by `create_note` via MCP (user writes directly). Lower priority. |
| **No `ingest_playlist` workflow** | Low | YouTube playlist → batch `ingest_youtube`. Needs partial failure handling. |
| **No re-ingestion path** | Low (future brainstorm) | If subtitles improve or transcription settings change, there's no way to re-process a source. |

## 3.3 Immediate action items (for Priority A plan)

None — workflows work correctly for their current scope. The gap is downstream (note creation + embedding), not in the workflows themselves.
