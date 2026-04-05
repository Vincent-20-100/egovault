# Unified Ingest Architecture

**Date:** 2026-03-31
**Updated:** 2026-04-01 (brainstorm adaptations)
**Status:** VALIDATED — ready for planning and implementation
**Priority:** SUPERIOR to all prior ingest/extraction specs
**Supersedes:** `2026-03-31-extraction-provider-design.md`, `2026-03-31-ingest-text-web-design.md`
**Brainstorm notes:** `specs/2026-04-01-unified-ingest-notes.md`

> **This spec is the single source of truth for all ingest-related architecture.**
> Any contradiction between this spec and prior specs, CLAUDE.md, or existing code
> must be resolved in favor of this document. A full implementation audit is required
> after execution to verify compliance.
>
> **2026-04-01 adaptations:** All code uses `ctx: VaultContext` (not `settings`).
> §15 (source_assets) and §16 (crash recovery) are **DEFERRED** — not in V1.
> See brainstorm notes for full decision rationale.

---

## 1. Problem

### 1.1 Duplication

The three existing workflows (`ingest_youtube`, `ingest_audio`, `ingest_pdf`) are **90% identical**. The only step that varies is text extraction:

| Step | YouTube | Audio | PDF | Shared? |
|------|---------|-------|-----|---------|
| Create source record | ✓ | ✓ | ✓ | **Identical** |
| Extract text | fetch_subtitles | compress → transcribe | pypdf extract | **Different** |
| Store transcript | ✓ | ✓ | ✓ | **Identical** |
| Token count check | ✓ | ✓ | ✓ | **Identical** |
| Chunk text | ✓ | ✓ | ✓ | **Identical** |
| Embed chunks | ✓ | ✓ | ✓ | **Identical** |
| LargeFormatError check | ✓ | ✓ | ✓ | **Identical** |
| Auto-generate note | ✓ | ✓ | ✓ | **Identical** |
| Return source | ✓ | ✓ | ✓ | **Identical** |

Even `_llm_is_configured()` is copy-pasted verbatim in all three files.

### 1.2 Scaling problem

Adding `ingest_web` and `ingest_text` would create 5 workflows (and growing). Future formats (DOCX, EPUB, PPTX, Markdown, JSON) would push this to 8+. Each new format means:
- A new workflow file (~120 lines, 90% copy-paste)
- New API endpoint
- New CLI dispatch branch
- New MCP tool
- New test file (~200 lines, 90% copy-paste)

### 1.3 Hardcoding problem

Type-specific constants are duplicated across layers:
- `_AUDIO_EXTENSIONS` exists in both `cli/commands/ingest.py` and `api/routers/ingest.py`
- Upload size limits are separate config keys (`max_audio_mb`, `max_pdf_mb`)
- API has three separate endpoints, three separate worker functions

---

## 2. Proposed Architecture

### 2.1 N pipeline families (extensible)

Ingest sources are organized into **pipeline families**. Each family defines an ordered sequence of steps. The architecture supports **N families** — new families can be added by registering a new pipeline, without modifying existing code.

**V1 families (implemented now):**

**Family A — Document pipeline** (text-based sources)
```
[extract text] → chunk → embed → [generate_note]
```
Sources: PDF, plain text, YouTube (subtitles mode)

**Family B — Media pipeline** (audio/video requiring transcription)
```
[prepare audio] → transcribe → chunk → embed → [generate_note]
```
Sources: audio files, video files, YouTube (transcription mode)

**Key insight:** The media pipeline produces text, then feeds it into the document pipeline's common steps (chunk → embed → generate_note). So Family B is really:
```
[prepare audio] → transcribe → DOCUMENT PIPELINE
```

**Future families (hooks must exist in V1 architecture):**
- **Family C — Web pipeline:** fetch → sanitize → parse HTML → document pipeline (requires security brainstorm)
- **Family D — Structured data:** parse JSON/CSV/DB → transform → chunk → embed
- **Family E — Interactive:** parse chat/thread export → chunk → embed

Each family is registered in the extractor registry with its pipeline definition. Adding a family = adding a pipeline function + registering source types. Zero changes to the common pipeline, surfaces, or tests.

### 2.2 YouTube spans both families

YouTube is dispatched based on subtitle availability:
- **Subtitles found** → Family A (fetch_subtitles returns text, feed into document pipeline)
- **No subtitles** → Family B (download audio → compress → transcribe → document pipeline)

This is already how `fetch_subtitles` works — it has a fallback to transcription. The difference is architectural clarity.

### 2.3 Unified workflow with pluggable extractors

```python
# workflows/ingest.py

def ingest(
    source_type: str,
    target: str,                    # URL, file path, or raw text
    settings: Settings,
    title: str | None = None,
    auto_generate_note: bool | None = None,
) -> Source:
    """
    Unified ingest pipeline. Dispatches to the right extractor
    based on source_type, then runs the common pipeline.
    """
    # 1. Extract text (the only step that varies)
    text, metadata = _extract(source_type, target, settings)

    # 2. Common pipeline
    source = _create_source(source_type, target, title, metadata, settings)
    _store_and_embed(source, text, settings)

    # 3. Optional note generation
    _maybe_generate_note(source, text, auto_generate_note, settings)

    return get_source(settings.vault_db_path, source.uid)
```

### 2.4 Extractor registry

```python
# Extractor functions — each returns (text: str, metadata: dict)
# New families/extractors are added here — zero changes to the common pipeline.
_EXTRACTORS: dict[str, Callable] = {
    # Family A — Document pipeline
    "pdf":       _extract_pdf,
    "livre":     _extract_pdf,         # same pipeline, different taxonomy value
    "texte":     _extract_text,
    # Family B — Media pipeline
    "youtube":   _extract_youtube,
    "audio":     _extract_audio,
    "video":     _extract_audio,       # same pipeline
    # FUTURE: "web": _extract_web (requires security brainstorm)
    # FUTURE: "docx": _extract_docx, "epub": _extract_epub, etc.
}

def _extract(source_type: str, target: str, settings: Settings) -> tuple[str, dict]:
    extractor = _EXTRACTORS.get(source_type)
    if extractor is None:
        raise ValueError(f"No extractor for source type '{source_type}'")
    return extractor(target, settings)
```

### 2.5 Extractor functions (micro-tools)

Each extractor is a small function that returns `(text, metadata)`:

```python
def _extract_youtube(target: str, settings: Settings) -> tuple[str, dict]:
    """Fetch subtitles from YouTube URL."""
    result = fetch_subtitles(target, settings)
    return result.text, {"language": result.language, "source": result.source}

def _extract_audio(target: str, settings: Settings) -> tuple[str, dict]:
    """Compress and transcribe audio/video file."""
    compressed = compress_audio(target)
    result = transcribe(compressed.output_path)
    return result.text, {"language": result.language, "duration": result.duration_seconds}

def _extract_pdf(target: str, settings: Settings) -> tuple[str, dict]:
    """Extract text from PDF file."""
    import pypdf
    reader = pypdf.PdfReader(target)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    return text, {"page_count": len(reader.pages)}

# FUTURE: _extract_web — requires security brainstorm before implementation
# Will use parse_html (Tier 0) or higher tiers for content extraction
# Web fetch + SSRF prevention in a dedicated secure fetch layer

def _extract_text(target: str, settings: Settings) -> tuple[str, dict]:
    """Identity extractor — text is already in final form."""
    return target, {}
```

### 2.6 Adding a new format in the future

To add DOCX ingestion:
1. Add `"docx"` to `system.yaml:taxonomy.source_types`
2. Add `_extract_docx()` function in `workflows/ingest.py`
3. Register in `_EXTRACTORS`
4. Add file extension mapping in config
5. Done — CLI, API, MCP all work automatically

**Zero changes** to the common pipeline, API routing, CLI dispatch, or MCP tools.

---

## 3. New tool: `parse_html` (local, no network)

> **Note:** Web fetching (HTTP requests) is **FUTURE WORK** requiring a dedicated security brainstorm (SSRF, DNS rebinding, rate limiting). This section covers only the **local HTML parser** — takes an HTML string as input, returns extracted text.

### 3.1 Purpose

Atomic tool: HTML string → extracted article text + metadata. Zero network access. Will become Tier 0 extractor when web ingestion is added later.

### 3.2 Location

`tools/text/parse_html.py` — follows existing pattern (`tools/text/chunk.py`, `tools/text/embed.py`).

### 3.3 Interface

```python
def parse_html(html: str, base_url: str | None = None) -> ParseHtmlResult:
    """Extract article content from an HTML string."""
```

### 3.4 Schema

```python
# core/schemas.py
class ParseHtmlResult(BaseModel):
    text: str
    title: str | None = None
    author: str | None = None
    date_published: str | None = None
    word_count: int
```

### 3.5 Extraction strategy (local only)

1. Parse HTML with `beautifulsoup4`
2. Remove: `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`
3. Find article content: `<article>` → fallback `<main>` → fallback `<body>`
4. Extract paragraph text from: `<p>`, `<h1>`-`<h6>`, `<li>`, `<blockquote>`, `<pre>`
5. Extract metadata: `<title>`/`og:title`, `<meta name="author">`, `article:published_time`
6. Clean whitespace, decode HTML entities
7. Return plain text (no HTML tags in output)

### 3.6 Tiered web extraction (FUTURE WORK)

When web ingestion is implemented, `parse_html` becomes Tier 0 in a tiered stack:

| Tier | Strategy | Coverage | Dependency |
|------|----------|----------|------------|
| 0 | `parse_html` (this tool) — basic HTML parsing | ~60-70% | beautifulsoup4 |
| 1 | Readability algorithm (trafilatura/readability-lxml) | ~85% | Third-party lib |
| 2 | LLM-assisted — send truncated HTML to LLM | ~95%+ | LLM API |
| 3 | Browser rendering (Playwright) + LLM | ~99% | Playwright + LLM |

Tier selection configured in `system.yaml:extraction.web_tier`. Not implemented in V1.

---

## 4. Config changes

### 4.1 `config/system.yaml` (V1 changes)

```yaml
taxonomy:
  source_types:
    - youtube
    - audio
    - video
    - pdf
    - livre
    - texte         # NEW — raw text ingestion
    - personnel
    # FUTURE: web (after security brainstorm)

upload:
  max_audio_mb: 500
  max_pdf_mb: 100
  max_text_chars: 500000     # NEW — ~125k words
  # FUTURE: max_web_response_mb, web_timeout_seconds (with web ingestion)
```

### 4.2 `core/config.py` (V1 changes)

```python
class UploadConfig(BaseModel):
    max_audio_mb: int = 500
    max_pdf_mb: int = 100
    max_text_chars: int = 500_000
    # FUTURE: max_web_response_mb, web_timeout_seconds (with web ingestion)
```

---

## 5. API changes

### 5.1 New endpoints (V1)

```
POST /ingest/text     — { text, title, url?, source_type?, auto_generate_note? }
```

> **FUTURE:** `POST /ingest/web` — requires security brainstorm. Hook: the unified `_run_ingest` worker already supports any source_type, so adding the endpoint is trivial once the extractor exists.

### 5.2 Existing endpoints — preserved

```
POST /ingest/youtube  — unchanged (backward compatible)
POST /ingest/audio    — unchanged (backward compatible)
POST /ingest/pdf      — unchanged (backward compatible)
```

**Rationale:** No breaking API changes. The existing endpoints call the same unified `ingest()` workflow internally. New endpoints added for new types.

### 5.3 Internal refactor

All five endpoints call the same worker function:

```python
def _run_ingest(source_type, target, settings, system_db, job_id, auto_generate_note):
    update_job_status(system_db, job_id, "running")
    try:
        result = ingest(source_type, target, settings, auto_generate_note=auto_generate_note)
        update_job_done(system_db, job_id, {"source_uid": result.uid, "slug": result.slug})
    except LargeFormatError as e:
        update_job_done(system_db, job_id, {"source_uid": e.source_uid, "slug": None, "large_format": True})
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))
```

### 5.4 Request schemas

```python
# api/routers/ingest.py (existing, unchanged)
class IngestYoutubeRequest(BaseModel):
    url: str
    auto_generate_note: bool | None = None

# New (V1)
class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    url: str | None = None
    source_type: str = "texte"
    auto_generate_note: bool | None = None

# FUTURE: IngestWebRequest (after security brainstorm)
```

---

## 6. CLI changes

### 6.1 Auto-detection update

```python
def _detect_type(target: str) -> str:
    # YouTube URLs
    if any(p in target for p in ("youtube.com", "youtu.be")):
        return "youtube"
    # FUTURE: Web URLs (http/https, not YouTube) → "web"
    # if target.startswith(("http://", "https://")): return "web"
    # File-based detection
    ext = Path(target).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}:
        return "audio"
    if ext == ".txt":
        return "texte"
    raise ValueError(f"Unsupported input: '{target}'")
```

### 6.2 New text subcommand

```bash
# From file
egovault ingest text --title "My Notes" --file notes.txt

# Inline (short texts)
egovault ingest text --title "My Notes" "The actual text content here"

# From stdin
echo "content" | egovault ingest text --title "My Notes" -
```

### 6.3 Internal dispatch

```python
def _run_ingest(input_type, target, settings, auto_generate_note=None, title=None):
    from workflows.ingest import ingest
    return ingest(input_type, target, settings, title=title, auto_generate_note=auto_generate_note)
```

Single import, single function call. No more type-specific branches.

---

## 7. MCP changes

### 7.1 Existing tools — preserved

All existing MCP tools remain unchanged:
- `transcribe()`, `compress_audio()`, `fetch_subtitles()` — still available as atomic tools
- `chunk_text()`, `embed_text()` — generic, unchanged
- `create_note()`, `update_note()`, etc. — unchanged

### 7.2 New MCP tools (V1)

```python
@server.tool()
def ingest_text(text: str, title: str, url: str | None = None, source_type: str = "texte") -> dict:
    """Ingest raw text into the vault. The text is chunked, embedded, and made searchable."""
```

> **FUTURE:** `ingest_web(url, title)` — added when web extraction is implemented. Hook: MCP tool just calls `ingest("web", url, settings)`, trivial once extractor exists.

### 7.3 Docstrings — G1/G2 compliant

No library names, no algorithm details. Describe capabilities only.

---

## 8. Security

### 8.1 Text input validation (V1)

- Min length: 1 char (non-empty)
- Max length: `system.yaml:upload.max_text_chars` (default 500,000)
- `source_type` validated against `taxonomy.source_types`

### 8.2 No user content in logs (V1)

Per G10: text content is logged at DEBUG only. INFO logs say "Ingest complete" without content.

### 8.3 HTML sanitization (V1 — for `parse_html` tool)

Output of `parse_html` is **plain text only**. No HTML tags survive extraction. This prevents XSS if the text is later rendered in any surface.

### 8.4 Web security (FUTURE — requires dedicated brainstorm)

All of the following are **deferred** until web ingestion is implemented:

- **SSRF prevention:** `validate_web_url()` — resolve hostname to IP before request, reject private/reserved ranges, reject cloud metadata endpoints
- **Web fetch limits:** configurable response size, timeout, streaming download with early abort
- **DNS rebinding:** re-validate IP after redirect
- **Rate limiting:** per-domain fetch throttle
- **Redirect following:** max redirects, no scheme downgrade (https → http)

These items require a dedicated security brainstorm before any network-facing code is written.

---

## 9. Error handling

### 9.1 New error classes in `core/errors.py`

```python
class IngestError(Exception):
    """Base class for ingest failures with structured error information."""
    def __init__(self, error_code: str, user_message: str, http_status: int = 400):
        self.error_code = error_code
        self.user_message = user_message
        self.http_status = http_status
        super().__init__(user_message)
```

### 9.2 Web errors (FUTURE — implemented with web ingestion)

| Error | Code | HTTP | User message |
|-------|------|------|-------------|
| `InvalidUrlError` | `invalid_url` | 400 | "The URL is invalid or uses an unsupported format." |
| `UrlUnreachableError` | `url_unreachable` | 502 | "Could not reach the URL. Check your connection and the URL." |
| `UrlTimeoutError` | `url_timeout` | 504 | "The page took too long to respond." |
| `PaywallDetectedError` | `paywall_detected` | 422 | "This page appears to require authentication." |
| `ContentExtractionError` | `extraction_failed` | 422 | "No article content found on this page." |
| `ContentTooLargeError` | `content_too_large` | 413 | "Content exceeds the configured size limit." |
| `DuplicateSourceError` | `duplicate_source` | 409 | "This URL has already been ingested." |

### 9.3 Text errors (V1)

| Error | Code | HTTP | User message |
|-------|------|------|-------------|
| `EmptyContentError` | `empty_content` | 400 | "The provided text is empty." |
| `ContentTooShortError` | `content_too_short` | 400 | "The provided text is too short to produce meaningful results." |
| `ContentTooLargeError` | `content_too_large` | 413 | "The provided text exceeds the configured size limit." |

### 9.4 General errors (all pipelines)

| Error | Code | HTTP | User message |
|-------|------|------|-------------|
| `EmbeddingServiceError` | `embedding_unavailable` | 503 | "The embedding service is not available." |
| `ChunkingError` | `chunking_failed` | 500 | "Content processing failed during text segmentation." |

### 9.5 API error handler

```python
@app.exception_handler(IngestError)
async def ingest_error_handler(request, exc: IngestError):
    return JSONResponse(status_code=exc.http_status, content={"error": exc.error_code, "message": exc.user_message})
```

### 9.6 Retrofit existing workflows

The existing error handling in YouTube/audio/PDF extractors should wrap known failures in `IngestError` subclasses:
- YouTube bad URL → `InvalidUrlError`
- Audio file not found → keep as `FileNotFoundError` (not an ingest error)
- PDF empty extraction → `EmptyContentError`
- Embedding failure → `EmbeddingServiceError`

---

## 10. File map — COMPLETE impact analysis

### 10.1 New files (V1)

| File | Purpose |
|------|---------|
| `workflows/ingest.py` | Unified ingest workflow + extractor registry |
| `tools/text/parse_html.py` | Local HTML parser (no network) — Tier 0 for future web |
| `tests/workflows/test_ingest.py` | Tests for unified workflow |
| `tests/tools/text/test_parse_html.py` | Tests for parse_html tool |

### 10.2 Modified files

| File | Change | Risk |
|------|--------|------|
| `core/errors.py` | Add `IngestError` hierarchy | Low |
| `core/schemas.py` | Add `ExtractWebResult` | Low |
| `core/config.py` | Add fields to `UploadConfig` | Low |
| `config/system.yaml` | Add `texte` to taxonomy, upload limits | Low |
| `api/routers/ingest.py` | Add `/ingest/text`, refactor workers to use unified `ingest()` | Medium |
| `api/main.py` | Add `IngestError` exception handler | Low |
| `cli/commands/ingest.py` | Update `_detect_type()`, `_run_ingest()`, add text subcommand | Medium |
| `mcp/server.py` | Add `ingest_web()` and `ingest_text()` tools | Low |
| `tests/conftest.py` | Add `texte` to test taxonomy | Low |
| `tests/api/conftest.py` | Add `texte`, `web` to test taxonomy | Low |

### 10.3 Deprecated files (keep but mark as wrappers)

| File | Change |
|------|--------|
| `workflows/ingest_youtube.py` | Becomes thin wrapper: calls `ingest("youtube", url, settings)` |
| `workflows/ingest_audio.py` | Becomes thin wrapper: calls `ingest("audio", file_path, settings)` |
| `workflows/ingest_pdf.py` | Becomes thin wrapper: calls `ingest("pdf", file_path, settings)` |

**Rationale:** Keep the old files as one-line wrappers for backward compatibility. Existing imports (`from workflows.ingest_youtube import ingest_youtube`) continue to work. Tests continue to pass. The wrappers are trivial and can be removed later.

### 10.4 Test files — adaptation strategy

| File | Change |
|------|--------|
| `tests/workflows/test_ingest_youtube.py` | Patch `workflows.ingest._extract_youtube` instead of multiple tools |
| `tests/workflows/test_ingest_audio.py` | Patch `workflows.ingest._extract_audio` instead of multiple tools |
| `tests/workflows/test_ingest_pdf.py` | Patch `workflows.ingest._extract_pdf` instead of multiple tools |
| `tests/workflows/test_ingest.py` | **New** — test the unified pipeline with mocked extractors |
| `tests/api/test_ingest_text.py` | **New** — API endpoint tests |
| `tests/tools/text/test_parse_html.py` | **New** — local HTML parser tests |

---

## 11. Database changes

**None.** The DB schema is already source-type agnostic. `source_type` is a free text field validated against taxonomy. No migration needed.

---

## 12. Migration strategy

### 12.1 Incremental approach (recommended)

1. **Phase 1:** Create `workflows/ingest.py` with the unified pipeline. Extract the common code from the three existing workflows. Keep old workflow files as wrappers.
2. **Phase 2:** Add `extract_web` tool and web ingestion support.
3. **Phase 3:** Add text ingestion support (simplest — no extraction tool needed).
4. **Phase 4:** Update CLI, API, MCP to use unified workflow.
5. **Phase 5:** Update tests. Add new tests for web and text.
6. **Phase 6:** Security review.

### 12.2 Backward compatibility

- Old workflow functions still exist (as wrappers) → no import breakage
- Old API endpoints still exist → no client breakage
- Old MCP tools still exist → no MCP client breakage
- DB schema unchanged → no data migration

### 12.3 Rollback

If something goes wrong, the wrapper pattern means we can revert `workflows/ingest.py` and the old files still have the original logic (in git history). Low risk.

---

## 13. Documentation updates

| Document | Change |
|----------|--------|
| `docs/architecture/ARCHITECTURE.md` | Update section 2.2 (workflows), add unified ingest description |
| `CLAUDE.md` | Update Structure section, mark ingest_web/text as implemented |
| `.meta/specs/2026-03-31-extraction-provider-design.md` | Mark as superseded |
| `.meta/specs/2026-03-31-ingest-text-web-design.md` | Mark as superseded |

---

## 14. Open questions

1. **YouTube dispatch:** Should `ingest("youtube", url)` try subtitles first and fall back to transcription automatically? Current `fetch_subtitles` already does this — the workflow doesn't need to decide.

2. **Text source_type:** Default `"texte"` vs `"personnel"`? Recommendation: `"texte"` for any raw text input, `"personnel"` remains for reflexion-type notes without external source.

3. **Duplicate detection for web:** Check if URL already exists in sources before fetching. Simple `SELECT` on `sources.url`. Not needed for other types (files can be re-ingested intentionally).

4. **Future extractors location:** Should extractors live in `workflows/ingest.py` as private functions, or in separate files under `tools/text/`? Recommendation: private functions in the workflow for now (G5 — no premature abstraction). Extract to separate files only when they grow complex enough to warrant it.

---

## 15. Image handling — 3-tier approach (DEFERRED — not in V1)

Sources like PDFs and web pages may contain images. Image handling is tiered:

### Tier 0 — Skip + notify (default, zero config)

- Images are **skipped entirely** during text extraction
- A warning is logged: `"Image {n} not processed — image extraction not configured"`
- The transcript/extracted text contains **no trace** of the image
- This is the baseline for v1 — no image-related code runs at all
- **Dependencies:** None

### Tier 1 — Extract + store + placeholder (optional, requires extraction library)

- Images are **extracted** from the source (PDF pages, web `<img>` tags)
- Stored in `egovault-user/data/media/` as source assets
- Tracked in a `source_assets` DB table: `(asset_uid, source_uid, asset_type, path, position)`
- The transcript includes **placeholder markers**: `[image-1: not described]`, `[image-2: not described]`
- These placeholders flow through chunking normally
- Enables: "show me image 1 from source X" (asset lookup by source_uid + position)
- **Dependencies:** Image extraction capability (Pillow or equivalent)

### Tier 2 — Extract + describe + dedicated chunks (requires LLM vision API)

- Images are **extracted and stored** (same as Tier 1)
- Each image is **sent to a vision-capable LLM** for description
- Each image description becomes its **own chunk** with its own embedding
- Chunk metadata includes `asset_uid` so the image can be retrieved alongside the description
- The transcript includes the description inline: `[image-1: {description}]`
- Semantic search can now match on image descriptions → retrieves both description + image
- **Dependencies:** Vision-capable LLM endpoint (configured in system.yaml)

### Tier selection

Configured in `system.yaml`:

```yaml
extraction:
  image_handling: 0    # 0 = skip, 1 = extract+store, 2 = extract+describe
```

Default: `0`. The tier is checked at extraction time. Extractors that don't support images (e.g., `_extract_text`) ignore this setting.

### `source_assets` table (Tier 1+)

```sql
CREATE TABLE IF NOT EXISTS source_assets (
    uid          TEXT PRIMARY KEY,
    source_uid   TEXT NOT NULL REFERENCES sources(uid),
    asset_type   TEXT NOT NULL,   -- 'image', 'table', etc.
    path         TEXT NOT NULL,   -- relative to media/
    position     INTEGER NOT NULL, -- order in source
    description  TEXT,             -- NULL at Tier 1, filled at Tier 2
    chunk_uid    TEXT REFERENCES chunks(uid),  -- linked chunk at Tier 2
    date_created TEXT NOT NULL
);
```

### Implementation note

**For v1 (this spec), only Tier 0 is implemented.** Tiers 1 and 2 are fully designed here so the data model and placeholder conventions are established. The `source_assets` table is created at init_db time (empty) to avoid future migration.

---

## 16. Crash recovery (DEFERRED — not in V1)

### Problem

If the ingest pipeline crashes mid-way (after source creation but before completion), the source is left in an inconsistent state: partial chunks, partial embeddings, wrong status.

### V1 strategy — Reset and restart

The simplest reliable approach: detect partial state and wipe it clean.

```python
def recover_source(source_uid: str, settings: Settings) -> None:
    """Reset a partially-ingested source to its initial state."""
    # 1. Delete all chunks for this source
    # 2. Delete all chunk embeddings for this source
    # 3. Delete transcript (set to NULL)
    # 4. Reset source status to 'raw'
    # 5. Log the recovery action
```

### When to trigger

- **Manual:** CLI command `egovault source recover <uid>` or API endpoint
- **Automatic:** On re-ingest of a source that has status `processing` (stuck)
- **Startup check:** Optional — detect sources with status `processing` older than N minutes, log a warning

### Source status lifecycle

```
raw → processing → [rag_ready | processed | error]
         ↑                                    |
         └──────── recover (reset) ───────────┘
```

### What "recover" deletes

| Data | Action |
|------|--------|
| Chunks (DB rows) | DELETE WHERE source_uid = ? |
| Chunk embeddings (vec table) | DELETE WHERE chunk_uid IN (source chunks) |
| Note embeddings | NOT touched (notes are independent) |
| Generated notes | NOT touched (user may have edited) |
| Source record | Status reset to `raw`, transcript set to NULL |
| Media files | NOT touched (original file preserved) |

### Implementation note

Recovery is a safety net, not a primary flow. The pipeline should be designed to be idempotent: re-running ingest on a `raw` source produces the same result regardless of prior partial state.

---

## 17. Future work — documented intentions

Each item below is **intentionally deferred** but architecturally accounted for. The hooks needed in V1 are noted.

| Item | Complexity | V1 Hook | Description |
|------|-----------|---------|-------------|
| **Web ingestion** (`ingest_web`) | L | Extractor registry entry (commented out), API/CLI/MCP hooks documented | Fetch URL → parse HTML → document pipeline. Requires dedicated security brainstorm (SSRF, DNS rebinding, rate limiting). |
| **Web extraction tiers** (1-3) | M-XL | `parse_html` tool = Tier 0 | Tier 1: readability lib. Tier 2: LLM-assisted. Tier 3: browser rendering. Config: `extraction.web_tier`. |
| **Crash recovery with checkpoints** | L | Source status lifecycle (`raw → processing → done/error`) | Resume from last checkpoint instead of restarting. Requires checkpoint storage in `.system.db` and idempotent pipeline steps. |
| **Image handling Tiers 1-2** | M-L | `source_assets` table created empty at init_db, image_handling config key | Tier 1: extract+store images with placeholders. Tier 2: LLM describe + dedicated chunks. |
| **DOCX/EPUB/PPTX extractors** | S each | Extractor registry — add function + register | Trivial with unified architecture. One function + one registry entry per format. |
| **`ingest_image`** (OCR) | M | Extractor registry | Requires Tier 2 extraction provider (LLM vision or dedicated OCR). |
| **Batch ingestion / crawling** | L | `ingest()` is single-source — batch = loop with error isolation | `ingest_playlist`, `ingest_sitemap`, etc. Partial failure handling needed. |
| **Extraction provider abstraction** | M | Tier config pattern established | Factory pattern for swapping extraction backends (builtin → markitdown → chandra). |
| **Structured data family** (Family D) | M | N-family architecture, extractor registry | JSON, CSV, DB exports → parse → transform → chunk → embed. |
| **Interactive family** (Family E) | M | N-family architecture, extractor registry | Chat exports, threads → parse → chunk → embed. |
