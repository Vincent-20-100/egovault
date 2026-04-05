# 8. Large format handling — blind spot

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 8.1 Current behavior

When a source exceeds `large_format_threshold_tokens`:
1. The pipeline runs normally (chunks created, embeddings computed, source → `rag_ready`)
2. **After success**, a `LargeFormatError` exception is raised
3. The API catches this and stores it as a job error

## 8.2 Problems

1. **Using an exception for expected behavior is a code smell.** The pipeline succeeded — the source is `rag_ready` and fully functional for RAG. The exception communicates "note generation would be too expensive" but it's not an error.

2. **The user receives an error for a successful operation.** From the API: `status: "failed"`, `error: "LargeFormatError"`. Confusing — the source is actually usable.

3. **No guidance on what to do next.** The user has a large source that's indexed but has no note. What are the options? No UI, no message, no workflow guides them.

4. **File size limits exist (security spec H2.13: 500MB audio, 100MB PDF) but token-level limits are separate.** A 50MB PDF could have 200k tokens. The file size limit passes but the token threshold triggers. These are different concerns handled at different levels with no unified strategy.

5. **No option to proceed anyway.** Some users may want to attempt note generation on large sources, accepting the cost. There's no override.

## 8.3 Needs dedicated brainstorming

This is an architectural decision point with multiple valid approaches:

- **Option A:** Replace exception with a return field (`source.large_format = True`). Job status = `success`. Frontend/CLI shows "Source indexed for RAG. Too large for automatic note generation — write one manually or provide a summary."
- **Option B:** Add compression/chunking strategies that allow note generation from summaries of summaries (hierarchical summarization).
- **Option C:** Add a `force_generate: bool` parameter that lets the user attempt generation anyway with a cost warning.
- **Option D:** Split large sources into logical parts (chapters, segments) before processing.

**The brainstorming should address:**
- How `LargeFormatError` should be represented (exception vs. return value vs. status)
- The relationship between file size limits (H2.13) and token limits (`large_format_threshold_tokens`)
- User-facing messaging (what does the user see? what can they do?)
- Whether hierarchical summarization belongs in current scope or is a future extension
- Human-in-the-loop for compression decisions (owner mentioned this explicitly)

**For now:** document this as a known blind spot. Do not attempt to fix without a brainstorming session.
