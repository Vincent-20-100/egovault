# Implementation Plan: Visual & Complex Document Ingestion (Phase 2)

**Date:** 2026-08-15  
**Status:** Plan-Ready  
**Related Spec:** [`.meta/specs/2026-08-15-visual-and-document-ingestion-spec.md`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/.meta/specs/2026-08-15-visual-and-document-ingestion-spec.md)  
**Related Vision:** [`docs/VISION-KNOWLEDGE-COMPILER.md`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/docs/VISION-KNOWLEDGE-COMPILER.md) (Tier 0 & Tier 1)  
**Prerequisite Dependency:** Phase 1 (Semantic Segmentation)

---

## 1. Objectives & Scope

1. Replace the basic `pypdf` extractor with a layout-aware structural parser preserving multi-column reading order and converting native tables to Markdown (`PyMuPDF4LLM` / `OpenDataLoader`).
2. Slice and extract high-definition figures into `data/media/{slug}/fig_xx.png`, referenced by clean Markdown pointers in chunks (`![Caption](media/{slug}/fig_xx.png)`).
3. Automatically detect and transcribe scanned PDFs using fast CPU OCR (`rapidocr-onnxruntime`).
4. Handle isolated image ingestion (diagrams, screenshots, infographics) using the Lean Pointer model.
5. Deduplicate repeating header banners and logos across pages via raw PDF image stream MD5 hashing.
6. Expose the MCP tool `get_media(file_path: str)` for on-demand visual inspection by LLM agents.
7. Execute safe PDF migration via `reingest_pdf_sources.py` preserving existing converted notes while re-segmenting unconverted candidates.

---

## 2. Task Breakdown

### Task 1: Structured PDF Parsing Engine (`tools/media/parse_document.py`)
- **File:** `tools/media/parse_document.py`
- **Tests:** `tests/tools/media/test_parse_document.py`
- **Actions:**
  1. Integrate `pymupdf4llm` for multi-column PDF to Markdown conversion.
  2. Extract and persist images exceeding `min_image_dimension` (default: 250px).
  3. Deduplicate images appearing across $> 2$ pages using raw byte-stream MD5 matching.
  4. Implement semantic caption fallback for uncaptioned images (injecting enclosing section heading).
  5. Attach page-level locators (`p. 42-55`).

### Task 2: Robust CPU OCR Engine (`tools/media/ocr_document.py`)
- **File:** `tools/media/ocr_document.py`
- **Tests:** `tests/tools/media/test_ocr_document.py`
- **Actions:**
  1. Integrate `rapidocr-onnxruntime` (ONNX CPU, Windows compatible without C++ runtime).
  2. Implement heuristic probe: trigger OCR if $\frac{\text{total\_characters}}{\text{page\_count}} < 50$.
  3. Reconstruct structured Markdown transcripts from OCR bounding boxes.

### Task 3: Isolated Image Ingestion & Pipeline Integration (`workflows/ingest.py`)
- **File:** `workflows/ingest.py`
- **Tests:** `tests/workflows/test_ingest_multimodal.py`
- **Actions:**
  1. Register `"image"` extractor in `_EXTRACTORS`: store under `media/{slug}/` and generate metadata transcript with `![Title](...)` pointer.
  2. Update `"pdf"` and `"livre"` extractors to use the new structural parser with automatic OCR fallback.
  3. Propagate page numbers to chunk results.

### Task 4: Media MCP Tool & Security Confinement (`tools/media/get_media.py`)
- **Files:** `tools/media/get_media.py`, `mcp/server.py`
- **Tests:** `tests/tools/media/test_get_media.py`, `tests/mcp/test_media_mcp.py`
- **Actions:**
  1. Create `get_media(file_path: str)`: validate path containment under `media_dir` via `security.py`, return binary/base64 payload with image dimensions and format metadata.
  2. Expose `get_media` on FastMCP server.

### Task 5: PDF Migration, Candidate Lifecycle & Re-ingestion Script
- **File:** `scripts/maintenance/reingest_pdf_sources.py`
- **Tests:** `tests/scripts/test_reingest_pdf_sources.py`
- **Actions:**
  1. Create maintenance script `reingest_pdf_sources.py` supporting `--dry-run` and `--source-uid`.
  2. **Candidate Lifecycle Management during Re-ingestion:**
     - Purge unconverted candidates (`queued`, `in_progress`, `skipped`) for the re-ingested source.
     - Re-run topic segmentation on new chunks to populate fresh `note_candidates`.
     - **Preserve Converted Notes:** Active notes linked to prior candidates retain their text and database rows; their historical candidate records are preserved with `"legacy_reingested": true` flag in metadata.
  3. Update architecture reference and user guide.
