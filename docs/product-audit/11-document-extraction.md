# 11. Document extraction — tiered architecture

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 11.1 Problem

Current PDF extraction (`ingest_pdf.py:33-38`) uses `pypdf.PdfReader.extract_text()` — a text-layer-only approach. This returns empty strings on scanned PDFs, loses table structure, ignores images and diagrams, and has no layout awareness. The codebase comment (`ingest_pdf.py:11`) already acknowledges this: *"Docling is a future upgrade for better layout analysis."*

Beyond PDF, EgoVault has no ingestion path for DOCX, EPUB, PPTX, or web HTML — all common knowledge source formats.

## 11.2 Tiered extraction design

The extraction provider follows the same pattern as `embedding_provider.py` (Ollama/OpenAI). Three tiers with automatic fallback:

| Tier | Library | Formats | GPU | Install weight | Quality |
|------|---------|---------|-----|----------------|---------|
| **0 — Builtin** | `pypdf`, `python-docx`, `python-pptx`, `ebooklib`, `beautifulsoup4` | PDF, DOCX, PPTX, EPUB, HTML | No | ~5MB total | Basic text extraction, no layout |
| **1 — Standard** | **markitdown** (Microsoft) | PDF, DOCX, PPTX, XLSX, EPUB, HTML, images (basic) | No | ~10-50MB | Structured markdown, tables, headings preserved |
| **2 — OCR** | **chandra** (Datalab) | PDF, images | Yes (or hosted API) | ~300MB+ models | Full OCR: scans, handwriting, math, complex tables, image extraction + captions |

## 11.3 Fallback strategy

```
User calls ingest(file) →
  1. Detect format from extension
  2. Check configured provider (system.yaml: extraction.provider)
  3. If "auto": try highest available tier → fall back on failure/missing install
  4. If explicit tier: use it, error if not installed
```

**Critical principle:** EgoVault MUST work out-of-the-box with zero optional dependencies. Tier 0 (builtin) is always available. markitdown and chandra are progressive enhancements.

## 11.4 Builtin fallback per format

| Format | Builtin library | What it extracts | What it misses |
|--------|----------------|------------------|----------------|
| **PDF** | `pypdf` | Text layer | Scans, images, tables, layout |
| **DOCX** | `python-docx` (~1MB) | Paragraphs, headings, basic tables | Complex formatting, embedded images |
| **PPTX** | `python-pptx` (~1MB) | Slide text, notes | Images, diagrams, layouts |
| **EPUB** | `ebooklib` (~500KB) | HTML content → text | Images, complex formatting |
| **HTML/web** | `beautifulsoup4` + `requests` | Article text | Dynamic content, JS-rendered pages |
| **Image** | None — skip with clear message | — | Everything (requires OCR) |

All builtin libs are lightweight, CPU-only, well-maintained, and have no conflicting dependencies.

## 11.5 markitdown — the middle ground

[markitdown](https://github.com/microsoft/markitdown) (Microsoft, MIT license) is the recommended Tier 1 provider:

- **One library, all formats:** PDF, DOCX, PPTX, XLSX, EPUB, HTML, images (basic OCR), audio, video
- **Output:** LLM-optimized markdown with structure preservation (headings, tables, lists)
- **CPU-only**, lightweight (~10-50MB), optional feature groups (install only what you need)
- **API:**
  ```python
  from markitdown import MarkItDown
  md = MarkItDown()
  result = md.convert("document.pdf")  # or .docx, .html, .epub, .pptx
  text = result.text_content            # → structured markdown
  ```
- Solves `ingest_web` (HTML extraction) and improves `ingest_pdf` (better tables/structure) in one dependency

## 11.6 chandra — advanced OCR (Tier 2)

[chandra](https://github.com/datalab-to/chandra) (Datalab, Apache 2.0 code / OpenRAIL-M models) is the recommended Tier 2 provider:

- **State of the art OCR:** scanned PDFs, handwritten text, mathematical formulas, complex tables, forms with checkboxes
- **Image extraction + captioning:** extracts embedded images and generates structured descriptions
- **90+ languages**, strong multilingual performance (77.8% average vs 60.5% for GPT-5 Mini)
- **Output:** markdown + HTML + JSON metadata + extracted images
- **Requires GPU** or hosted API (`datalab.to/pricing` — free for startups under $2M)
- **API:**
  ```python
  # CLI: chandra input.pdf ./output --method hf
  # Or via vLLM server for batch processing
  ```
- **License consideration:** model weights use OpenRAIL-M (free for research, personal use, startups under $2M funding/revenue). Code is Apache 2.0.

## 11.7 Implementation sketch

```
infrastructure/
  extraction_provider.py    ← ExtractionProvider interface + 3 implementations

core/schemas.py             ← new schemas:
  ExtractionResult(markdown: str, images: list[ImageRef], metadata: dict)
  ImageRef(path: str, caption: str | None, page: int | None)

config/system.yaml          ← new section:
  extraction:
    provider: auto           # auto | builtin | markitdown | chandra
    chandra:
      method: hf             # hf | vllm | datalab-api
      api_key: null           # only for datalab-api (stored in install.yaml)
```

**Workflow impact:** minimal. Only the extraction step changes:

```python
# Before (ingest_pdf.py)
text = _extract_pdf_text(file_path)           # pypdf, plain text

# After (any ingest workflow)
result = extract(file_path, settings)          # provider-driven
text = result.markdown                         # structured markdown
images = result.images                         # [] if Tier 0/1, populated if Tier 2
```

The rest of the pipeline (chunk → embed → rag_ready) remains identical.

## 11.8 What this unlocks

With a single `extraction_provider.py` + markitdown as Tier 1:

| New capability | Marginal cost | Notes |
|----------------|---------------|-------|
| `ingest_web` (HTML articles) | Near-zero | Same pipeline after extraction |
| `ingest_docx` (Word documents) | Near-zero | Same pipeline after extraction |
| `ingest_epub` (Ebooks) | Near-zero | Same pipeline after extraction |
| `ingest_pptx` (Presentations) | Near-zero | Same pipeline after extraction |
| Better PDF extraction (tables, structure) | Zero — replacement | markitdown > pypdf |
| `ingest_image` (screenshots, photos) | Tier 2 only | Requires chandra, no CPU fallback |

These could be exposed as individual CLI commands (`egovault ingest web <url>`, `egovault ingest document <file>`) or as a unified `ingest_document` that auto-detects format.

## 11.9 Priority and roadmap position

This is **not blocking** (current PDF/YouTube/audio workflows work). Recommended position:

```
After: CLI + MCP flow fix + Delete operations (Tier 1-2 features)
Before: Frontend (frontend will want drag & drop for all formats)
Brainstorming: superpowers:brainstorming on extraction provider architecture
```

The brainstorming should cover: fallback behavior, image handling strategy (see 10.9), config UX, and how extraction quality impacts chunking/embedding downstream.
