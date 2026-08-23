---
mode: deep
date: 2026-08-18
slug: turbovec
url: https://github.com/ryancodrai/turbovec
paper: https://arxiv.org/abs/2504.19874
angle: Rust TurboQuant vector index & SIMD quantization vs sqlite-vec for large corpus scaling
status: active
---

# Deep — RyanCodrai/turbovec (TurboQuant Vector Index)

## 1. Fingerprint

- **Primary lang:** Rust (core index + SIMD kernels) + Python bindings (PyO3)
- **Repo type:** Fast in-memory / persistent quantized vector index
- **Paper:** Google Research — *TurboQuant* ([arXiv:2504.19874](https://arxiv.org/abs/2504.19874))
- **License:** Open Source (PyPI: `turbovec`, Crates.io: `turbovec`)
- **Pitch:** "A 10 million document corpus takes 31 GB of RAM as float32. turbovec fits it in 4 GB — and searches it faster than FAISS."

## 2. Key Architecture & Features

```
TurboQuantIndex (raw index) / IdMapIndex (uint64 external IDs)
  ├── 2-bit & 4-bit Data-Oblivious Quantization (no training / k-means step)
  ├── SIMD Kernels (x86 AVX-512 VNNI / AVX2, ARM NEON SDOT/SMMLA)
  ├── Filtered Search via allowlist / bitmask (Stage-2 dense reranking)
  └── Crash-safe incremental sync (sync() / write() / load())
```

### 2.1 Online Ingest without Training
- Unlike Product Quantization (FAISS `IndexPQ`), TurboQuant uses a **data-oblivious quantizer** based on calibrated spherical random projections.
- Vectors can be added incrementally (`add`, `add_with_ids`) without an initial codebook training phase or index rebuilds as the vault grows.

### 2.2 Memory Footprint & High Recall
- Reduces vector memory by **4× (4-bit)** or **8× (2-bit)** with near-zero recall degradation ($R@1 \ge 0.99$ by $k \le 4$ for OpenAI $d=1536$ / $d=3072$).
- Hand-crafted SIMD kernels outperform FAISS `IndexPQFastScan` by up to $3.4\times$ on AVX-512 / NEON.

### 2.3 Native Allowlist Filtering (Ideal for Hybrid Retrieval)
- `search(query, k=10, allowlist=allowed_ids)` evaluates filtering directly inside SIMD blocks (32-vector chunks).
- Blocks with no candidate matches are skipped with zero lookup cost.
- Matches perfectly with EgoVault's 2-stage retrieval: SQLite/FTS5 (BM25) filters candidates $\to$ Turbovec scores candidates.

---

## 3. Comparison with EgoVault's Current Vector Engine

| Aspect | EgoVault Current (`sqlite-vec`) | Future Candidate (`turbovec`) |
| :--- | :--- | :--- |
| **Storage Architecture** | **Single-file embedded SQLite database** (vectors & metadata co-located, 100% ACID). | **Memory-mapped / file index (`.tvim`)** alongside relational metadata in SQLite. |
| **Precision** | Exact float32 cosine distance (zero quantization loss). | Quantized (2-bit or 4-bit TQ+ calibration), high recall at $k \ge 4$. |
| **RAM at Scale** | Scales linearly with float32 vectors; paging handled by SQLite. | $\sim 4$ GB RAM for $10\text{M}$ vectors in 4-bit (huge memory savings for large vaults). |
| **Sweet Spot** | Personal knowledge vaults ($< 200\text{k}$ chunks/notes, $< 5\text{ms}$ latency). | Huge text archives, massive web scrapes, multi-million chunk vaults, low-RAM edge devices. |

---

## 4. Integration Strategy for EgoVault (When Needed)

1. **Hexagonal Seam (`infrastructure/db.py` / `VaultContext`)**:
   EgoVault's Rule G4 isolates database access. A future pluggable backend (`VectorStore` adapter) could route vector writes/searches to `turbovec` while keeping all note/source metadata and FTS5 text tables in SQLite.
2. **Two-Stage Hybrid Search**:
   - Stage 1: SQLite FTS5 retrieves candidate `rowid`s matching text/tags.
   - Stage 2: `IdMapIndex.search(query, k=K, allowlist=candidate_rowids)` performs ultra-fast SIMD reranking.
3. **Configuration Trigger**:
   Configurable in `config/system.yaml` via `vector_engine: sqlite_vec` (default) vs `vector_engine: turbovec` (large corpus mode).
