# Design spec: `ingest_text` + `ingest_web`

**Date:** 2026-03-31
**Status:** ~~SPEC READY~~ **OBSOLETE — superseded by `2026-03-31-unified-ingest-architecture.md`**
**Prerequisites:** None (all patterns exist)
**Depends on:** Block A complete (done), existing ingest patterns

> **⚠ This spec has been superseded.** See `2026-03-31-unified-ingest-architecture.md` for the definitive design.

---

## 1. Design decisions

### 1.1 Extraction provider: full abstraction vs simple tool?

**Decision: simple tool, no abstraction.**

Rationale:
- G5 (no over-engineering) is the decisive guardrail. A full `ExtractionProvider` interface with three tiers, fallback chains, and pluggable backends is premature. Today we need exactly one thing: extract article text from an HTML page.
- `ingest_text` needs no extraction at all — text is provided directly.
- `ingest_web` needs HTML-to-text extraction. This is a single atomic operation: URL in, text out. It fits naturally as a tool in `tools/text/extract_web.py`.
- The existing `ingest_pdf` already does extraction inline (`_extract_pdf_text()`). Adding a parallel `extract_web` tool is consistent.
- When markitdown (Tier 1) or chandra (Tier 2) are adopted later, they can either replace the builtin implementation inside `extract_web.py` or justify a proper `extraction_provider.py` at that point. The tool's public interface (`ExtractWebResult`) won't change.
- The audit doc (section 11) correctly identifies the tiered architecture as future work. Building the abstraction now would create dead code and unused interfaces.

**What we build now:**
- `tools/text/extract_web.py` — atomic tool: URL in, extracted text + metadata out
- `workflows/ingest_text.py` — simplest pipeline: text in, chunk, embed
- `workflows/ingest_web.py` — URL in, extract, chunk, embed

### 1.2 `source_type` taxonomy additions

The taxonomy in `system.yaml` already has `web` and `personnel`. Both are documented as future/personal types. We use:
- `web` for `ingest_web` sources
- `texte` for `ingest_text` sources (new addition — French, consistent with `livre`)

Why `texte` and not `personnel`? `personnel` means "personal reflection" — it implies no external source. `texte` is for any raw text regardless of origin (copy-paste from an article, a transcript someone shared, meeting notes, etc.). `personnel` remains available for `reflexion`-type notes that have no source at all.

### 1.3 Status transitions

Both pipelines follow the same status model as existing workflows:

```
ingest_text: raw → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
ingest_web:  raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
```

`ingest_text` skips `transcribing` because there is nothing to extract — text is already provided. The source goes directly to `text_ready` after insertion.

`ingest_web` uses `transcribing` for the fetch+extract step (same semantic as existing workflows: "converting raw input to text").

---

## 2. `ingest_text` spec

### 2.1 Purpose

Ingest raw text directly into the vault. The simplest possible pipeline: the user provides text and a title, and EgoVault chunks it, embeds it, and makes it searchable. No file, no URL fetch, no extraction.

Use cases:
- Copy-paste from anywhere (article, email, chat, document)
- Raw transcripts from external tools
- Personal notes or ideas the user wants searchable
- Content from sources EgoVault cannot fetch directly

### 2.2 Workflow: `workflows/ingest_text.py`

```python
def ingest_text(
    text: str,
    title: str,
    settings: Settings,
    url: str | None = None,
    source_type: str = "texte",
    auto_generate_note: bool | None = None,
) -> Source:
```

Pipeline steps:
1. **Validate inputs** — title required (non-empty), text non-empty, source_type valid
2. **Create source record** — status `raw`, slug from title
3. **Store transcript** — update source transcript with the provided text, status -> `text_ready`
4. **Chunk + embed** — identical to existing workflows, status -> `embedding` -> `rag_ready`
5. **Optional note generation** — same LLM path as all other workflows

No `transcribing` step — text goes directly to `text_ready`.

### 2.3 Schemas

No new Pydantic models needed for the workflow itself — it uses `Source`, `ChunkResult`, and the existing embed pipeline.

**API model** (in `api/models.py`):
```python
class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500_000)  # ~125k words max
    title: str = Field(min_length=1, max_length=200)
    url: str | None = None
    source_type: str = "texte"
    auto_generate_note: bool | None = None
```

### 2.4 Layers

**CLI** (`cli/commands/ingest.py`):
- Extend `_detect_type()` to recognize `--text` flag or stdin pipe
- New subcommand approach: `egovault ingest text --title "My Notes" --file notes.txt` or `egovault ingest text --title "My Notes" < stdin`
- Alternative: `egovault ingest text --title "My Notes" "the actual text here"` for short texts
- Best approach: `target` can be a `.txt` file path, and we add `--text` option for inline. Detection: if file has `.txt` extension, read its content and use `ingest_text`

**API** (`api/routers/ingest.py`):
- `POST /ingest/text` — accepts `IngestTextRequest` JSON body
- Async job pattern (same as youtube/audio/pdf)

**MCP** (`mcp/server.py`):
- `ingest_text(text, title, url=None, source_type="texte")` tool
- Docstring: "Ingest raw text into the vault. Provide text content and a title. The text is chunked, embedded, and made searchable."

---

## 3. `ingest_web` spec

### 3.1 Purpose

Ingest a web article by URL. EgoVault fetches the page, extracts the article content (stripping navigation, ads, scripts), and runs the standard chunk+embed pipeline.

### 3.2 Tool: `tools/text/extract_web.py`

```python
def extract_web(url: str, settings: Settings) -> ExtractWebResult:
```

**Behavior:**
1. Fetch HTML from URL with a reasonable timeout and user-agent
2. Parse HTML and extract article content, title, author, publication date
3. Strip navigation, ads, scripts, styles, footers, sidebars
4. Return clean text suitable for chunking

**Extraction strategy (Tier 0 — builtin):**
- `requests.get()` with configurable timeout and max response size
- `beautifulsoup4` for HTML parsing
- Article extraction heuristics (adapted from readability algorithm):
  - Remove `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>` tags
  - Look for `<article>` tag first; fall back to `<main>`; fall back to `<body>`
  - Extract `<p>`, `<h1>`-`<h6>`, `<li>`, `<blockquote>`, `<pre>`, `<code>` text
  - Metadata: `<title>` or `og:title`, `<meta name="author">` or `article:author`, `<meta name="date">` or `article:published_time`
- Clean up whitespace, decode HTML entities

**Error handling:**
- HTTP errors (4xx/5xx) -> raise with status code context (no URL in error message per G10)
- Non-HTML content-type -> reject with clear error
- Timeout -> raise with generic timeout message
- Empty extraction (paywall, login-wall) -> raise with "no article content found" message
- Response too large (exceeds configured max) -> reject

**Result schema** (in `core/schemas.py`):
```python
class ExtractWebResult(BaseModel):
    text: str
    title: str | None = None
    author: str | None = None
    date_published: str | None = None
    word_count: int
```

### 3.3 Workflow: `workflows/ingest_web.py`

```python
def ingest_web(
    url: str,
    settings: Settings,
    title: str | None = None,
    auto_generate_note: bool | None = None,
) -> Source:
```

Pipeline steps:
1. **Validate URL** — must be HTTP(S), not a YouTube URL (use `ingest_youtube` for that)
2. **Create source record** — status `raw`, slug from title or extracted title, `source_type="web"`
3. **Fetch + extract** — call `extract_web(url, settings)`, status `transcribing` -> `text_ready`
4. **Store transcript** — save extracted text to source
5. **Store metadata** — title (from extraction if not provided), author, date in source fields
6. **Chunk + embed** — identical to existing workflows, status -> `embedding` -> `rag_ready`
7. **Optional note generation** — same LLM path

### 3.4 URL validation: `core/security.py`

New function:
```python
def validate_web_url(url: str) -> str | None:
    """
    Validate a web URL for article ingestion.
    Returns canonicalized URL if valid, None otherwise.
    Rejects: non-HTTP(S), YouTube URLs (wrong pipeline), local/private IPs.
    """
```

Validation rules:
- Must start with `http://` or `https://`
- Must not be a YouTube URL (redirect to `ingest_youtube`)
- Must not target private/internal IPs (SSRF protection): reject `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1`, `0.0.0.0`
- Must not target `localhost` or `*.local`
- Max URL length: 2048 characters

### 3.5 Layers

**CLI** (`cli/commands/ingest.py`):
- Extend `_detect_type()`: if target starts with `http://` or `https://` and is NOT YouTube, detect as `web`
- `_run_ingest()` dispatches to `ingest_web`

**API** (`api/routers/ingest.py`):
- `POST /ingest/web` — accepts `IngestWebRequest` JSON body
- Same async job pattern

**API model** (in `api/models.py`):
```python
class IngestWebRequest(BaseModel):
    url: str
    title: str | None = None
    auto_generate_note: bool | None = None
```

**MCP** (`mcp/server.py`):
- `ingest_web(url, title=None)` tool
- Docstring: "Ingest a web article by URL. Fetches the page, extracts article content, and indexes it for search."

---

## 4. Config changes

### 4.1 `config/system.yaml`

```yaml
taxonomy:
  source_types:
    - youtube
    - audio
    - video
    - pdf
    - livre
    - web
    - texte         # NEW — raw text ingestion (copy-paste, external transcripts)
    - personnel

upload:
  max_audio_mb: 500
  max_pdf_mb: 100
  max_text_chars: 500000    # NEW — max text length for ingest_text (~125k words)
  max_web_response_mb: 10   # NEW — max HTML response size for web fetch
  web_timeout_seconds: 30   # NEW — HTTP request timeout for web fetch
```

### 4.2 `core/config.py`

Update `UploadConfig`:
```python
class UploadConfig(BaseModel):
    max_audio_mb: int = 500
    max_pdf_mb: int = 100
    max_text_chars: int = 500_000      # NEW
    max_web_response_mb: int = 10      # NEW
    web_timeout_seconds: int = 30      # NEW
```

### 4.3 No changes to `user.yaml` or `install.yaml`

No user-configurable or machine-specific settings needed for these features.

---

## 5. Schema changes (`core/schemas.py`)

### 5.1 New model: `ExtractWebResult`

```python
class ExtractWebResult(BaseModel):
    """Result of extracting article content from a web page."""
    text: str
    title: str | None = None
    author: str | None = None
    date_published: str | None = None
    word_count: int
```

That is the only new schema. Everything else reuses existing models (`Source`, `ChunkResult`, etc.).

---

## 6. Security considerations

### 6.1 URL sanitization (SSRF prevention)

`validate_web_url()` in `core/security.py` MUST reject:
- Private IP ranges: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- IPv6 loopback: `::1`
- Special hostnames: `localhost`, `*.local`, `metadata.google.internal`, `169.254.169.254` (cloud metadata)
- Non-HTTP(S) schemes: `file://`, `ftp://`, `data:`, `javascript:`
- Extremely long URLs (>2048 chars)

Implementation: resolve hostname to IP BEFORE making the request, then check against blocked ranges. This prevents DNS rebinding where `evil.com` resolves to `127.0.0.1`.

### 6.2 HTML sanitization

The extracted text must NOT contain:
- JavaScript (no `<script>` content should survive extraction)
- HTML tags (output is plain text, not HTML)
- Data URIs or embedded content

The `extract_web` tool returns plain text only. Tags are stripped during extraction, not preserved.

### 6.3 Input validation for `ingest_text`

- `text` max length: controlled by `system.yaml:upload.max_text_chars` (default 500,000 chars ~125k words)
- `title` max length: 200 chars (matches `NoteContentInput.title`)
- `source_type` must be in `taxonomy.source_types`
- `url` (optional) is stored as-is (metadata only, not fetched)

### 6.4 Response size limits for `ingest_web`

- Max HTTP response: `system.yaml:upload.max_web_response_mb` (default 10 MB)
- Streaming download with size check — abort if response exceeds limit before downloading fully
- Timeout: `system.yaml:upload.web_timeout_seconds` (default 30s)

### 6.5 Error messages (G1, G6, G10)

All error messages use generic descriptions:
- "Web page could not be fetched" (not "requests.get() returned 403")
- "No article content found on the page" (not "BeautifulSoup found no <article> tag")
- "Text exceeds maximum allowed length" (not "text is 600,000 chars, max is 500,000")
- "URL is not allowed" (not "SSRF: private IP detected")

### 6.6 No logging of content or URLs at INFO+

Per G10, URLs, text content, and page HTML are logged at DEBUG only. INFO-level logs say things like "Web extraction complete" without the URL.

---

## 7. File map

### 7.1 New files

| File | Purpose |
|------|---------|
| `tools/text/extract_web.py` | Atomic tool: URL -> extracted article text + metadata |
| `workflows/ingest_text.py` | Workflow: raw text -> chunk -> embed |
| `workflows/ingest_web.py` | Workflow: URL -> extract -> chunk -> embed |
| `tests/tools/text/test_extract_web.py` | Unit tests for extract_web tool |
| `tests/workflows/test_ingest_text.py` | Unit tests for ingest_text workflow |
| `tests/workflows/test_ingest_web.py` | Unit tests for ingest_web workflow |
| `tests/api/routers/test_ingest_text_web.py` | API endpoint tests for both new routes |

### 7.2 Modified files

| File | Change |
|------|--------|
| `config/system.yaml` | Add `texte` to `taxonomy.source_types`; add `max_text_chars`, `max_web_response_mb`, `web_timeout_seconds` to `upload` |
| `core/config.py` | Add three new fields to `UploadConfig` |
| `core/schemas.py` | Add `ExtractWebResult` model |
| `core/security.py` | Add `validate_web_url()` function |
| `cli/commands/ingest.py` | Extend `_detect_type()` for web URLs and .txt files; extend `_run_ingest()` with two new dispatch branches |
| `api/models.py` | Add `IngestTextRequest`, `IngestWebRequest` models |
| `api/routers/ingest.py` | Add `POST /ingest/text` and `POST /ingest/web` endpoints |
| `mcp/server.py` | Add `ingest_text()` and `ingest_web()` MCP tools |
| `tests/conftest.py` | Add `texte` and `web` to test taxonomy `source_types` |
| `tests/core/test_security.py` | Add tests for `validate_web_url()` |

---

## 8. Test plan

### 8.1 `tests/tools/text/test_extract_web.py`

Tests for the `extract_web` tool (HTML parsing logic). All HTTP calls mocked.

| Test | What it verifies |
|------|-----------------|
| `test_extract_web_article_tag` | Extracts text from `<article>` element |
| `test_extract_web_fallback_to_main` | Falls back to `<main>` when no `<article>` |
| `test_extract_web_fallback_to_body` | Falls back to `<body>` as last resort |
| `test_extract_web_strips_scripts_and_styles` | No `<script>`/`<style>` content in output |
| `test_extract_web_strips_nav_footer` | No `<nav>`/`<footer>`/`<aside>` content |
| `test_extract_web_extracts_title` | Title from `<title>` or `og:title` |
| `test_extract_web_extracts_author` | Author from `<meta name="author">` |
| `test_extract_web_extracts_date` | Date from `article:published_time` |
| `test_extract_web_handles_encoding` | Correctly handles UTF-8 and Latin-1 pages |
| `test_extract_web_rejects_non_html` | Raises error for non-HTML content-type |
| `test_extract_web_empty_article` | Raises error when no article content found |
| `test_extract_web_http_error` | Raises error on 4xx/5xx responses |
| `test_extract_web_timeout` | Raises error on request timeout |
| `test_extract_web_response_too_large` | Raises error when response exceeds size limit |

### 8.2 `tests/workflows/test_ingest_text.py`

Tests for the `ingest_text` workflow. extract_web, chunk, embed all mocked.

| Test | What it verifies |
|------|-----------------|
| `test_ingest_text_returns_rag_ready_source` | Happy path — source created at `rag_ready` |
| `test_ingest_text_stores_transcript` | Provided text stored as source transcript |
| `test_ingest_text_source_type_default` | Default source_type is `texte` |
| `test_ingest_text_source_type_override` | source_type can be overridden |
| `test_ingest_text_url_stored` | Optional URL stored on source record |
| `test_ingest_text_chunks_stored` | Chunks created and stored in DB |
| `test_ingest_text_raises_large_format_error` | LargeFormatError for text exceeding threshold |
| `test_ingest_text_auto_generate_true` | Note generation triggered when enabled |
| `test_ingest_text_auto_generate_false` | Note generation skipped when disabled |

### 8.3 `tests/workflows/test_ingest_web.py`

Tests for the `ingest_web` workflow. extract_web, chunk, embed all mocked.

| Test | What it verifies |
|------|-----------------|
| `test_ingest_web_returns_rag_ready_source` | Happy path — source created at `rag_ready` |
| `test_ingest_web_stores_transcript` | Extracted text stored as source transcript |
| `test_ingest_web_stores_extracted_title` | Title from extraction used if not provided |
| `test_ingest_web_explicit_title_overrides` | User-provided title overrides extraction |
| `test_ingest_web_stores_url` | URL stored on source record |
| `test_ingest_web_stores_metadata` | Author and date stored in raw_metadata |
| `test_ingest_web_source_type_is_web` | source_type is always `web` |
| `test_ingest_web_chunks_stored` | Chunks created and stored in DB |
| `test_ingest_web_raises_large_format_error` | LargeFormatError for large articles |
| `test_ingest_web_auto_generate_true` | Note generation triggered when enabled |
| `test_ingest_web_extraction_error_propagates` | Extraction errors propagate cleanly |

### 8.4 `tests/api/routers/test_ingest_text_web.py`

API endpoint tests using FastAPI TestClient.

| Test | What it verifies |
|------|-----------------|
| `test_ingest_text_returns_202` | POST /ingest/text returns job_id |
| `test_ingest_text_missing_title_400` | Rejects request without title |
| `test_ingest_text_empty_text_400` | Rejects request with empty text |
| `test_ingest_text_too_large_413` | Rejects text exceeding max_text_chars |
| `test_ingest_web_returns_202` | POST /ingest/web returns job_id |
| `test_ingest_web_invalid_url_400` | Rejects invalid URLs |
| `test_ingest_web_youtube_url_400` | Rejects YouTube URLs with helpful message |

### 8.5 `tests/core/test_security.py`

Tests for `validate_web_url()`.

| Test | What it verifies |
|------|-----------------|
| `test_valid_https_url` | Accepts normal HTTPS URLs |
| `test_valid_http_url` | Accepts HTTP URLs |
| `test_rejects_youtube_url` | Rejects YouTube URLs |
| `test_rejects_private_ip` | Rejects 127.0.0.1, 10.x, 172.16.x, 192.168.x |
| `test_rejects_localhost` | Rejects localhost |
| `test_rejects_non_http` | Rejects file://, ftp://, data: |
| `test_rejects_long_url` | Rejects URLs > 2048 chars |
| `test_rejects_metadata_endpoint` | Rejects cloud metadata IPs (169.254.169.254) |

---

## 9. Implementation order

Recommended execution order (minimizes blocked work):

1. **Config + schemas** — `system.yaml`, `config.py`, `schemas.py` changes
2. **Security** — `validate_web_url()` in `core/security.py`
3. **`ingest_text` workflow** — simplest, no new tool needed
4. **`extract_web` tool** — the only genuinely new tool
5. **`ingest_web` workflow** — depends on extract_web
6. **CLI** — extend detection and dispatch
7. **API** — new endpoints
8. **MCP** — new tool wrappers
9. **Tests** — can be written alongside each step

Steps 1-3 are independently testable. Steps 4-5 depend on 1-2. Steps 6-8 depend on 3+5.

---

## 10. Dependencies

### 10.1 New Python packages

- `beautifulsoup4` — HTML parsing (already listed in audit as Tier 0 builtin)
- `requests` — HTTP fetching (likely already installed as transitive dependency)

Both are lightweight, well-maintained, and have no conflicting dependencies. Add to `requirements.txt` / `pyproject.toml`.

### 10.2 No new system dependencies

No GPU, no external services, no API keys. Everything runs locally with zero configuration.

---

## 11. What this does NOT include (future work)

- **Full extraction provider abstraction** — deferred until markitdown/chandra adoption (section 11 of audit)
- **`ingest_docx` / `ingest_epub` / `ingest_pptx`** — trivial to add later with same pattern
- **JavaScript rendering** — dynamic/SPA sites not supported in Tier 0; future upgrade with playwright or similar
- **Cookie/session handling** — no login-wall bypass; graceful error on paywalled content
- **Image extraction from web pages** — text-only extraction in Tier 0
- **Readability scoring** — no quality gate on extracted content (user decides)
