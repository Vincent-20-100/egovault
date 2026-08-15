# Plan — Notebooks Real-Engine Overhaul

**Date:** 2026-08-15
**Confidence:** GREEN — both open decisions resolved by Vincent 2026-08-16 (fail-loud only, new notebook takes the `03` slot). Ready to implement.

## Why

Current notebooks (`01`, `02`, `04`) all embed text with a hash-based bag-of-words
mock (`hash(word) % 768`), not the real pipeline (`infrastructure/embedding_provider.py:embed`,
Ollama `nomic-embed-text`, 768 dims). That means every segmentation/retrieval
conclusion drawn from them (e.g. notebook 02's "Method 1 RECOMMENDED") is based on
lexical overlap, not semantic similarity — it may not hold with real embeddings.
`04`'s pipeline bar chart also reports a fabricated number
(`len(chunk_uids) * len(cands)` instead of the real chunk count). `01`'s `.ipynb`
JSON is corrupted and won't open.

Goal: every notebook calls real engine functions end-to-end (chunk → embed → segment
→ ingest → curate), in English, with enough visualization to make each internal
step legible, and with genuine benchmarking (metrics, not eyeballed bar widths).

## Decisions needed from Vincent before implementation

1. **Fail-loud on missing Ollama, confirmed.** `embed()` already raises
   `RuntimeError` (via `sanitize_error`) if Ollama is unreachable. Notebooks will
   NOT catch this and silently fall back to the mock embedder — they'll run a
   connectivity probe in cell 1 with a clear markdown instruction
   ("start Ollama, `ollama pull nomic-embed-text`") and otherwise let the real
   error surface. Confirm this matches what you want (vs. e.g. a `--mock` opt-in
   flag for CI/offline use).
2. **Numbering conflict.** `notebooks/README.md` promises a `03_multimodal_pdf_and_ocr_inspection.ipynb`
   that doesn't exist yet (separate spec/plan already tracks that feature). This
   plan proposes inserting the new retrieval/curate benchmark as `03_retrieval_curate_benchmark.ipynb`
   and pushing the not-yet-built multimodal notebook to a "Planned" section of the
   README instead of the numbered table. Confirm, or say if `03` must stay reserved
   (in which case the new notebook becomes `05`).

## Files involved

- `notebooks/_lib/embedding_cache.py` — **create**. Shared disk-cache wrapper around
  `infrastructure.embedding_provider.embed()` so re-running a notebook over 293
  chunks doesn't re-hit Ollama every time. Cache key = sha256(text) + model name +
  dims (read from `settings.system.embedding`, no hardcoded literals). Cache file
  under `notebooks/.cache/` (gitignored).
- `.gitignore` — **modify**. Add `notebooks/.cache/`.
- `notebooks/01_topic_segmentation_visualizer.ipynb` — **regenerate** (JSON is
  corrupted; rebuild from the fixed `.py` mirror rather than hand-patching broken JSON).
- `notebooks/demo_segmentation_visualizer.py` — **modify**. Real embeddings via
  cache helper; add adaptive-threshold and valley-depth visualizations.
- `notebooks/02_semantic_clustering_benchmark.ipynb` — **modify in place**. Swap
  mock embed for real (cached) embed; add quantitative metrics.
- `notebooks/demo_marcus_aurelius_segmentation.py` — **modify** to match.
- `notebooks/03_retrieval_curate_benchmark.ipynb` — **create** (new). Benchmarks
  `curate()` strategies (hybrid RRF vs pure cosine, confidence weighting,
  escalation behavior) against the real ingested Marcus Aurelius vault.
- `notebooks/demo_retrieval_curate_benchmark.py` — **create**. `.py` mirror, per
  existing convention (every `.ipynb` has a terminal-runnable twin).
- `notebooks/04_end_to_end_cognitive_explorer.ipynb` — **modify in place**. Real
  embeddings; fix the fabricated chunk-count bar; add embedding-space projection
  showing why `curate()` escalates or not.
- `notebooks/demo_end_to_end_explorer.py` — **modify** to match.
- `notebooks/README.md` — **modify**. Reconcile the table with what's actually on
  disk (filenames, real `02`/new `03` descriptions), move multimodal notebook to
  a "Planned" section, add a note about the Ollama prerequisite and the embedding cache.

No changes to `infrastructure/`, `tools/`, or `workflows/` — this is a notebooks-only
overhaul; the engine functions being demonstrated are already correct.

## Tasks

### 1. Embedding cache helper
- **Files:** `notebooks/_lib/embedding_cache.py`, `.gitignore`
- **Do:** `get_or_embed(texts: list[str], ctx) -> list[list[float]]`. For each text,
  compute `sha256(text)`, look up `{sha256}_{model}_{dims}.json` under
  `notebooks/.cache/`; on miss, call `ctx.embed(text)` (real provider), persist,
  return. First call in any notebook does a cheap connectivity probe (one
  `ctx.embed("ping")` call) and re-raises with a friendlier markdown-visible
  message pointing at `ollama pull nomic-embed-text` if it fails — no mock fallback.
- **Verify:** `uv run python -c "from notebooks._lib.embedding_cache import get_or_embed; ..."`
  against a running Ollama returns 768-dim vectors; second call is a cache hit
  (no network call — verify via a monkeypatched counter in a quick manual test).

### 2. Fix `01` — real embeddings + deeper visualization
- **Files:** `notebooks/demo_segmentation_visualizer.py`, `notebooks/01_topic_segmentation_visualizer.ipynb`
- **Do:** Replace `mock_embed` with `get_or_embed`. Keep the existing 3-topic
  synthetic sample (Quantum/Neuroscience/Game Theory — good for a clean boundary
  demo) but ALSO run the same pipeline against a slice of the real Marcus Aurelius
  corpus for a "hard" real-world case. Add: (a) raw vs. smoothed cosine curve with
  the `sensitivity_k`-derived threshold band drawn on top (currently text-only),
  (b) valley depth score bar chart per candidate boundary, (c) color-coded segment
  bands over the chunk sequence (currently ASCII bar only).
- **Verify:** Run the `.py` script end-to-end against live Ollama; regenerate the
  `.ipynb` from it (nbformat) and confirm it opens without JSON errors in VS Code.

### 3. Fix `02` — real embeddings + quantitative benchmarking
- **Files:** `notebooks/demo_marcus_aurelius_segmentation.py`, `notebooks/02_semantic_clustering_benchmark.ipynb`
- **Do:** Replace mock embed with `get_or_embed` (293 chunks, cached after first
  run). Add a metrics table per method: mean intra-candidate cosine (cohesion),
  mean cross-boundary cosine (separation), separation-minus-cohesion score,
  candidate-count/size distribution (min/max/std), wall-clock runtime. Render as a
  bar/heatmap comparison, not just eyeballed band widths. Re-run the existing 4-way
  visual comparison and 3D PCA plot on real embeddings; update the final
  recommendation table with the real numbers (the current "Method 1 RECOMMENDED"
  call is only validated on bag-of-words vectors today).
- **Verify:** Metrics table renders with numeric values; recommendation cell text
  reflects the real-embedding run, not the stale bag-of-words conclusion.

### 4. New `03` — retrieval / curate benchmark
- **Files:** `notebooks/03_retrieval_curate_benchmark.ipynb`, `notebooks/demo_retrieval_curate_benchmark.py`
- **Do:** Ingest the real corpus into an isolated tmp vault (same pattern as `04`),
  generate + approve a handful of notes (mix of `reviewed`/`unreviewed` so
  confidence weighting is visible), then run `curate()` under real embeddings for
  a fixed query set on Stoic themes (duty, virtue, death, self-discipline).
  Compare: pure cosine vs. `use_hybrid_retrieval=true` (RRF fusion) — visualize
  the BM25-rank vs cosine-rank vs fused-rank table for one query; show the
  escalation behavior (tier composition — notes only vs. notes+chunks — across
  queries with different note coverage); show confidence score composition
  (reviewed-weight vs unreviewed-weight contribution) for a query hitting both.
- **Verify:** Notebook runs end-to-end against live Ollama; RRF-on and RRF-off
  results are visibly different for at least one query in the fixed set (if not,
  pick a better query — a benchmark that can't show a difference isn't a benchmark).

### 5. Fix `04` — real embeddings + correct pipeline chart
- **Files:** `notebooks/demo_end_to_end_explorer.py`, `notebooks/04_end_to_end_cognitive_explorer.ipynb`
- **Do:** Replace mock embed with `get_or_embed`. Fix the pipeline bar chart to use
  `len(chunks)` (the real 293, from the actual `chunk_text()` call, not
  `len(chunk_uids) * len(cands)`). Add a 2D projection (PCA — no new heavy dep) of
  note + chunk vectors relative to the query vector, to visually explain why
  `curate()` did or didn't escalate to chunks for the demo query.
- **Verify:** Bar chart's "SOTA Chunks" bar equals the printed chunk count from
  step 1's ingest log. Confidence score and similarity plot use real distances.

### 6. README reconciliation
- **Files:** `notebooks/README.md`
- **Do:** Update the table to match the 4 real notebooks (`01`, `02`, `03` new,
  `04`), correct the `02` description (semantic clustering benchmark, not "dual
  vector space topology" — that description belongs to a notebook that doesn't
  exist), add the Ollama prerequisite + `notebooks/.cache/` note, move the
  multimodal PDF/OCR notebook to a "Planned" section referencing its spec.
- **Verify:** Every filename in the table exists on disk; every notebook on disk
  (except `_lib/` and assets) is referenced in the table or the Planned section.

## Ripple effects (per CLAUDE.md doc-maintenance automatism)

- `notebooks/README.md` updated in the same batch (task 6) — no separate PR.
- No `docs/user-guide/` impact — notebooks are internal dev/demo tooling, not
  user-facing product behavior.
- No `config/system.yaml` changes needed — all thresholds notebooks visualize
  already live there and get read, not hardcoded.

## Scope addition — 2026-08-16 (mid-implementation, Vincent)

Real-embedding results from task 3 exposed a premise problem: the benchmark was
implicitly rewarding uniform-ish segment sizes. Vincent's actual goal is semantic
coherence regardless of size — a single powerful one-chunk idea and a 50-chunk
passage about one central idea are equally valid note candidates. Two changes:

1. **Size-distribution / uniformity-bias analysis added to notebook 02.** Real
   run showed `Two-Stage Hierarchical Merging` enforces a narrow 18-24 chunk
   range (its `min_chunks`/`max_chunks` caps fight the actual goal) while
   Baseline, AHC, and Gaussian all naturally range from 1 to 40-52 chunks. The
   "winner" can no longer be picked by contrast score alone — size-range breadth
   (does the method let a 1-chunk idea and a 46-chunk idea coexist) is now a
   named criterion, not just cohesion/separation.
2. **Second corpus: spoken discourse/podcast format**, to stress-test whether
   segmentation methods calibrated on book prose hold up on transcript speech
   (filler, repetition, no paragraph structure). Source: YouTube video
   `5JDrK7sP3gA` (single video, per Vincent — not the full playlist), ingested via
   the real `tools.media.fetch_subtitles` path, confirmed feasible (9151 chars,
   English captions tagged `fr` — a pre-existing metadata quirk, not a blocker).
   Strategy functions + metrics extracted to `notebooks/_lib/segmentation_strategies.py`
   so both corpora reuse the same benchmarking code (2 real call sites justifies
   the shared module — not previously planned, but avoids ~150 lines of duplication).

Files added to the touched set: `notebooks/_lib/segmentation_strategies.py` (create),
`notebooks/demo_podcast_segmentation_benchmark.py` (create, mirrors task 3's script
for the new corpus). Notebook `02` gains a "Corpus B: spoken discourse" section
and a size-distribution figure; no new numbered notebook.

## Out of scope (explicitly deferred)

- Multimodal PDF/OCR notebook (`03` per stale README) — tracked by its own spec,
  not touched here.
- Batch-embedding Ollama's `/api/embed` (plural) endpoint vs. one-call-per-chunk —
  worth checking during implementation of task 1 for speed, but not a plan-level
  decision; the cache makes repeat runs free regardless.
- Any change to `infrastructure/embedding_provider.py`, `tools/text/segment.py`,
  or `tools/vault/curate.py` — engine code is correct today; only the notebooks
  were lying about what it does.
