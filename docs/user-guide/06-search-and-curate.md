# 06 — Search and curate

This is the chapter you'll reread most.

## Mental model — three tiers

| Tier | What it returns | LLM needed? | Status |
|---|---|:-:|---|
| **0 — deterministic Librarian** | sorted raw results from notes + chunks, with truncation | no | shipped (`curate()`) |
| **1 — LLM synthesis** | tier-0 + LLM dedupes/selects/synthesizes a coherent text | yes | open redesign (Q #7) |
| **2 — agentic** | full agent loop, multi-call reasoning | yes | not on roadmap |

Today, when you say "search" you mean tier-0 + optional hybrid retrieval. The
deferred tier-1 brainstorm (open question 7 in SESSION-CONTEXT) is being
informed by the 2026-05-19 SOTA synthesis (`docs/.../research/synthesis-retrieval-sota-2026-05-19.md`).

## What `curate()` does (tier 0)

```
curate(query, filters?, limit=5) →
   1. embed query (via ctx.embed)
   2. retrieve notes (top-K via cosine, optionally + BM25 fused via RRF)
   3. count "relevant" notes (distance < escalation_max_distance)
   4. if < escalation_min_notes  →  retrieve chunks too (same query)
   5. merge: notes first, chunks second; truncate each item's content
   6. return CuratedContext(synthesis, sources, confidence=None, query)
```

The default behavior is **notes-first**: chunks only fill in when the notes
tier is empty or sparse. This is the Knowledge Compiler thesis in action —
compiled knowledge beats raw chunks when it exists.

### The two escalation knobs

```yaml
# system.yaml
curate:
  escalation_min_notes: 3              # if < N notes pass the distance gate, escalate
  escalation_max_distance: 0.5         # cosine distance threshold for "relevant"
```

Real-corpus calibration (25 FR notes, see
`.meta/audits/2026-05-20-real-notegen-test-results.md`):
- Relevant notes typically land at distance **0.27–0.40**.
- The default `0.5` is comfortable — escalation almost never fires when notes
  exist for the topic.
- If escalation always fires, lower it (more permissive on what counts as relevant).
- If you want **only** notes (never chunks), set it to `2.0` (max cosine
  distance) — then chunks become impossible.

## Hybrid retrieval (RRF + BM25) — the headline feature

**Shipped 2026-05-21. Opt-in, default OFF.**

### The problem it solves (finding E)

On real French data, pure cosine sometimes misses the exact-topic source.
Concrete example:

- Query: *"fragilité des systèmes centralisés"*
- Cosine top-3 over the notes: `Resilience...`, `Failles royaute archaique`,
  `Effets des systemes centralises` — **the obvious note
  `Fragilité des systèmes centralisés` is OUTSIDE top-3.**

Why? Cosine on `nomic-embed-text` clusters distances narrowly (~0.37–0.39),
and the embedding doesn't always reward exact-keyword overlap on FR.

### The mechanism

Hybrid runs **two retrievals in parallel** and fuses them:

```
Cosine (sqlite-vec)     ranks by semantic similarity
                  ↘
                    Reciprocal Rank Fusion (k=60)  →  one unified ranked list
                  ↗
BM25 (SQLite FTS5)      ranks by lexical / keyword overlap
```

RRF score per doc = Σ over both lists of `1 / (k + rank_in_that_list)`. A
doc top-3 in EITHER list bubbles to the top of the fused list. Top-3 in
BOTH explodes upward.

### What changes when you flip it on

```yaml
# system.yaml
curate:
  use_hybrid_retrieval: true
```

`curate()` then calls `search_notes_hybrid` and `search_chunks_hybrid` instead
of the pure-cosine variants. Same return type — but BM25-only results carry
`distance = 2.0` (sentinel) to signal "lexical recall, not cosine-relevant"
without breaking the cosine-threshold logic in `escalation_max_distance`.

### Empirical impact

On the 25-note real corpus, 4 thematic queries:
- **Q "fragilité systèmes centralisés"** (the finding-E case):
  - Cosine: exact-topic note missed top-3
  - Hybrid: **exact-topic note promoted to rank 2** (via BM25, distance=2.0
    sentinel) ✅ — the precise mitigation
- **Q "méthode scientifique + décentralisation"**: lexical-exact `Méthode
  scientifique` bumped to rank 1 (defensible)
- **Q "fourmis sans chef"**: no change (cosine already top1)
- **Q "desire path"**: no change (EN/FR vocabulary mismatch BM25 can't bridge)

**1 big win, 1 reorder, 2 neutral, 0 regression.** Full results:
`.meta/audits/2026-05-21-rrf-hybrid-experiment-results.md`.

### When to enable

| Enable when… | Leave off when… |
|---|---|
| Your queries mix concepts AND exact keywords (proper nouns, terms) | Pure conceptual queries — cosine handles them better |
| You ingest content in languages where embedding models are weaker (FR, niche tech terms) | Your corpus is well-served by the embedding model already |
| You want a more "search-engine-like" feel | You want the most "AI-semantic" feel |

The flag is **fully reversible** — flip back to `false` and you're on cosine
alone. Plan to default it to `true` after more queries confirm no regression.

## Raw search vs `curate()`

Two CLI commands cover different needs:

```bash
# Raw semantic search — returns a flat list of top-K notes OR chunks
egovault search "votre requête" --mode notes  --limit 10
egovault search "votre requête" --mode chunks --limit 10

# Librarian retrieval — returns a curated synthesis + sources
egovault curate "votre requête"
```

- Use `search` when you want a quick verbatim lookup (proper nouns, exact
  quotes you'll cite). It does NOT escalate, does NOT respect the curate flags.
- Use `curate` when you want "the best knowledge I have on X" — it respects
  every flag above.

## MCP usage

Via MCP, the same logic exposes two tools:

- `search(query, mode, filters, limit)` — direct search
- `curate(query, filters, limit)` — the recommended entry point for LLM clients

The vault-usage rule (`.claude/rules/vault-usage.md`) tells MCP clients to
prefer `curate` first, `search` only when verbatim quoting is needed.

## Filters

Both functions accept a `SearchFilters` object:

```python
SearchFilters(
    source_type=None,    # e.g. "youtube" — only search sources of this type
    note_type=None,      # e.g. "synthese" — only this note category
    tags=None,           # e.g. ["bitcoin"] — must include any of these tags
    date_from=None,      # ISO date — sources/notes created on/after
    date_to=None,        # ISO date — sources/notes created on/before
)
```

> Note: filters are **declared in the API but not yet enforced at the DB
> level** (DB-M4 in the 2026-05-17 audit, post-reinit debt). They are passed
> through but currently ignored. Use sparingly until DB-M4 is fixed.

## Performance

- `search_notes` / `search_chunks`: a few ms on corpora of thousands of items
  (sqlite-vec ANN). Sub-millisecond on test corpora.
- `search_*_hybrid`: roughly 2× that (an extra FTS5 query + the in-memory
  fusion). Still well under 50 ms in practice.
- The bottleneck is always the embedding step (`ctx.embed(query)`), which is
  one Ollama HTTP call (~50–100 ms locally).

## What's next

- [07 — Notes](07-notes.md): the layer that makes tier 2 work
- [04 — Providers](04-providers.md): which LLM does tier-1 (when it ships)
- [11 — Maintenance](11-maintenance.md): re-embed after model changes
