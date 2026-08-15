# EgoVault Interactive Visual Notebooks

This directory contains visual exploration, tuning, and demonstration notebooks for the EgoVault Cognitive Memory Compiler.

**Every notebook here uses the real engine end to end** — real chunking (`tools/text/chunk.py`),
real segmentation (`tools/text/segment.py`), real embeddings (Ollama `nomic-embed-text`,
768 dims, via `infrastructure/embedding_provider.py`), and real retrieval (`tools/vault/curate.py`).
There is no mock/bag-of-words fallback anywhere: if the embedding provider is unreachable, a
notebook fails loud in its first cell with setup instructions rather than silently degrading.

## Prerequisite: Ollama

```bash
ollama pull nomic-embed-text
ollama serve   # if not already running
```

Every notebook's first code cell probes the provider and raises a clear error if it can't
reach it. Embeddings are disk-cached under `notebooks/.cache/` (gitignored, see
`notebooks/_lib/embedding_cache.py`) — the first run of a notebook against a large corpus
(e.g. the 293-chunk Marcus Aurelius PDF) takes a few minutes; every run after that is
near-instant, since only new text triggers a network call.

## Available Notebooks

| Notebook | Topic | Description |
|---|---|---|
| [`01_topic_segmentation_visualizer.ipynb`](01_topic_segmentation_visualizer.ipynb) | Thematic Boundary Segmentation (TextTiling) | Real-embedding cosine similarity curve, valley depth score, and adaptive threshold ($\mu + k\sigma$), on both a clean synthetic sample and a real noisy book excerpt. |
| [`02_semantic_clustering_benchmark.ipynb`](02_semantic_clustering_benchmark.ipynb) | Semantic Clustering Benchmark | Compares 4 segmentation strategies (baseline TextTiling, two-stage hierarchical merge, constrained AHC, Gaussian-smoothed minima) with quantitative cohesion/separation/contrast scoring and explicit uniformity-bias analysis, on both book prose and a real spoken-discourse transcript. |
| [`03_retrieval_curate_benchmark.ipynb`](03_retrieval_curate_benchmark.ipynb) | Retrieval / `curate()` Benchmark | Benchmarks the Librarian tool itself against a real ingested vault: pure cosine vs. hybrid RRF retrieval, escalation-to-chunks behavior, confidence weighting breakdown, and RRF fusion mechanics for one query. |
| [`04_end_to_end_cognitive_explorer.ipynb`](04_end_to_end_cognitive_explorer.ipynb) | End-to-End Walkthrough | Full journey from ingestion to intelligence synthesis — ingest, segment, claim, convert to note, review, curate, drill down to verbatim evidence, and an embedding-space projection showing why `curate()` escalated (or didn't). |

Each `.ipynb` has a `.py` mirror for terminal execution (see Quickstart below) — keep both in sync when editing either.

## Planned

- **Multimodal PDF/OCR inspection** — bounding-box overlays from RapidOCR on PDF pages,
  high-res figure slice inspection. Not built yet; tracked by
  [`.meta/specs/2026-08-15-visual-and-document-ingestion-spec.md`](../.meta/specs/2026-08-15-visual-and-document-ingestion-spec.md).

## Quickstart

### Option A: Jupyter Lab / Jupyter Notebook (.ipynb)
```bash
uv run jupyter lab notebooks/
```
Or open any `.ipynb` directly in VS Code / Cursor.

### Option B: Direct Terminal Execution (.py)
```bash
uv run python notebooks/demo_segmentation_visualizer.py
uv run python notebooks/demo_marcus_aurelius_segmentation.py
uv run python notebooks/demo_podcast_segmentation_benchmark.py
uv run python notebooks/demo_retrieval_curate_benchmark.py
uv run python notebooks/demo_end_to_end_explorer.py
```
