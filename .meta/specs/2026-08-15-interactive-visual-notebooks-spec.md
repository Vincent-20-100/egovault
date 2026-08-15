# Spec: Interactive Visual Notebooks & End-to-End Cognitive Memory Explorer

**Date:** 2026-08-15  
**Status:** Spec-Ready  
**Related Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md` (Cognitive Architecture & 3-Tier Memory Engine)  
**Output Directory:** `notebooks/`

---

## 1. Context & Motivation

EgoVault relies on non-trivial mathematical and topological concepts:
1. **Tier 0:** Consecutive cosine similarity drop detection (TextTiling) on chunk embedding trajectories.
2. **Tier 1 vs. Tier 2 Topology:** Dual vector spaces (`chunks_vec` vs `notes_vec`) representing raw episodic evidence vs. condensed neocortical conceptual centroids.
3. **Tier 3 Context Assembly:** Spreading activation, Reciprocal Rank Fusion (RRF), and working memory slot allocation (4–7 mental models).
4. **Multimodal Extraction:** Structural PDF layout parsing, bounding box OCR, and high-definition figure slicing.

While unit tests validate functional correctness, **interactive visual notebooks** provide:
- Instant hyperparameter calibration (tuning TextTiling sensitivity $k$, similarity floor $S_{\text{min}}$, RRF $k=60$).
- Visual empirical proof of the cognitive compression advantage (1 bloated note vs $N$ cohesive conceptual nuclei).
- An intuitive, interactive playground for researchers, developers, and power users.

---

## 2. Notebook Suite Architecture

```
notebooks/
├── 01_topic_segmentation_visualizer.ipynb      ← (Phase 1) TextTiling curve, depth scores, and candidate merges
├── 02_dual_vector_space_topology.ipynb         ← (Curate) 2D/3D UMAP space of chunks vs notes, spreading activation
├── 03_multimodal_pdf_and_ocr_inspection.ipynb  ← (Phase 2) OCR bounding boxes, sliced figures, and Markdown tables
├── 04_end_to_end_cognitive_explorer.ipynb      ← Complete end-to-end interactive pipeline walkthrough
└── README.md                                   ← Guide for running notebooks
```

---

## 3. Detailed Specifications per Notebook

### 3.1 Notebook 01: Thematic Boundary Visualizer (`01_topic_segmentation_visualizer.ipynb`)
- **Primary Focus:** Mathematical inspection of the consecutive cosine TextTiling algorithm on real sources (e.g. *Antifragile*, *Masterclass ECM/DCM*).
- **Interactive Visualizations:**
  1. **Trajectory Plot:** Continuous curve of consecutive cosine similarities $s_i = \cos(v_i, v_{i+1})$.
  2. **Trough & Peak Detection:** Flanking peak detection ($\max_{\text{left}}, \max_{\text{right}}$) and calculated Valley Depth Scores $d_i$.
  3. **Adaptive Threshold Overlays:**
     - Horizontal dashed lines for $\mu_d + k \cdot \sigma_d$ (adaptive boundary threshold).
     - Horizontal solid line for $S_{\text{min}}$ (absolute similarity floor).
  4. **Segmentation Spans:** Vertical red boundary markers and pastel color-banded regions displaying raw segments and final merged note candidates.
  5. **Parameter Sliders (ipywidgets):** Live slider to tweak $k \in [0.1, 2.0]$ and $S_{\text{min}} \in [0.2, 0.6]$ and observe boundary splits in real-time.

---

### 3.2 Notebook 02: Dual-Vector Space Topology & Curate Drill-Down (`02_dual_vector_space_topology.ipynb`)
- **Primary Focus:** Topological comparison between Tier 1 (Hippocampal Chunks) and Tier 2 (Neocortical Notes).
- **Interactive Visualizations:**
  1. **2D/3D Dimension Reduction (UMAP / t-SNE / PCA):**
     - Blue scatter points: Raw source chunks.
     - Gold centroid markers: Distilled conceptual notes.
     - Clusters highlighted by tag and topic.
  2. **Query Activation Path:**
     - A user query point plotted in the vector space.
     - Visual vectors linking the query to top activated notes, with dotted drill-down lines connecting notes back to their underlying source chunks.
  3. **RRF vs. Pure Cosine Search Comparison:** Side-by-side rank distribution graphs.

---

### 3.3 Notebook 03: Multimodal Layout & OCR Inspection (`03_multimodal_pdf_and_ocr_inspection.ipynb`)
- **Primary Focus:** Verification of structural document layout extraction and CPU OCR.
- **Interactive Visualizations:**
  1. **PDF Page Viewer with Bounding Boxes:** Original PDF page rendered with matplotlib/OpenCV bounding boxes around headings, text columns, tables, and figures.
  2. **Sliced Image Gallery:** Displaying figures extracted into `media/{slug}/fig_xx.png` with their enclosing section captions.
  3. **Markdown Reconstruction Diff:** Side-by-side view of extracted Markdown tables vs. raw PDF rendering.

---

### 3.4 Notebook 04: The End-to-End Cognitive Memory Explorer (`04_end_to_end_cognitive_explorer.ipynb`)
- **Primary Focus:** Complete end-to-end interactive journey from ingestion to intelligence synthesis.
- **Sequential Pipeline Steps:**
  1. **Ingest:** Load a complex document (YouTube audio or PDF).
  2. **Chunk & Embed:** Generate chunks and compute unit embeddings (`chunks_vec`).
  3. **Segment:** Run TextTiling, visualize boundaries, and inspect the generated `note_candidates` queue.
  4. **Synthesize:** Claim candidate and generate a structured note using the configured LLM provider.
  5. **Embed Note:** Embed the newly generated note into `notes_vec`.
  6. **Curate:** Query the vault and view the assembled prefrontal working memory context (4–7 conceptual slots) with full verbatim source proof.
  7. **Metrics Dashboard:** Compression ratio (Tokens in Chunks vs. Tokens in Notes), retrieval precision, and latency profiling.

---

## 4. Dependencies & Implementation Strategy

- Visualization packages: `matplotlib`, `seaborn`, `plotly` (for interactive HTML graphs), `umap-learn` (for 2D/3D manifold projections).
- Stored under `notebooks/` with clear runnable cells consuming the standard `VaultContext` without mocking.
- Notebook 01 will be created in conjunction with Phase 1 Task 1.
