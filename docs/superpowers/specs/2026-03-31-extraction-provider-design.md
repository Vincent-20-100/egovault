# Extraction Provider Design — with `ingest_web` and `ingest_text`

**Date:** 2026-03-31
**Status:** ~~Draft~~ **OBSOLETE — superseded by `2026-03-31-unified-ingest-architecture.md`**
**Roadmap item:** Backlog — Extraction provider (tiered architecture)
**Depends on:** Block A (complete), Block B (in progress)
**Reference:** `docs/product-audit/11-document-extraction.md`

> **⚠ This spec has been superseded.** See `2026-03-31-unified-ingest-architecture.md` for the definitive design.

---

## 1. Problem

EgoVault currently ingests three formats: YouTube, audio, and PDF. Two common knowledge-capture patterns have no ingestion path:

1. **Web articles** — the most frequent source type for a knowledge worker. No `ingest_web` exists.
2. **Plain text / clipboard** — quick capture of text from any source. No `ingest_text` exists.

The PDF pipeline uses a single library for extraction and has no fallback. Beyond these two gaps, DOCX/EPUB/PPTX support is desirable but lower priority.

The audit (`docs/product-audit/11-document-extraction.md`) proposes a tiered extraction provider. This spec covers:
- The extraction provider infrastructure
- Two new workflows: `ingest_web` and `ingest_text`
- A complete error catalog for all ingest pathways (new and future)

---

## 2. Scope

### In scope
- `infrastructure/extraction_provider.py` — tiered extraction with fallback
- `tools/text/extract_web.py` — web content extraction tool
- `workflows/ingest_web.py` — full pipeline: fetch URL → extract → chunk → embed → [generate note]
- `workflows/ingest_text.py` — full pipeline: validate text → chunk → embed → [generate note]
- Error types in `core/errors.py` for all ingest failures
- API endpoints: `POST /ingest/web`, `POST /ingest/text`
- CLI commands: `egovault ingest <url>` (auto-detect web), `egovault ingest --text`
- MCP tools: `ingest_web`, `ingest_text`
- Config additions to `system.yaml`
- Error catalog (section 8)

### Out of scope
- DOCX/EPUB/PPTX ingestion (future — same provider, new workflows)
- Tier 2 OCR (chandra) — spec covers the interface, not the implementation
- `ingest_image` — requires Tier 2, no CPU fallback
- Re-ingestion of existing sources

---

## 3. Tiered Extraction Provider

Follows the same pattern as `embedding_provider.py`.

### 3.1 Tiers

| Tier | Scope | GPU | Install weight | Capability |
|------|-------|-----|----------------|------------|
| **0 — Builtin** | `beautifulsoup4` + `requests` (web), `pypdf` (PDF) | No | ~5 MB | Basic text extraction |
| **1 — Standard** | markitdown (Microsoft) | No | ~10-50 MB | Structured markdown, tables, headings |
| **2 — OCR** | chandra (Datalab) | Yes | ~300 MB+ | Full OCR, scans, handwriting |

### 3.2 Fallback strategy

```
extract(input, format) →
  1. Detect format (from URL scheme, file extension, or explicit parameter)
  2. Read configured provider (system.yaml: extraction.provider)
  3. If "auto": try highest installed tier → fall back on failure
  4. If explicit tier: use it, error if not installed
```

Tier 0 is always available. Zero optional dependencies required.

### 3.3 Config

```yaml
# system.yaml additions
extraction:
  provider: auto           # auto | builtin | markitdown | chandra
  web:
    timeout_seconds: 30    # max time to fetch a URL
    max_content_bytes: 10485760  # 10 MB — max raw HTML size
    min_content_chars: 100       # minimum extracted text length (paywall detection)
  text:
    min_chars: 10          # minimum input text length
    max_chars: 5000000     # ~5 MB of text
```

### 3.4 Interface

```python
# infrastructure/extraction_provider.py

class ExtractionResult(BaseModel):
    """Result of content extraction."""
    text: str                        # extracted plain text or markdown
    title: str | None = None         # extracted title (web pages, PDFs)
    metadata: dict = {}              # provider-specific metadata (word count, language, etc.)

def extract_web(url: str, settings: Settings) -> ExtractionResult:
    """Fetch and extract article content from a URL."""

def extract_file(file_path: str, settings: Settings) -> ExtractionResult:
    """Extract text content from a local file (PDF, DOCX, etc.)."""
```

---

## 4. `ingest_web` Workflow

### 4.1 Pipeline

```
validate_url → fetch_page → extract_content → chunk → embed → [generate_note]
```

Status transitions: `raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]`

Reuses the same status model as other ingest workflows. The "transcribing" step maps to "fetching + extracting" for web sources.

### 4.2 Source record

```python
Source(
    uid=generate_uid(),
    slug=make_unique_slug(extracted_title or domain_name, existing_slugs),
    source_type="web",
    status="raw",
    url=url,
    title=extracted_title,
    date_added=today,
)
```

### 4.3 Duplicate detection

Before creating a new source, check if a source with the same canonical URL already exists. If so, raise `DuplicateSourceError`. URL canonicalization: strip trailing slashes, remove tracking parameters (`utm_*`, `fbclid`, `gclid`), normalize to HTTPS.

---

## 5. `ingest_text` Workflow

### 5.1 Pipeline

```
validate_text → chunk → embed → [generate_note]
```

Status transitions: `raw → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]`

No "transcribing" step — text is already in final form.

### 5.2 Source record

```python
Source(
    uid=generate_uid(),
    slug=make_unique_slug(title or f"text-{date}", existing_slugs),
    source_type="personnel",  # or configurable
    status="raw",
    title=title,               # user-provided, optional
    date_added=today,
)
```

### 5.3 API contract

```python
class IngestTextRequest(BaseModel):
    text: str
    title: str | None = None
    source_type: str = "personnel"
    auto_generate_note: bool | None = None
```

---

## 6. API Endpoints

### 6.1 `POST /ingest/web`

**Request:**
```json
{
  "url": "https://example.com/article",
  "auto_generate_note": true
}
```

**Response (202):**
```json
{
  "job_id": "abc123"
}
```

Same async job pattern as existing ingest endpoints.

### 6.2 `POST /ingest/text`

**Request:**
```json
{
  "text": "Content to ingest...",
  "title": "My capture",
  "source_type": "personnel",
  "auto_generate_note": true
}
```

**Response (202):**
```json
{
  "job_id": "abc123"
}
```

---

## 7. CLI Integration

### 7.1 Auto-detection update

`_detect_type()` in `cli/commands/ingest.py` gains web URL detection:

```
if target starts with http:// or https:// and is not a YouTube URL → "web"
```

### 7.2 Text ingestion

New subcommand or flag:

```bash
egovault ingest --text "Paste your content here"
egovault ingest --text --file notes.txt     # read from file
echo "content" | egovault ingest --text -   # read from stdin
```

---

## 8. Error Catalog

Every ingest failure must produce a clear, actionable, user-facing message. No internal details (library names, stack traces, file paths) may appear in user-facing output — per G1, G2, G6.

### 8.1 Error types in `core/errors.py`

New error classes (all extend `Exception`):

| Error class | Purpose |
|---|---|
| `IngestError` | Base class for all ingest failures. Carries `error_code`, `user_message`, `http_status`. |
| `UrlUnreachableError(IngestError)` | Network failure, DNS error, connection refused |
| `UrlTimeoutError(IngestError)` | Page took too long to load |
| `InvalidUrlError(IngestError)` | Malformed or unsupported URL scheme |
| `PaywallDetectedError(IngestError)` | Content too short or login wall detected |
| `ContentExtractionError(IngestError)` | No article body found after extraction |
| `ContentTooLargeError(IngestError)` | Content exceeds configured size limit |
| `ContentEncodingError(IngestError)` | Unreadable encoding after extraction |
| `EmptyContentError(IngestError)` | Empty text provided or extracted |
| `ContentTooShortError(IngestError)` | Text below meaningful threshold |
| `DuplicateSourceError(IngestError)` | URL or content already ingested |
| `ChunkingError(IngestError)` | Chunking pipeline failure |
| `EmbeddingServiceError(IngestError)` | Embedding provider unavailable or failed |
| `DatabaseWriteError(IngestError)` | Database write failure during ingest |

### 8.2 Base class design

```python
class IngestError(Exception):
    """Base class for ingest failures with structured error information."""

    def __init__(self, error_code: str, user_message: str, http_status: int = 400):
        self.error_code = error_code
        self.user_message = user_message
        self.http_status = http_status
        super().__init__(user_message)
```

The `error_code` is a stable machine-readable identifier for programmatic handling. The `user_message` is the human-readable string shown to users. The `http_status` is used by the API layer for HTTP responses.

### 8.3 Web ingestion errors

| Error class | `error_code` | `http_status` | User-facing message |
|---|---|---|---|
| `InvalidUrlError` | `invalid_url` | 400 | "The URL is invalid or uses an unsupported format. Check the URL and try again." |
| `UrlUnreachableError` | `url_unreachable` | 502 | "Could not reach the URL. Check your internet connection and verify the URL is correct." |
| `UrlTimeoutError` | `url_timeout` | 504 | "The page took too long to respond. Try again later or check if the site is available." |
| `PaywallDetectedError` | `paywall_detected` | 422 | "This page appears to require authentication. EgoVault cannot ingest paywalled or login-protected content." |
| `ContentExtractionError` | `extraction_failed` | 422 | "No article content found on this page. The URL may point to a non-article page (login, homepage, media file, etc.)." |
| `ContentTooLargeError` | `content_too_large` | 413 | "The page content exceeds the configured size limit. Consider ingesting a smaller page or adjusting the limit in system.yaml." |
| `ContentEncodingError` | `encoding_error` | 422 | "The page content could not be decoded. The page may use an unsupported character encoding." |
| `DuplicateSourceError` | `duplicate_source` | 409 | "This URL has already been ingested. Use search to find the existing source." |

### 8.4 Text ingestion errors

| Error class | `error_code` | `http_status` | User-facing message |
|---|---|---|---|
| `EmptyContentError` | `empty_content` | 400 | "The provided text is empty. Please provide content to ingest." |
| `ContentTooShortError` | `content_too_short` | 400 | "The provided text is too short to produce meaningful results. Please provide more content." |
| `ContentTooLargeError` | `content_too_large` | 413 | "The provided text exceeds the configured size limit. Consider splitting it into smaller pieces or adjusting the limit in system.yaml." |

### 8.5 General ingest errors (apply to all pathways)

These errors can occur in any ingest workflow (YouTube, audio, PDF, web, text).

| Error class | `error_code` | `http_status` | User-facing message |
|---|---|---|---|
| `ChunkingError` | `chunking_failed` | 500 | "Content processing failed during text segmentation. This is unexpected — please report it." |
| `EmbeddingServiceError` | `embedding_unavailable` | 503 | "The embedding service is not available. Check that the configured provider is running and accessible." |
| `DatabaseWriteError` | `db_write_failed` | 500 | "Failed to save the ingested content. This may indicate a database issue — check disk space and permissions." |
| `LargeFormatError` | `large_format` | 200 (job succeeds) | "Source is too large for automatic note generation. It has been indexed and is searchable. Create the note manually." |

Note: `LargeFormatError` already exists in `core/errors.py`. It is not an `IngestError` subclass because the ingest itself succeeds (source reaches `rag_ready`). The error is raised after successful ingestion to signal that note generation was skipped.

### 8.6 CLI output format

The CLI displays errors using the existing `print_error()` helper from `cli/output.py`. The `error_code` is used as the error type label.

**Standard mode:**
```
✗ Could not reach the URL. Check your internet connection and verify the URL is correct.
```

**Verbose mode:**
```
✗ Could not reach the URL. Check your internet connection and verify the URL is correct.
  [url_unreachable] ConnectionError: <redacted detail from sanitize_error()>
```

**JSON mode:**
```json
{
  "error": true,
  "code": "url_unreachable",
  "message": "Could not reach the URL. Check your internet connection and verify the URL is correct."
}
```

### 8.7 API error response format

All `IngestError` subclasses are caught by a FastAPI exception handler that returns:

```python
@app.exception_handler(IngestError)
async def ingest_error_handler(request, exc: IngestError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": exc.error_code, "message": exc.user_message},
    )
```

For async job failures (the ingest runs in a background thread), the error is stored in the job record:

```python
# In _run_web / _run_text job functions
except IngestError as e:
    update_job_failed(system_db, job_id, e.user_message)
except Exception as e:
    update_job_failed(system_db, job_id, sanitize_error(e))
```

The `GET /jobs/{id}` response for a failed job includes:
```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "Could not reach the URL. Check your internet connection and verify the URL is correct."
}
```

### 8.8 MCP error handling

MCP tools surface errors via the standard MCP error mechanism. The `user_message` is returned directly — no internal details.

### 8.9 Error detection logic

How each error condition is detected:

| Error | Detection |
|---|---|
| `InvalidUrlError` | URL parsing fails, or scheme is not `http`/`https` |
| `UrlUnreachableError` | `ConnectionError`, `DNSLookupError`, or response status 5xx after retries |
| `UrlTimeoutError` | Request exceeds `extraction.web.timeout_seconds` |
| `PaywallDetectedError` | Extracted text length < `extraction.web.min_content_chars` AND page returned 200 (content was served but is gated) |
| `ContentExtractionError` | Extraction returns empty or near-empty text from a page that returned 200 with substantial HTML |
| `ContentTooLargeError` | Raw HTML exceeds `extraction.web.max_content_bytes` OR text exceeds `extraction.text.max_chars` |
| `ContentEncodingError` | `UnicodeDecodeError` or detected encoding is not decodable |
| `EmptyContentError` | Input text is empty or whitespace-only |
| `ContentTooShortError` | Input text length < `extraction.text.min_chars` |
| `DuplicateSourceError` | Canonical URL matches an existing source's URL in the database |
| `ChunkingError` | Unexpected exception during `chunk_text()` |
| `EmbeddingServiceError` | Connection refused, timeout, or error response from the embedding provider |
| `DatabaseWriteError` | SQLite write failure (disk full, locked, schema mismatch) |

### 8.10 Mapping existing ingest errors

The existing YouTube, audio, and PDF workflows currently use generic `Exception` handling. As part of this work, wrap known failure modes in the appropriate `IngestError` subclass:

| Existing workflow | Current behavior | Target behavior |
|---|---|---|
| `ingest_youtube` — bad URL | `validate_youtube_url` returns `None` → HTTP 400 | Raise `InvalidUrlError` |
| `ingest_youtube` — subtitles unavailable | Generic exception | Raise `ContentExtractionError("No subtitles available...")` |
| `ingest_audio` — file not found | `FileNotFoundError` | Keep as-is (not an `IngestError` — it's a local file issue) |
| `ingest_pdf` — empty extraction | Returns empty string, proceeds | Raise `EmptyContentError` |
| All workflows — embedding failure | Generic exception caught by `sanitize_error` | Raise `EmbeddingServiceError` |

---

## 9. Implementation Sketch

### 9.1 New files

```
infrastructure/extraction_provider.py    ← ExtractionProvider with tier fallback
tools/text/extract_web.py               ← Web content extraction tool
workflows/ingest_web.py                 ← Web ingestion pipeline
workflows/ingest_text.py                ← Text ingestion pipeline
tests/workflows/test_ingest_web.py
tests/workflows/test_ingest_text.py
tests/infrastructure/test_extraction_provider.py
tests/tools/text/test_extract_web.py
```

### 9.2 Modified files

```
core/errors.py                          ← New IngestError hierarchy
core/schemas.py                         ← IngestTextRequest, IngestWebRequest, ExtractionResult
config/system.yaml                      ← extraction section
api/routers/ingest.py                   ← /ingest/web, /ingest/text endpoints
api/models.py                           ← Request/response models
cli/commands/ingest.py                  ← Web URL detection, --text flag
mcp/server.py                           ← ingest_web, ingest_text tools
workflows/ingest_youtube.py             ← Wrap errors in IngestError subclasses
workflows/ingest_pdf.py                 ← Wrap errors in IngestError subclasses
workflows/ingest_audio.py               ← Wrap errors in IngestError subclasses
```

---

## 10. Open Questions

1. **Paywall detection heuristic** — `min_content_chars` is a rough proxy. Should we also check for common paywall indicators (specific meta tags, known paywall domains)? Start simple, iterate.
2. **JavaScript-rendered pages** — Tier 0 (requests + beautifulsoup) cannot handle SPAs. Should we document this limitation or add optional browser-based extraction (playwright)? Recommendation: document the limitation, defer browser extraction.
3. **URL canonicalization scope** — Which tracking parameters to strip? Start with `utm_*`, `fbclid`, `gclid`, `ref`. Configurable list in `system.yaml` if needed later.
4. **`ingest_text` source_type** — Default to `personnel`? Or add a new `text` source type to taxonomy? The audit lists `personnel` as "no external source, personal reflection" which fits.
5. **Rate limiting for web fetches** — Should we add a delay between consecutive fetches to avoid being blocked? Not needed for single-URL ingestion, relevant for future `ingest_playlist` / batch ingestion.

---

## 11. Non-Goals

- This spec does not cover `ingest_image` (requires Tier 2 OCR with no CPU fallback).
- This spec does not cover batch ingestion or crawling.
- This spec does not change the chunking or embedding pipeline — only the extraction step.
- Tier 1 (markitdown) and Tier 2 (chandra) are specced as interfaces. Only Tier 0 is implemented in the first pass.
