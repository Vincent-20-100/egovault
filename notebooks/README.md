# EgoVault Interactive Visual & Benchmark Notebooks

This directory contains R&D benchmark suite and interactive product showcase notebooks for the **EgoVault Cognitive Memory Compiler**.

**Every notebook uses the real engine end to end** — real chunking (`tools/text/chunk.py`), real TextTiling segmentation (`tools/text/segment.py`), real embeddings (Ollama `nomic-embed-text`, 768 dims via `infrastructure/embedding_provider.py`), and real retrieval (`tools/vault/curate.py`).

---

## Suite Structure

```
notebooks/
├── 01_engine_benchmarks.ipynb      # [R&D & Engine Benchmarks]
│                                   # 1. TextTiling Trajectory Inspection (consecutive cosines & valley depths)
│                                   # 2. 4-Strategy Segmentation on Heterogeneous Sources (Book Prose vs Spoken Discourse Podcast)
│                                   # 3. Retrieval curate() Benchmark (Pure Cosine vs Hybrid RRF)
│
├── 02_cognitive_explorer_demo.ipynb # [Product Showcase & End-to-End Walkthrough]
│                                   # Complete 7-step journey from raw PDF ingestion to Markdown note compilation,
│                                   # working memory recall (curate), and verbatim proof drill-down.
│
├── demo_engine_benchmarks.py       # Terminal mirror script for Notebook 01
├── demo_cognitive_explorer_demo.py # Terminal mirror script for Notebook 02
└── assets/                         # Generated high-resolution Matplotlib figures
```

---

## Prerequisite: Ollama

```bash
ollama pull nomic-embed-text
ollama serve   # if not already running
```

Embeddings are disk-cached under `notebooks/.cache/` (see `notebooks/_lib/embedding_cache.py`) — repeated runs are near-instantaneous.

---

## Execution

### Option A: Jupyter Environment
```bash
uv run jupyter lab notebooks/
```
Or open `01_engine_benchmarks.ipynb` or `02_cognitive_explorer_demo.ipynb` directly in VS Code / Cursor / Jupyter.

### Option B: Terminal Execution (.py Mirrors)
```bash
uv run python notebooks/demo_engine_benchmarks.py
uv run python notebooks/demo_cognitive_explorer_demo.py
```

---

## Benchmarked Corpora

1. **Book Prose:** *Marcus Aurelius Meditations* (128 pages, PDF in `notebooks/assets/Marcus-Aurelius-Meditations.pdf`).
2. **Spoken Discourse:** YouTube Podcast Transcript (URL: `https://youtu.be/Pef22g53zsg`, 6,316 words).
