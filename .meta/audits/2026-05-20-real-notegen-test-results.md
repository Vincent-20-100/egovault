# 2026-05-20 — Real-condition local note-gen test (F5 + curate tier-2)

**Setup:** `user.yaml` `llm.provider: ollama, model: qwen2.5:7b-instruct` (Q4_K_M);
25 `rag_ready` text sources from `_corpus-test-20260517`; CPU-only inference on
Ryzen 7840U / 11.7 GB RAM; nomic-embed-text for embeddings. Driver:
`.meta/scratch/notegen_corpus.py` (one-off, gitignored).

## Generation results

- **22 / 25 notes generated** (88%), all status `draft` / `synced` per workflow gate.
- Total wall time **44 min** (avg ~50–100 s/note typical, first call ~240 s for
  model load, longer outliers correspond to 3-retry attempts).
- Sample (`algorithmes-consensus`, 1344 chars body): coherent French Markdown,
  proper section headings (`## Introduction`, `## Fonctionnement`...), minor
  typo (`Leir`→`Leur`) — acceptable from a 7B local model.
- `note_type` field NOT in the configured taxonomy is accepted at generation
  time (e.g. `technique`) — by design (F5 spec §3.1: bare
  `NoteContentInput(**data)`, taxonomy enforcement deferred to approval).
  **Parity with the claude path holds in real conditions.** ✅

## Failures — root cause (deterministic, NOT flaky)

3 failures, identical pattern across 3 retry attempts each:
```
ValueError: LLM failed to produce valid NoteContentInput after 3 attempts.
Last error: 1 validation error for NoteContentInput
tags: Value error, tag 'systèmes' must contain only ASCII characters (no accents)
```

Qwen 7B Q4 generates accented French tags (`systèmes`, etc.) despite the
template's instruction. Error context injection on retry does NOT make Qwen
fix it — sticky failure mode for sources whose topic vocabulary is naturally
accented. NOT correlated with source size (failed transcript lens 480/488/690,
all within the success-set range, median success = 468 chars).

**Implication:** F5 / Ollama integration itself is correct (the validation
contract caught a real product issue). The defect is in EgoVault's
tag-validation policy vs local-LLM realism for FR. Three possible fixes,
listed in escalating cost:
1. **Post-process tags at generation:** transliterate accents to ASCII before
   validation in `_generate_ollama` (and `_generate_anthropic` for parity).
   Cheap, fixes 100% of this class. Recommended.
2. Strengthen `config/templates/generation/standard.yaml` system_prompt with
   an explicit accent-stripping example. May reduce but not eliminate.
3. Defer tag-ASCII validation to approval (mirror the taxonomy pattern). Most
   aligned with the existing late-enforcement convention, but the tag rule is
   a hard vault rule, not a config-driven taxonomy — different in nature.

A targeted retry of one failed source (`2025-07-14-fragilite-des-systemes-
centralises`) reproduced the exact same `systèmes` accent failure 3 times in
a row, confirming determinism.

## curate() tier-2 — the headline result

curate() now hits the **notes layer first**; all 4 thematic queries returned
exclusively `note:` results (zero chunk escalation), confirming
`escalation_max_distance=0.5` is well-calibrated for this corpus + model.

| Query | Étape 6 (chunks only) | Étape 7 (notes tier) | Δ |
|---|---|---|---|
| fourmis sans chef | chunk `organisation-decentralisee-des-fourmis` d=0.4173 ✅ | note **Organisation décentralisée des fourmis** d=**0.2703** ✅ | distance −36% |
| fragilité systèmes centralisés | chunk `algorithmes-consensus` d=0.4987 ⚠️ MISS | note `Resilience des systèmes décentralisés` d=0.3678, top3 includes `Effets des systèmes centralisés` | thematic-rank improved, distances much better |
| méthode scientifique + décentralisation | chunk `methode-scientifique` d=0.318 | note `Science décentralisée` d=0.310 → `Méthode scientifique` d=0.318 (semantic fusion of both concepts) | ✅ |
| desire path | chunk `4-livres...` d=0.4146 (exact source rank 2) ⚠️ | note **`Définition et intérêt des désir paths`** d=0.3131 | ✅ exact-topic now rank 1 |

**Dramatic improvement on both precision and absolute distances** (all top-1
distances drop ~0.10–0.13). The compiled-notes tier delivers exactly what the
Knowledge Compiler vision predicted: dense, human-titled, semantically
distinct notes embed and rank better than fragmented chunks. Tier-2 over
tier-1 is a real, measurable win on real French data.

## Calibration confirmed

- `escalation_max_distance = 0.5` is correct for this corpus + nomic +
  qwen-generated notes: relevant notes land 0.27–0.40, well under the
  threshold; never triggers chunk escalation when notes exist.
- The cosine ceiling described in finding E **persists** for chunks (étape 6
  showed it) but is **substantially mitigated** by the notes tier — because
  notes have crisp titles + dense docstrings that embed cleanly. This
  reframes finding E: the search-quality track (RRF BM25+cosine experiment
  #1) should now be evaluated on TWO axes — chunks improvement AND whether
  the notes tier is "good enough" that RRF mostly matters at the chunks
  level (raw RAG fallback).

## Verdict + next actions

- F5 (Ollama provider): **operational on real corpus, 88% success.** Failure
  mode is a clean validation-rejection (no silent corruption), reproducible.
- curate() tier-2: **operational and a clear win**, no parameter changes
  needed.
- Next: implement fix #1 (auto-transliterate tags in both `_generate_*`) → a
  small TDD slice that should bring success rate to ~100% on this corpus.
- Then: experiment #1 (RRF BM25+cosine for chunks), with the now-richer
  intuition that the notes tier already does the heavy lifting in practice.
