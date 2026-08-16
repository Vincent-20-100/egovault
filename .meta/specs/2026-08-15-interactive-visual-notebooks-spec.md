# Spec: Interactive Visual Notebooks & End-to-End Cognitive Memory Explorer

**Date:** 2026-08-15  
**Status:** Spec-Ready (Validated)  
**Related Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md` (Cognitive Architecture & 3-Tier Memory Engine)  
**Output Directory:** `notebooks/`

---

## 1. Context & Motivation

EgoVault relies on non-trivial mathematical and topological concepts:
1. **Tier 0 (Mechanical Chunks):** Consecutive cosine similarity drop detection (TextTiling) on chunk embedding trajectories.
2. **Tier 1 vs. Tier 2 Topology:** Dual vector spaces (`chunks_vec` vs `notes_vec`) representing raw episodic evidence vs. condensed neocortical conceptual centroids.
3. **Tier 3 Context Assembly:** Spreading activation, Reciprocal Rank Fusion (RRF), and working memory slot allocation (4–7 mental models).
4. **Multimodal Extraction:** Structural PDF layout parsing, bounding box OCR, and high-definition figure slicing.

While unit tests validate functional correctness, **interactive visual notebooks** (.ipynb files) provide:
- Instant hyperparameter calibration (tuning TextTiling sensitivity $k$, similarity floor $S_{\text{min}}$, RRF $k=60$).
- Visual empirical proof of the cognitive compression advantage (1 bloated note vs $N$ cohesive conceptual nuclei).
- An intuitive, interactive visual playground for researchers, developers, and power users with pre-rendered inline plots and cell outputs.

---

## 2. Notebook Suite Architecture

```
notebooks/
├── 01_topic_segmentation_visualizer.ipynb      ← TextTiling mathematical inspection, valley depth d_i, and k calibration
├── 02_semantic_clustering_benchmark.ipynb       ← 4-strategy clustering benchmark on Marcus Aurelius PDF (2D/3D PCA & Dendrogram)
├── 03_multimodal_pdf_and_ocr_inspection.ipynb  ← Layout parsing bounding boxes, sliced figure gallery, and Markdown tables
├── 04_end_to_end_cognitive_explorer.ipynb      ← Complete end-to-end interactive memory engine walkthrough
├── assets/                                     ← Versioned PDF assets (Marcus-Aurelius-Meditations.pdf) & PNG figures
└── README.md                                   ← Guide for executing and inspecting notebooks
```

---

## 3. Cell-by-Cell Specification per Notebook

### 3.1 Notebook 01: Thematic Boundary Visualizer (`01_topic_segmentation_visualizer.ipynb`)

- **Objective:** Mathematical inspection and hyperparameter calibration of the consecutive cosine TextTiling algorithm.
- **Cell-by-Cell Structure:**
  - **Cell 1 (Markdown):** Mathematical foundations of TextTiling:
    $$\text{Cosine Similarity: } s_i = \cos(v_i, v_{i+1})$$
    $$\text{Valley Depth Score: } d_i = \frac{(\max_{\text{left}} - s_i) + (\max_{\text{right}} - s_i)}{2}$$
    $$\text{Adaptive Boundary Seuil: } T = \mu_d + k \cdot \sigma_d$$
  - **Cell 2 (Code):** Environment initialization and imports (`numpy`, `matplotlib`, `pypdf`, `core.config`, `tools.text.segment`).
  - **Cell 3 (Code):** Load multi-topic benchmark source text and compute SOTA chunking ($300$ words, $40$ words overlap).
  - **Cell 4 (Code + Plot):** Plot 1: Consecutive cosine similarity curve $s_i$ across chunk boundaries with mean similarity dashed line $\mu$.
  - **Cell 5 (Code + Plot):** Plot 2: Valley Depth Score bar chart $d_i$ highlighting deep semantic shifts.
  - **Cell 6 (Code + Plot):** Plot 3: 3-Panel Matplotlib subplot comparing sensitivity levels ($k=0.5$ over-segmented, $k=1.2$ balanced, $k=1.8$ macro-topics) with horizontal threshold overlays and vertical boundary markers.
  - **Cell 7 (Code + Plot):** Plot 4: Pastel color-banded horizontal spans overlay displaying the exact chunk span, word count, and extracted heading label of generated `NoteCandidate` objects.
  - **Cell 8 (Markdown):** Sensitivity calibration guidance table for long documents vs short articles.

---

### 3.2 Notebook 02: Semantic Clustering Benchmark & Topology (`02_semantic_clustering_benchmark.ipynb`)

- **Objective:** Empirical R&D benchmark comparing 4 semantic clustering algorithms on the full 128-page *Marcus Aurelius' Meditations* (293 SOTA chunks).
- **Cell-by-Cell Structure:**
  - **Cell 1 (Markdown):** Benchmark motivation: Preventing over-segmentation on large books.
  - **Cell 2 (Code):** Imports & PDF loading (`Marcus-Aurelius-Meditations.pdf` $\to$ 293 chunks).
  - **Cell 3 (Code + Text Output):** Method 1 — Two-Stage Hierarchical Merging (Fine Cut $k=0.4 \to$ Centroid Cosine Merging at $\ge 0.65$).
  - **Cell 4 (Code + Text Output):** Method 2 — Contiguity-Constrained Agglomerative Hierarchical Clustering (AHC Scikit-Learn with adjacency matrix $A_{i,i+1}=1$).
  - **Cell 5 (Code + Text Output):** Method 3 — Gaussian Kernel Smoothed Minima ($\sigma=2.0$ noise-filtered valley detection).
  - **Cell 6 (Code + 3D Plot):** Plot 1: **3D PCA Vector Topology Scatter Plot ($PC_1, PC_2, PC_3$)** showing the sequential trajectory wire through 3D space with colored cluster spheres representing generated note candidates.
  - **Cell 7 (Code + 2D Plot):** Plot 2: **Gaussian Smoothed Minima Curve Overlay** showing raw similarity vs smoothed curve with red dots marking exact valley cut points.
  - **Cell 8 (Code + 4-Panel Plot):** Plot 3: **4-Strategy Subplot Comparison** showing horizontal candidate note spans side-by-side.
  - **Cell 9 (Markdown):** R&D summary table and final recommendation (Two-Stage Hierarchical Merging producing 15 cohesive notes for 128 pages).

---

### 3.3 Notebook 03: Multimodal Layout & OCR Inspection (`03_multimodal_pdf_and_ocr_inspection.ipynb`)

- **Objective:** Verification of PyMuPDF4LLM structural layout extraction, bounding boxes, and CPU OCR.
- **Cell-by-Cell Structure:**
  - **Cell 1 (Markdown):** Multimodal ingestion overview.
  - **Cell 2 (Code):** Document loading & PyMuPDF page parsing.
  - **Cell 3 (Code + Image Plot):** PDF Page Viewer displaying OpenCV/Matplotlib bounding boxes around headings, text blocks, tables, and figures.
  - **Cell 4 (Code + Image Gallery):** Sliced Image Gallery rendering extracted figures from `media/{slug}/fig_xx.png` with enclosing section captions.
  - **Cell 5 (Code + Markdown Diff):** Markdown Table Reconstruction Diff comparing extracted Markdown tables vs raw PDF text.

---

### 3.4 Notebook 04: The End-to-End Cognitive Memory Explorer (`04_end_to_end_cognitive_explorer.ipynb`)

- **Objective:** Complete end-to-end interactive journey from PDF ingestion to candidate review, SQLite storage, and `curate()` prefrontal working memory retrieval.
- **Cell-by-Cell Structure:**
  - **Cell 1 (Markdown):** EgoVault 3-Tier Cognitive Memory Engine overview.
  - **Cell 2 (Code):** Full PDF Ingestion of Marcus Aurelius Meditations into `chunks` and `chunks_vec`.
  - **Cell 3 (Code):** Candidate generation via two-stage semantic clustering into `note_candidates` table.
  - **Cell 4 (Code):** Interactive candidate review loop (`claim`, `create_note_from_candidate`, `skip`).
  - **Cell 5 (Code + Matplotlib Bar Chart):** Compression Ratio Dashboard comparing raw source tokens (76,155 words) vs distilled neocortical note tokens (~4,500 words).
  - **Cell 6 (Code + Retrieval Output):** `curate()` execution retrieving top 4–7 working memory slots with verbatim source chunk proof drill-down.

---

## 4. Execution & Pre-rendering Guidelines

- All `.ipynb` notebooks must be checked into `notebooks/` with pre-executed inline Matplotlib figures and text outputs so they can be inspected visually immediately upon opening in VS Code, Jupyter, or GitHub.
- Python CLI mirror scripts (`notebooks/demo_marcus_aurelius_segmentation.py` and `notebooks/demo_end_to_end_explorer.py`) generate high-definition PNG figures into `notebooks/assets/`.

