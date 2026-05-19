---
mode: synthesis
date: 2026-05-19
sources: [deep-claude-obsidian, deep-pageindex, deep-tencentdb-agent-memory]
status: active
---

# Synthesis — Retrieval SOTA vs EgoVault (3 deep dives, 2026-05-19)

## The one emergent thesis

**Three independent, recent, well-starred projects all reject *pure cosine
similarity* as the retrieval primitive for compiled knowledge.** They are not
three features to cherry-pick — they are three points on ONE design space:

| Project | Replacement for cosine | EgoVault tier it maps to |
|---|---|---|
| claude-obsidian | Deterministic structural precedence: `hot.md`→`index.md`→typed pages, LLM synthesizes | curate() **tier-0** (no embeddings, no LLM for retrieval) |
| TencentDB-Agent-Memory | **BM25 + cosine fused via RRF** (same sqlite-vec stack) | curate() **tier-0** (deterministic, hybrid recall) |
| PageIndex | LLM **reasons over a TOC/tree** instead of similarity | curate() **tier-1** (reasoning retrieval, long sources) |

This directly explains and answers EgoVault **finding E** (cosine ranking
directional-but-imprecise on real French data, exact-topic source ranked #2 /
missed): the SOTA consensus is **hybrid + structural retrieval**, NOT "get a
better embedding model". The embedding becomes a recall prefilter, not the
ranker.

## Architecture validation (not just borrowing)

TencentDB-Agent-Memory independently uses the **same stack (SQLite +
sqlite-vec)** and the **same tier split** as EgoVault: lower tiers in the DB
for retrieval, upper tiers as human-readable Markdown for density + white-box
inspection. claude-obsidian independently ships the exact Karpathy-LLM-Wiki
"compounding wiki, not ephemeral chat" thesis EgoVault's VISION states.
EgoVault's Knowledge Compiler architecture is **convergent SOTA, not
idiosyncratic** — strong external validation.

## Actionable, ranked

1. **Search-quality track, experiment #1 — RRF(BM25, cosine).** Highest
   value / lowest risk. BM25 via SQLite **FTS5** (already have SQLite), fuse
   with existing cosine via Reciprocal Rank Fusion, deterministic, fits
   curate() tier-0, **no embedding-model swap, no new dep**. Test against the
   `2026-05-17-real-ingest-test-results.md` finding-E corpus and queries.
   This is the concrete next step for the search-quality track.
2. **Reframe the curate() tier-1 spec.** The deferred "curate() tier 1 = LLM
   synthesis of cosine top-K" should be re-examined against "LLM reasons over
   a structural index" (PageIndex) before it's planned. → a curate()-retrieval
   **brainstorm** is now warranted (was: just implement tier-1).
3. **Deterministic structural tier-0 (claude-obsidian).** A materialized
   `index`/`hot` digest of the notes table, queried before cosine. Bigger
   change; do after #1 proves the hybrid baseline.

## What this does NOT change

- Tier-0-deterministic / LLM-as-accelerator principle: reinforced by all 3.
- Human approval gate, MCP-first, provider-agnostic (F5): keep — the agentic
  auto-capture models (TencentDB/OpenClaw) are explicitly rejected.
- No new runtime deps for experiment #1 (FTS5 is in stdlib SQLite).

## Pointers

- Deep cards: `deep-claude-obsidian-2026-05-19.md`,
  `deep-pageindex-2026-05-19.md`, `deep-tencentdb-agent-memory-2026-05-19.md`
- Feeds: search-quality track (finding E) + a new curate()-retrieval brainstorm
  before the curate() tier-1 plan.
