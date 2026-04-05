# 10. Open questions for future brainstorming

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

These questions are documented here for future `superpowers:brainstorming` sessions. They should NOT be answered during implementation planning — they require dedicated design thinking.

## 10.1 Large format strategy
See section 8. Full brainstorming needed on error representation, compression, hierarchical summarization, and human-in-the-loop decisions.

## 10.2 Workflow deduplication
The chunk + embed loop is identical across `ingest_youtube`, `ingest_audio`, `ingest_pdf`. Extract to a shared `_embed_pipeline()`? Or keep the duplication for readability? This is a style decision, not urgent.

## 10.3 Re-ingestion path
If YouTube subtitles improve, or transcription settings change, how does the user re-process a source? Delete and re-ingest? Update in place? This needs a design decision.

## 10.4 Provider management and coherence
Dedicated CLI script to configure/change providers (LLM, embedder, transcriber, reranker, **extractor**). Already mentioned in CLAUDE.md future work. Needs brainstorming on: unified abstraction, hot-swap from frontend, OpenRouter support. Security guardrails (G6.1-G6.9) apply. **Critical constraint:** provider coherence — see section 12. A user paying for one external service should not need a second API key for a different feature.

## 10.5 Frontend UX/UI
Navigation, dashboard, ingest (screening + drag & drop), notes, search, chat stub. Already mentioned in CLAUDE.md future work. Depends on MCP flow fix + CLI being done first.

## 10.6 `ingest_web` design
Web article extraction: which library (readability, trafilatura, newspaper3k)? How to handle paywalls, dynamic content, cookie walls? Same pipeline after extraction? **Update:** markitdown handles HTML→Markdown natively (see section 11). This simplifies the library choice if markitdown is adopted as Tier 1 extraction provider.

## 10.7 MCP system prompt / resource
Should EgoVault provide a system prompt resource via MCP that explains to the LLM how to use the vault effectively? This would replace enriched docstrings with a single coherent guide. Could include example workflows, best practices, and vault conventions.

## 10.8 Extraction provider architecture
See section 11. Dedicated brainstorming needed on: tiered fallback strategy, image handling (storage, linking in notes, captions as chunks), provider configuration in `system.yaml`, and how extraction quality impacts downstream chunking and embedding.

## 10.9 Image handling in notes
When a source contains images (PDF diagrams, web article illustrations), how should they be represented?
- **Option A:** Images extracted and referenced in the note markdown (`![caption](media/slug/fig.png)`). Obsidian renders natively.
- **Option B:** Image captions embedded as searchable chunks, images stored but not linked in notes.
- **Option C:** Hybrid — transcript includes image references, captions are chunked for RAG, note author (LLM or user) decides which images to keep.
- Depends on extraction provider tier: Tier 0-1 (pypdf/markitdown) extract no or basic images; Tier 2 (chandra) extracts + captions.

## 10.10 Unified `ingest_document` workflow
Should the individual `ingest_pdf`, `ingest_docx`, `ingest_epub`, `ingest_pptx` workflows be merged into a single `ingest_document` workflow that auto-detects format and delegates to the extraction provider? Pro: less code, one entry point. Con: format-specific logic (e.g., PDF page ranges, EPUB chapters) may need specialized handling.
