# Étape 6 — Real-condition ingestion test results (2026-05-17)

**Setup:** fresh DB (post-reinit, corrected schema DB-C1/C2), 25 `source.md`
text sources from `_corpus-test-20260517` (raw-sources corpus), ingested via
`workflows.ingest("texte", ...)`, no note generation (F5 deferred). Ollama
`nomic-embed-text` embeddings (cosine, normalized).

## Ingestion

- 25 ok / 0 fail / 2 skipped (dirs without `source.md`). All `rag_ready`.
- 25 chunks for 25 sources (texts ~0.5 KB → 1 chunk each). ~59 s total.
- Titles populated (driver passed dir name). No errors, no encoding issues
  in stored bytes.

## curate() relevance (4 thematic FR queries, limit 3)

| Query | Top-1 | distance | Verdict |
|-------|-------|----------|---------|
| fourmis sans chef | organisation-decentralisee-des-fourmis | 0.417 | ✅ correct |
| méthode scientifique + décentralisation | methode-scientifique | 0.318 | ✅ clear separation |
| fragilité systèmes centralisés | algorithmes-consensus | 0.499 | ⚠️ MISS — `fragilite-des-systemes-centralises` not in top-3 |
| desire path | 4-livres… | 0.415 | ⚠️ exact source `…desir-paths` ranked #2 (0.417, tied) |

## Findings

### D — `.md` not an accepted text extension (UX, MAJOR-ish)
`cli/commands/ingest.py::_detect_type` maps only `.txt`→texte (and
.html/.htm, .pdf, audio). `.md` raises "Unsupported input". The entire corpus
is `.md`; a user with markdown notes cannot `egovault ingest x.md`. Had to
bypass via the workflow API. Fix: add `.md` (and likely `.markdown`) to the
texte branch.

### E — Cosine ranking is directional but imprecise on real FR data (search quality)
This is the TEST-C2 blind spot made visible. Relevant docs appear in top-3 but
the *exact-topic* source is sometimes #2 or absent from top-3; distances are
clustered 0.32–0.50 with weak separation. Likely causes: (a) `nomic-embed-text`
mediocre on French, (b) whole-short-doc = 1 chunk loses granularity, (c) no
reranking. NOT a correctness bug (metric is sound, F2 confirmed) — a quality
ceiling. Feeds the deferred reranking spec
(`.meta/specs/future/2026-03-28-reranking-design.md`) and an embedding-model
review.

### Calibration — escalation_max_distance
Relevant results land at distance 0.32–0.50. The default
`escalation_max_distance=0.5` sits exactly on the noise floor (Q2's loosely
relevant hits ≈ 0.50). With this corpus + model, 0.5 is too permissive to be a
strong "notes are sufficient" gate; once notes (tier 2) exist, expect frequent
escalation. Revisit after an embedding-model decision; do not hard-tune on one
corpus.

## Verdict

Pipeline ingest → chunk → embed(cosine, normalized) → search → curate works
end-to-end on real French data with zero errors. Semantic precision is the
real limitation (finding E), exactly as the test-suite audit predicted
(TEST-C2). Next quality work: embedding model + reranking + chunking
granularity — a dedicated search-quality track, not a quick patch.
