# EgoVault — Future Work & Ideas Backlog

Ideas, suggestions, and work items not yet specced. This file collects everything that is **not implemented and has no approved spec**.

Work items with an approved spec are listed in `CLAUDE.md` (Progress status section).
Visual references and inspiration: `docs/references/`.

---

## Decided — not yet implemented

### Vault sync watcher (bidirectional)
`watchdog` (event-driven) for local dev + force-sync at app startup for cross-platform reliability. The `uid` is the anchor: renaming a file = slug update in DB, never a duplicate. Currently `vault_writer.py` handles DB→vault on explicit calls. The vault→DB watcher is the next work item.

### Re-embedding on model change
`scripts/maintenance/reembed_all.py`: drops `chunks_vec` and `notes_vec`, recreates them with the new dimension, re-embeds all chunks from `sources.transcript`, updates `db_metadata`. Triggered manually by the user after a mismatch is detected at startup. **Mandatory prerequisite before adding any embedding provider beyond Ollama.**

---

## Still open

### Multi-user
`user_id` column in all tables vs. separate DB instance per user. Separate instance is simpler for a personal PKM — recommended default.

### Migration of legacy Markdown notes
Script to import an existing Markdown vault into the EgoVault DB schema. Not blocking — existing notes and the new vault can coexist during the transition. To be built together with the user when the need arises.

### Open question: LLM-initiated rating
Should the `rating` field be proposable by the LLM (subject to human validation), or remain strictly user-only? Current position: user-only, to preserve the value of an authentic human signal. To be reconsidered if a suggestion workflow proves useful.

---

## Future work items (non-priority)

### Multi-provider embedding
Add OpenAI / alternative Ollama models. Requires the full re-embedding system (see section above). Do not implement partially.

### Full bidirectional watcher
Currently vault→DB only. DB→vault is handled by `vault_writer.py` on explicit calls. Full bidirectional sync (programmatic edits reflected live in Obsidian) is a future feature.

### `scripts/maintenance/sync_vectors.py`
Orphan cleanup script for `chunks_vec` and `notes_vec` after bulk deletions. Low priority until large-scale source deletion is a real use case.

### Generation templates library
Initial set of templates derived from the initial workflows (A/B/C → synthese-source, reflexion, concept). Community templates shareable as `.yaml` files. Not blocking — `standard.yaml` ships with the repo.

### `pending_deletion` workflow
UI for reviewing sources marked `pending_deletion` before permanent removal (DB + vectors + media). Requires frontend or a dedicated CLI command. Human confirmation is mandatory — no automatic deletion.

### Map-reduce summarization (`workflows/ingest_large.py`)
Fully independent workflow for automatic note generation from large sources (summarize chunks → summarize summaries → generate note). Completely separate from the standard ingest workflows. **Not an immediate priority** — the large format policy (section 4.1 of ARCHITECTURE.md) covers the immediate need without this complexity.

### Monitoring dashboard
SQL queries over `tool_logs` exposed as a simple web view or CLI report. The data is already there — just needs a reader. Partially covered by the monitoring API (spec 7.3) but a dedicated frontend dashboard remains to be built.

### LLM-as-judge for benchmark
`LLMJudgeEvaluator`: the LLM receives a `(query, result)` pair and assigns a relevance score. Interfaces defined in the benchmark framework, not implemented (YAGNI). To be wired up when qualitative measurement is needed.

### Promoting golden dataset from the UI
Allow the user to promote a perfect response from the interface to the benchmark golden dataset. DB tables reserved (`benchmark_golden`), endpoints stubbed (`/benchmark/promote`). Not implemented.

### Semantic cache — pre-warming
Pre-warm the cache on frequent queries at startup. Future extension of the semantic cache.

### Hosting
Hosted Next.js deployment for multi-device access. Requires auth (currently no auth — local MVP only) and migration from SQLite → PostgreSQL + media → S3.

---

## RAG improvements (inspired by Advanced RAG architecture)

*Reference: `docs/references/classic-vs-advanced-rag.png`*

### Metadata enrichment
Enrich chunks with source metadata (source_type, date, tags, URL) before embedding. Improves retrieval relevance by giving the vector search more contextual signal. Currently chunks contain raw text only.

### Hybrid search (Dense + Sparse / BM25)
Combine dense vector search (current) with sparse keyword search (BM25). Dense search excels at semantic similarity; sparse search captures exact matches (proper nouns, acronyms, technical terms) that embeddings may miss. Libraries: `rank-bm25`, `tantivy` (Rust-based), or SQLite FTS5 (built-in).

### Relevance filtering
Post-retrieval filtering based on a configurable similarity threshold. Currently all top-K results are returned regardless of distance. A threshold would filter out low-confidence matches, reducing noise in search results.

### Context fusion
Combine chunks from multiple sources into a coherent context window before LLM generation. Currently each chunk is returned independently. Fusion would group related chunks, deduplicate overlapping content, and present a unified context to the LLM.

---

## Architecture pivot — Knowledge compiler + Agent retrieval (2026-03-31)

*Inspired by Andrej Karpathy's LLM Wiki pattern and the agentify project.*

### The insight

RAG retrieves chunks then forgets. A knowledge compiler **accumulates and densifies**
knowledge over time. EgoVault already has the seed: `generate_note_from_source` digests
a source into a structured note. But it stops there — search still returns raw chunks.

### Two-layer architecture

**Layer 1 — RAG on sources (keep as-is)**
Chunk → embed → search over raw source material. Good for precise retrieval,
exact quotes, specific facts. This is the current system and it works.

**Layer 2 — Compiled knowledge on notes (new)**
Notes are the distilled, human-validated knowledge. As notes accumulate, they form
a compiled knowledge base that is denser and more reliable than raw chunks.
Notes get re-embedded as they evolve (already implemented: `embed_note`).
A "big note" could be a synthesis of multiple sources — not just one source per note.

### Agent-based retrieval (the real evolution)

Instead of dumping top-K chunks into the context window:

1. **Context agent** reads the current conversation to understand what the user actually needs
2. **Retrieval agent** searches both layers (source chunks + compiled notes), scores relevance
3. **Synthesis agent** produces a **short list or mini-synthesis** from retrieved material
4. Only the **useful, distilled result** enters the conversation context window

This is fundamentally different from RAG:
- RAG: query → retrieve chunks → stuff into context → hope the LLM figures it out
- Agent retrieval: understand intent → search → synthesize → inject only what's relevant

### Confidence scores + temporal decay

Each fact (chunk, note, synthesis) carries a confidence score:
- Raw chunk from a single source: base confidence
- Confirmed by multiple sources: confidence increases
- Contradicted by newer source: confidence decreases
- Older facts without reconfirmation: gradual decay
- Human-validated notes: high confidence, slow decay

This mirrors human memory: repeated exposure strengthens, time without use weakens.

### Connection to our own dev workflow

Our 3-file system (CLAUDE.md, PROJECT-STATUS.md, SESSION-CONTEXT.md) is exactly this pattern
applied to development:
- CLAUDE.md = compiled knowledge (high confidence, slow change)
- SESSION-CONTEXT.md = working memory (rewritten, consolidated each session)
- PROJECT-STATUS.md = state (factual, updated frequently)

EgoVault could offer the same pattern to its users for their own knowledge.

### Refined architecture — Librarian agent pattern

The RAG layer is NOT dead — it changes client. Instead of serving the user directly,
it serves a **librarian agent** that is far better at querying, cross-referencing,
and filtering than any human.

```
User ↔ Conversational agent (no DB access, clean context window)
              ↓ "I need info about X"
        Librarian agent
              ├── searches compiled notes (fast, dense, reliable)
              ├── if insufficient → queries RAG chunks (precise, verbatim)
              ├── can run MULTIPLE RAG queries internally
              ├── cross-references, deduplicates, detects contradictions
              ├── decides: return existing note? compile on-the-fly? cite a chunk?
              ↓
        Returns to conversational: sorted, synthesized, minimal context
```

**Why this works:**
- Conversational agent context window stays clean — only relevant material enters
- RAG precision is preserved (exact quotes, specific facts) but noise is filtered out
- Librarian can compile multi-source syntheses that don't exist as notes yet
- Each layer has exactly one job: converse, curate, or store

**What this changes for EgoVault:**
- `search` tool becomes an internal tool for the librarian, not a user-facing endpoint
- New tool: `curate(query, conversation_context) → CuratedContext`
- The curated context may contain: note excerpts, chunk quotes, on-the-fly synthesis
- User-facing search becomes "ask the librarian" not "query the vector DB"

### What this does NOT mean

- Not replacing RAG — giving it a smarter client (the librarian)
- Not requiring a rewrite — incremental, builds on existing tools
- Not blocking current work — this is a future direction, not a prerequisite

### Prerequisites

- Unified ingest workflow (in progress)
- VaultContext refactoring (pending)
- Multi-source note synthesis tool (new, not yet specced)
- Agent framework for retrieval (new, needs dedicated brainstorm)

---
