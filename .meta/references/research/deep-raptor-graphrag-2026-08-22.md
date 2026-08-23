---
mode: deep
date: 2026-08-22
slug: raptor-graphrag
sources: [raptor-arxiv-2401.18059, microsoft-graphrag-arxiv-2404.16130, lazygraphrag-msr-blog, raptor-benchmarks-secondary]
angle: prior art for Tier-2 chunk→concept clustering/synthesis; decide architecture + benchmark order before building EgoVault's own clustering/scoring
status: active
---

# Deep — RAPTOR & GraphRAG (prior art for Tier 2 chunk→concept synthesis)

## 1. Why this note exists

The 2026-08-22 brainstorm with ChatGPT independently re-derived two published
systems: **RAPTOR** (tree of recursive summaries) and **Microsoft GraphRAG**
(entity graph + community summaries). Rather than design EgoVault's own
clustering + importance-scoring algorithm from scratch, this note extracts
what these two systems actually validated empirically, so the Tier-2 refinement
(chunks → synthetic concept notes) reuses proven mechanics and known failure
modes instead of re-litigating them.

Confidence note: exact benchmark numbers below come from secondary sources
(the arXiv PDF didn't extract cleanly); two secondary sources disagreed on the
QuALITY gain (+2pts vs +20pts absolute), flagged below. Treat the *mechanism*
claims as solid (multiple sources agree), the *magnitude* claims as
directional only.

---

## 2. RAPTOR — mechanism

```
chunks (~100 tokens, SBERT embeddings)
   │
   ▼
UMAP (dimensionality reduction)
   │
   ▼
GMM soft clustering (BIC picks cluster count — a chunk CAN belong to >1 cluster)
   │
   ▼
LLM summarizes each cluster → new "node" text, re-embedded
   │
   ▼
recurse: cluster the summary-nodes themselves, summarize again
   │
   ▼
stop when clustering is no longer feasible (few nodes left)
   → result: a TREE, leaves = raw chunks, higher layers = coarser summaries
```

**Retrieval — two strategies tested, one clear winner:**
- *Tree traversal*: walk layer by layer, top-k per layer, descend into children of selected nodes.
- *Collapsed tree*: flatten **every node at every layer into one pool** (leaf chunks AND all summary levels together), rank all of them by cosine similarity to the query, take nodes until a token budget is filled.

Collapsed tree wins — lower latency, better accuracy, because it lets a
single query pull whatever granularity actually matches it (a very specific
question surfaces a leaf chunk; a broad question surfaces a level-3 summary),
instead of forcing one fixed level.

**Direct answer to the user's original question ("chunks brouillent-ils les
pistes?"):** RAPTOR's answer is *no* — it does not exclude chunks from the
index. It indexes chunks and summaries **together** in one space and lets
retrieval pick the right granularity per query. This is the opposite of
what the ChatGPT conversation assumed ("je n'indexerais pas les chunks par
défaut"). Worth treating as a hypothesis to test, not a settled design
choice — see §5.

**Reported gains vs plain chunk retrieval** (secondary-source numbers, treat
as directional): NarrativeQA ROUGE-L +1.6pt, QASPER F1 +2.7pt. QuALITY
accuracy: one source says ~+2pt over a strong DPR baseline, another cites a
~20pt absolute jump — likely against a much weaker no-retrieval baseline.
**Take-away: gains over a *strong* chunk baseline are modest (low single
digits), not transformative.** This directly informs how much benchmark
rigor is needed before committing (§6, hypothesis 1).

No ablation was found isolating "summary-only" vs "summary+chunk" retrieval —
that comparison doesn't seem to exist in the paper, which is itself useful:
it means EgoVault would be the one generating that data point (§6).

---

## 3. GraphRAG — mechanism

```
raw text
   │
   ▼
LLM extracts entities + relationships + claims (expensive: 1 LLM call region per chunk)
   │
   ▼
knowledge graph (nodes=entities, edges=relationships)
   │
   ▼
Leiden algorithm — hierarchical community detection
   (level 0: fine communities on raw graph → level 1: communities-of-communities → ...)
   │
   ▼
LLM writes a community summary per community, bottom-up
   (higher-level summaries are built FROM lower-level summaries, not raw text again)
```

**Two query modes:**
- *Local search*: pull the entity neighborhood around query-matched entities + their edges/claims, single generation pass. Cost ≈ standard vector RAG.
- *Global search*: map-reduce over community summaries (ask every community summary "does this help answer X", then reduce). Handles corpus-wide questions ("what are the main themes across all my books?") that pure chunk RAG cannot answer at all — but expensive, because it fans out over many community summaries per query.

**Cost is the headline problem.** Original full-pipeline indexing: **$20–40
per 1M tokens** (gpt-4o), because every entity/relationship/community needs
its own LLM summarization pass — this is *per-document* LLM cost, not
one-time-per-corpus, and it scales with the number of entities extracted,
not the number of concepts you actually want.

**LazyGraphRAG (Microsoft's own answer to the cost problem) is the most
relevant finding for EgoVault:** it defers ALL LLM summarization to query
time. At ingestion it uses cheap NLP (noun-phrase extraction) + graph
statistics only — **zero LLM calls at ingestion**, indexing cost ≈ plain
vector embedding cost (0.1% of full GraphRAG). At query time it does
lightweight LLM work only over the communities relevant to that specific
query. Result: quality comparable to or better than full GraphRAG global
search, at up to 700× lower query cost.

**This maps almost exactly onto the "3 synthetic queries + agent selection"
idea from the ChatGPT conversation** — both defer the expensive LLM
reasoning to query time and keep ingestion cheap/deterministic. It's strong
independent validation of that half of the brainstorm, and a concrete
prior-art reference instead of an untested idea.

---

## 4. Synthesis — what actually transfers to EgoVault Tier 2

EgoVault already has the tiers (chunks / notes / curate); the open design
question is specifically **how chunks get clustered into a note, and what
gets embedded.** Recommendations, ranked by how much prior-art support they have:

1. **Index chunks and concept-notes in the same vector space, not
   concepts-only.** (RAPTOR's strongest, most surprising finding — contradicts
   the ChatGPT assumption. Test before committing either way, see §6 H1.)
2. **Keep ingestion LLM-light, defer expensive reasoning to query time.**
   (LazyGraphRAG's core insight, and independently already GraphRAG's own fix
   for its own cost problem.) Maps onto EgoVault's existing `curate()` tier-1
   librarian design — reinforces that architecture rather than requiring a
   new one.
3. **Cluster chunks by embedding similarity (UMAP+GMM or simpler), not by
   LLM entity extraction.** GraphRAG's LLM-driven entity/relationship
   extraction is what makes it expensive; RAPTOR's embedding-based clustering
   is what makes it cheap. For a personal vault (not a corpus-QA benchmark),
   RAPTOR's approach is the closer fit.
4. **One summarization LLM call per cluster, not per chunk.** Both systems
   agree: the LLM cost is bounded by *cluster count*, not corpus size. A
   50-chunk book → maybe 10-30 clusters → 10-30 LLM calls, not 300+.
5. **Don't hand-tune a multi-factor importance formula up front.** Neither
   RAPTOR nor GraphRAG scores cluster "importance" with a weighted formula —
   RAPTOR keeps ALL clusters (every node stays retrievable, so a "minor"
   cluster is never discarded, just ranked lower at query time by
   similarity). This argues against the ChatGPT conversation's
   `importance = α·coverage + β·centrality + ...` idea: don't build a scoring
   formula to decide what to keep — keep everything, let retrieval-time
   similarity do the ranking. Simpler, no magic weights, matches Rule G3
   (zero-hardcode).

---

## 5. Features / parameters worth testing (not committing to yet)

Ordered from cheapest-to-test to most involved:

| # | Parameter / feature | What RAPTOR/GraphRAG suggest | EgoVault-specific variant to try |
|---|---|---|---|
| 1 | Retrieval pool | RAPTOR: chunks + summaries together, ranked by cosine, no fixed level | Add notes_vec results into the same ranked pool as chunks_vec, single top-k |
| 2 | Clustering method | RAPTOR: UMAP+GMM (soft, BIC-picked k) | Start simpler: agglomerative clustering on cosine distance with a fixed distance threshold — cheaper to implement, no UMAP dependency to add (Rule: reuse before adding deps) |
| 3 | Cluster→note LLM call | 1 call per cluster | Reuse existing `generate_note_from_source` prompt, just change its input from "1 source" to "1 cluster of chunks" |
| 4 | Recursion depth | RAPTOR recurses until clustering infeasible (multi-level tree) | Cap at 1 level (chunks→notes) for the MVP benchmark; multi-level tree is a v2 question, not a blocker |
| 5 | Query-time reformulation | LazyGraphRAG: cheap LLM work at query time, not ingestion | Matches ChatGPT's "3 synthetic queries" idea — test as a `curate()` enhancement, independent of the clustering question |
| 6 | Importance scoring | Neither system pre-filters by importance | Skip the multi-signal formula entirely for MVP; if pruning is needed later, use cluster size alone as the single signal |

---

## 6. Ordered hypotheses to validate/invalidate

Each hypothesis gates the next — stop and reconsider direction if one fails,
don't build downstream features on an unvalidated assumption.

**H1 — Does a concept-note retrieve better than its source chunks for a short query, on a strong chunk-RAG baseline?**
Protocol: pick 1-2 already-ingested books, hand-write ~20-30 questions with
known correct passages. Compare recall@5 of (a) chunk-only index vs (b)
concept-note-only index vs (c) both combined (RAPTOR's collapsed-tree
approach). *If (c) doesn't clearly beat (a), the whole synthesis-note
direction has no retrieval justification — stop here, the product angle
(§7 below) would have to carry the project alone.*
RAPTOR's own numbers (§2) suggest the gain over a strong chunk baseline is
real but modest — set expectations accordingly, don't require a huge delta
to call H1 validated.

**H2 — Is clustering-before-summarizing better than the current 1-source→N-notes flow?**
Compare notes generated from embedding-based clusters of chunks (across
possibly non-contiguous passages of the same book) vs the current per-source
note generation. Does clustering surface concepts that span the whole book
better, or does it just add clustering-pipeline complexity for a similar
result on a book that's already reasonably well-structured?

**H3 — Is deferring LLM work to query time (§4.2, LazyGraphRAG-style) better than pre-computing everything at ingestion?**
Compare `curate()` with a single direct query embedding vs `curate()` with
the "3 synthetic queries" reformulation. Measure quality gain vs added
query-time latency/cost. This is testable independently of H1/H2 — can run
in parallel.

**H4 — Does the ingestion LLM cost pay for itself?**
Only worth precise-costing once H1 is validated. Compute $ per book at
current provider pricing for cluster-count-many summarization calls,
compare against how many times a book is realistically re-queried in
practice. If H1 fails, this question is moot.

**H5 — Multi-level tree (RAPTOR-style recursive summarization) vs single-level (chunks→notes only)?**
Only relevant once H1-H2 are validated. Multi-level trees add real
complexity (recursion stopping condition, level selection at query time);
don't build this until single-level clustering has already proven its
worth.

---

## 7. What's out of scope for this note

The "personal memory layer" idea (user reflections linked to concepts,
graph-3D exploration by author/topic) from the ChatGPT conversation is a
**product** differentiator, not a retrieval-architecture question — it's
orthogonal to H1-H5 and doesn't need RAPTOR/GraphRAG prior art. Revisit
after H1 is validated, as previously agreed.

---

## 8. Sources

- [RAPTOR paper, arXiv 2401.18059](https://arxiv.org/abs/2401.18059) — mechanism confirmed via secondary sources, PDF text extraction failed
- [Microsoft GraphRAG paper, arXiv 2404.16130](https://arxiv.org/abs/2404.16130) — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"
- [LazyGraphRAG — Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) — fetched directly, cost/quality numbers confirmed
- [GraphRAG community detection docs](https://www.mintlify.com/microsoft/graphrag/concepts/community-detection) — Leiden hierarchy mechanism
- [RAPTOR review — liner.com](https://liner.com/review/raptor-recursive-abstractive-processing-for-treeorganized-retrieval) — secondary summary, benchmark table
- GraphRAG cost figures ($20-40/1M tokens gpt-4o; early $33k outlier) — aggregated from multiple 2026 secondary blog sources (Spheron, techcommunity.microsoft.com), not independently verified against primary billing data — treat as approximate
