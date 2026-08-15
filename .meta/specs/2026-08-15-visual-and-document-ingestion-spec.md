# Spec: Visual, Image, and Complex Document Ingestion (Lean Multimodal)

**Date:** 2026-08-15 (Updated: 2026-08-15 — Post-Review Hardened & Zero-Hardcode)  
**Status:** Validated — Plan-Ready  
**Dependencies:** Unified ingest (`workflows/ingest.py`), VaultContext, `tools/media/`  
**Related Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md` (Cognitive Architecture, Tier 0 & Tier 1)

---

## 1. Context & Problem Statement

Currently, document ingestion in EgoVault has three major limitations:

1. **Isolated images are not supported** (architecture diagrams, infographics, screenshots, whiteboard photos).
2. **Current PDF extractor (`pypdf`) is simplistic:**
   - Destroys reading order on multi-column documents.
   - Turns tables into unformatted text soup.
   - Ignores all figures, graphs, and diagrams.
3. **Scanned PDFs (pages as images without text layer) fail** (`EmptyContentError`).

### The "Full-VLM at Ingestion" Anti-Pattern (Rejected)
Running a Vision-Language Model (VLM) on every image to generate textual descriptions at ingestion is inefficient:
- **Prohibitive compute cost:** Drastically slows down ingestion and consumes VRAM / API tokens on hundreds of potentially trivial images.
- **Information degradation:** Automated textual summaries lose the technical nuance of complex charts and architecture schematics.

### Architecture Decision: The "Lean Pointer" Model (Lazy Evaluation)
1. **At Ingestion (Tier 0 — 100% Deterministic & Free):**
   - Slice and store high-resolution images under `egovault-user/data/media/{slug}/`.
   - Insert clean Markdown pointers in source transcripts and chunks:  
     `![Figure 3: Native extracted caption](media/{slug}/fig_03.png)`.
   - Vectorize text and surrounding captions (zero VLM inference).
2. **At Consumption (Tier 1 — On Demand):**
   - **For Humans in Obsidian:** Direct visualization of high-definition images embedded in notes or sources.
   - **For LLM Agents via MCP:** The agent uses an explicit MCP tool `get_media(path)` to inspect images natively *only when its reasoning requires it*.

---

## 2. Ingestion Pipeline & Business Rules

```
VISUAL SOURCE (Complex PDF, Isolated Image, Scanned Document)
                     │
                     ▼
          [Fast Heuristic Probe (5ms)]
                     │
     ┌───────────────┼────────────────────────┐
     │               │                        │
[Digital PDF]    [Scanned PDF (<50 char/p)] [Isolated Image]
     │               │                        │
     ▼               ▼                        ▼
PyMuPDF4LLM /   RapidOCR (ONNX CPU)      Binary Storage
OpenDataLoader                                + Metadata
     │               │                        │
     └───────────────┬────────────────────────┘
                     ▼
          [Filtering & Deduplication]
   - MD5 hash per image (exclude if > 2 pages)
   - Min dimension filter (>= 250px)
   - Caption fallback: Enclosing section header
                     │
                     ▼
          [Structured Extraction]
   - Markdown text with headings (#, ##)
   - Markdown tables (| col1 | col2 |)
   - Figures sliced into data/media/{slug}/
   - Pointers inserted: ![Caption](media/{slug}/fig_xx.png)
                     │
                     ▼
        [Source Transcript (Tier 1)]
                     │
                     ▼
        Chunking ──► Chunk Embeddings ──► rag_ready
```

---

## 3. Strategy Details & Edge Case Resolutions

### 3.1 Digital PDF with Complex Layout (Tier 0.5 — CPU)
- **Engine:** `pymupdf4llm` or `opendataloader-pdf` (deterministic layout mode).
- **Behavior:**
  - Reconstructs multi-column reading order.
  - Converts native tables into structured Markdown tables.
  - Slices vector and raster images exceeding `config.ingest.pdf.min_image_dimension` (default: 250px).

### 3.2 Uncaptioned Diagrams & Figures (Semantic Fallback)
- **Problem:** Many slide decks and whitepapers contain uncaptioned diagrams lacking `Figure X:` labels. Without text, they would be invisible to semantic search.
- **Deterministic Rule:** If no native caption is found in the visual bounding box, the parser injects the **enclosing Markdown section header** into the pointer:
  `![Diagram in: ## 3.2 Data Flow Architecture](media/{slug}/fig_03.png)`.
  This injects semantic keywords into the chunk for BM25 and cosine search without VLM costs.

### 3.3 Deduplication of Repeated Images (Logos & Headers)
- **Problem:** Header banners, corporate logos, and template icons repeat on every page of a PDF, cluttering `media/`.
- **Deterministic Rule:** Compute MD5 hash of each extracted image. If the same hash appears on more than `max_repeated_image_count` pages (default: 2), the image is classified as a template artifact and discarded.

### 3.4 Scanned PDF / Pure Image Document (Tier 1 — Robust CPU OCR)
- **Automatic Detection:** Triggered if $\frac{\text{total\_characters}}{\text{page\_count}} < \text{scanned\_char\_threshold}$ (default: 50).
- **Engine:** **`rapidocr-onnxruntime`** (Pure ONNX Runtime, zero C++ compilation, Windows x64 CPU compatible, cold start $< 200\text{ ms}$, weight $< 15\text{ MB}$).
- **Fallback:** `pytesseract` if explicitly configured in `config/user.yaml`.

### 3.5 Isolated Images (Infographics, Diagrams, Screenshots)
- Stored in `egovault-user/data/media/{slug}/source_image.<ext>`.
- Generates a metadata transcript and standard Markdown pointer.

---

## 4. Locator Transition & Migration Path

- **Phase 1 (Legacy pypdf):** Existing PDF sources use line-based locators (`L120-L245`).
- **Phase 2 (Visual Ingestion):** New PDF ingestions produce page-precise locators (`p. 42-55`).
- **Migration Script:** `scripts/maintenance/reingest_pdf_sources.py` allows re-extracting legacy PDF sources to generate sliced figures and page numbers.

---

## 5. Components & Contracts

### 5.1 New Components

| Component | Role |
|---|---|
| `tools/media/parse_document.py` | Structural PDF parser (PyMuPDF4LLM) extracting Markdown + sliced images + tables |
| `tools/media/ocr_document.py` | OCR engine via RapidOCR ONNX for scanned documents |
| `tools/media/get_media.py` | Secure binary/base64 media reader for MCP and API surfaces |

### 5.2 Modified Components

| Component | Modification |
|---|---|
| `workflows/ingest.py` | Heuristic routing: digital PDF vs scanned PDF vs isolated image |
| `mcp/server.py` | Expose `get_media(file_path: str)` with strict path containment (`security.py`) |
| `core/config.py` & `config/system.yaml` | Add comprehensive `ingest.pdf` and `ingest.ocr` configuration |

---

## 6. Comprehensive Configuration (`config/system.yaml`)

```yaml
ingest:
  pdf:
    strategy: auto                  # auto | fast_native | layout | ocr
    scanned_char_threshold: 50      # OCR trigger threshold (characters per page)
    extract_images: true            # Slice and persist significant figures
    min_image_dimension: 250        # Minimum width/height in pixels
    max_repeated_image_count: 2     # MD5 deduplication threshold for headers/logos
  
  ocr:
    engine: rapidocr                # rapidocr | pytesseract
    languages:
      - fr
      - en

  image:
    supported_extensions:
      - .png
      - .jpg
      - .jpeg
      - .webp
      - .svg
    vlm_captioning: false           # false = Lean Pointer (default); true = VLM inference at ingest
```
