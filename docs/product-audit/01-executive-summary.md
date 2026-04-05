# 1. Executive summary

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

The architecture is rigorous — hexagonal layers, Pydantic contracts, clean separation of concerns. The README is compelling and the specs are thorough. However, the project has a critical gap between its promise and its current state:

**The core value loop is broken.** EgoVault's promise is: ingest → structured note → searchable forever. Today, the pipeline stops at `rag_ready` (chunks embedded). The step from source to note depends on the LLM calling `create_note` via MCP, but:
- Notes created via MCP are never embedded (`notes_vec` stays empty → `mode="notes"` returns nothing)
- MCP tool descriptions don't guide the LLM through the expected workflow
- There's no MCP setup documentation for any client

**No user-facing surface exists beyond MCP.** No CLI, no frontend (specced but not built). A developer who clones the repo cannot do anything without writing Python or configuring an MCP client with zero guidance.

**The spec implementation order optimizes internals before delivering user value.** Monitoring, reranking, cache, and benchmark all improve a pipeline that doesn't yet produce notes. Reprioritization is needed.

**Owner context (important for future readers):**
- The original design intent is MCP-first: the user's own LLM (Claude, GPT, etc.) orchestrates note creation by calling EgoVault tools. EgoVault provides the building blocks, not the intelligence.
- The owner has a data background, not fullstack — CLI and guided setup are essential.
- The README is intentionally aspirational (guides LLM-assisted development). A beta disclaimer is sufficient.
