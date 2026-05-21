# 2026-05-21 — RRF(BM25, cosine) experiment #1 — empirical results

**Goal:** validate the SOTA-synthesis claim (deep #1+#2+#3, 2026-05-19) that
hybrid retrieval mitigates finding E (FR cosine imprecision) on EgoVault's real
corpus. Built FTS5 + RRF fusion in this commit chain (6db5c0f..43e7af5).

**Stack:** SQLite FTS5 (`tokenize='unicode61 remove_diacritics 2'`) +
sqlite-vec cosine + `_rrf_fuse(k=60)`. Zero new Python dep. New functions:
`search_chunks_hybrid` / `search_notes_hybrid` in `infrastructure/db.py`.

**Corpus:** the 25 notes (qwen2.5:7b generated) + 25 chunks from
`_corpus-test-20260517` (étapes 6–7).

## Side-by-side results on the 4 thematic queries

| Q | Layer | Cosine top-3 | Hybrid (RRF) top-3 | Verdict |
|---|---|---|---|---|
| Q1 fourmis sans chef | notes | Organisation décentralisée des fourmis (0.27), Intelligence collective (0.38), Modèle évolution (0.40) | **identical** | neutral — cosine already perfect |
| Q1 | chunks | identical to cosine | identical | neutral |
| Q2 fragilité systèmes centralisés | notes | Resilience (0.37), Failles royaute (0.39), Effets (0.39) — **misses exact-topic** | Resilience (0.37), **Fragilité des systèmes centralisés (d=2.0 BM25-only, rank 2)**, Failles royaute | ✅✅ **WIN** — exact-topic promoted from outside-top-3 to rank 2 |
| Q2 | chunks | Effets (0.34), Fragilité (0.35), Resilience (0.37) — exact-topic rank 2 | **Fragilité (rank 1)**, Effets (rank 2), Resilience | ✅ exact-topic promoted to rank 1 |
| Q3 méthode + décentralisation | notes | Science décentralisée (0.31), Méthode scientifique (0.32), Modèle (0.38) | **Méthode scientifique (rank 1)**, Science décentralisée (rank 2), Modèle | reorder — BM25 boost on lexical-exact match (defensible either way) |
| Q3 | chunks | identical | identical | neutral |
| Q4 desire path | notes | Définition et intérêt des désir paths (0.31), Justice (0.38), Démocratie (0.39) | **identical** | neutral — cosine already perfect |
| Q4 | chunks | 4-livres (0.41), Définition désir paths (0.42), Justice (0.46) — exact-topic rank 2 | **identical** | neutral — vocabulary mismatch ("desire" EN vs "désir" FR) — BM25 can't bridge stems |

## Headline finding

- **1 big win, 1 smaller win, 1 defensible reorder, 5 neutral, 0 regression.**
- The Q2 result is the canonical finding-E case — the exact-topic source's
  vocabulary didn't embed well in `nomic-embed-text`; cosine missed it. BM25
  found it instantly via the keyword "fragilite"; RRF surfaced it into top-3.
  This is exactly what deep-card synthesis predicted.
- BM25-only sentinel (`distance = 2.0`) works as designed: the result appears
  in the fused list **without** corrupting cosine-thresholded reasoning
  (`curate.escalation_max_distance = 0.5` would still classify it as
  not-cosine-relevant — RRF just adds it to recall).

## Where hybrid does NOT help

- **Vocabulary stems mismatch** (Q4 chunks): EN "desire" vs FR "désir" — BM25
  needs a shared lexical surface; `remove_diacritics` normalizes accents but
  not language stems. Cross-language retrieval is a different track
  (multilingual embeddings).
- **Cosine already top1** (Q1, Q4 notes, Q3 chunks): hybrid changes nothing,
  no harm done.

## Reframe (revisits the 2026-05-19 synthesis)

- The notes tier ALREADY absorbed most of finding E (étape 7) — RRF is now
  the smaller, finishing-touch layer **on top** of that.
- The Q2 result confirms RRF's specific value: **lexical recall for
  exact-topic sources whose vocabulary doesn't embed well**. Not a universal
  cosine replacement; a targeted complement.
- The synthesis card's claim "structural navigation / hybrid is THE SOTA
  direction" is partially validated: hybrid is one half (lexical+semantic).
  Structural (claude-obsidian's hot.md/index.md precedence) was NOT part of
  this experiment and remains a separate, larger redesign.

## Adoption decision (deferred to next slice)

- Status quo: `search_*_hybrid` exist; `curate()` still uses pure cosine.
- Next slice (small): add a config flag `curate.use_hybrid_retrieval` (default
  `false` for safe rollout), wire it in `tools/vault/curate.py` to swap
  `ctx.db.search_*` for hybrid variants. A/B-able, reversible.
- Default-on later, once we have more queries to validate no regression.

## Cost

- 0 new Python dep (FTS5 in stdlib SQLite)
- ~80 lines of production code + 13 new tests
- FTS5 storage overhead: ~1× the indexed text (chunks content + notes title +
  docstring). Negligible at current corpus sizes; documented in `DATABASES.md`.
- Backfill is idempotent in `init_db`; existing populated DBs get FTS for free
  on next startup.
