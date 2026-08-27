# Unified Ingest Workflow — Implementation Plan

**Date:** 2026-04-01
**Spec:** `specs/2026-03-31-unified-ingest-architecture.md`
**Brainstorm:** `specs/2026-04-01-unified-ingest-notes.md`
**Status:** READY FOR EXECUTION

---

## Pre-flight check

Before starting, verify these assumptions still hold:

- [ ] VaultContext is fully wired (`core/context.py`, `infrastructure/context.py`)
- [ ] All 3 workflows use `ctx: VaultContext` (not `settings`)
- [ ] `system.yaml` has taxonomy.source_types (youtube, audio, video, pdf, livre, web, personnel)
- [ ] `core/errors.py` has `LargeFormatError`, `NotFoundError`, `ConflictError`
- [ ] 374+ tests pass

---

## Step 1 — IngestError hierarchy

**Files:** `core/errors.py`
**Do:**
- Add `IngestError` base class with `error_code: str`, `user_message: str`, `http_status: int = 400`
- Add V1 subclasses: `EmptyContentError`, `ContentTooLargeError`
- Migrate `LargeFormatError` to inherit from `IngestError` (keep existing fields, add error_code/http_status)
- Keep `NotFoundError` and `ConflictError` unchanged (not ingest-specific)

**Test:** `python -m pytest tests/ -x` — all existing tests must pass (LargeFormatError interface unchanged)
**Doc:** None (internal change, no doc impact)
**Commit message:** `feat: add IngestError hierarchy for structured ingest error handling`

---

## Step 2 — Config: add `texte` source type + text upload limits

**Files:** `config/system.yaml`, `core/config.py`
**Do:**
- Add `texte` to `taxonomy.source_types` in `system.yaml`
- Add `max_text_chars: 500000` to `upload` section in `system.yaml`
- Add `max_text_chars: int = 500_000` to `UploadConfig` in `core/config.py`

**Test:** `python -m pytest tests/core/ -x`
**Doc:** None (config is self-documenting)
**Commit message:** `feat: add texte source type and text upload config`

---

## Step 3 — `tools/text/parse_html.py` + schema

**Files:** `tools/text/parse_html.py` (new), `core/schemas.py`
**Do:**
- Add `ParseHtmlResult` to `core/schemas.py`: `text`, `title`, `author`, `date_published`, `word_count`
- Create `tools/text/parse_html.py` with `parse_html(html: str, base_url: str | None = None) -> ParseHtmlResult`
- Implementation: BeautifulSoup4-based. Remove script/style/nav/footer/header/aside. Find article/main/body. Extract paragraphs + metadata. Return plain text only.
- Receives no `ctx` (pure function, no infrastructure dependencies)

**Test:** `python -m pytest tests/tools/text/test_parse_html.py -x` (new test file)
**Doc:** None
**Commit message:** `feat: add parse_html tool for local HTML text extraction`

---

## Step 4 — Unified workflow: `workflows/ingest.py`

**Files:** `workflows/ingest.py` (new)
**Do:**
- Create the unified `ingest()` function with signature:
  ```python
  def ingest(source_type: str, target: str, ctx: VaultContext,
             title: str | None = None, auto_generate_note: bool | None = None) -> Source:
  ```
- Extract common pipeline from existing workflows:
  1. Create source record (uid, slug, insert)
  2. Extract text via `_EXTRACTORS` registry dispatch
  3. Store transcript, update status
  4. Token count check
  5. Chunk + embed
  6. Maybe generate note (same logic as current)
  7. LargeFormatError if over threshold
  8. Return source
- Implement private extractor functions:
  - `_extract_youtube(url, ctx)` → calls `fetch_subtitles`
  - `_extract_audio(file_path, ctx)` → calls `compress_audio` + `transcribe`
  - `_extract_pdf(file_path, ctx)` → calls pypdf
  - `_extract_text(target, ctx)` → identity (text already extracted)
  - `_extract_html(target, ctx)` → calls `parse_html`
- `_EXTRACTORS` registry: `dict[str, Callable]` mapping source_type → extractor
- Slug generation: type-specific logic (video ID for youtube, file stem for audio/pdf, title for text)
- `url` field: set for youtube, None for file-based types (or pass explicitly)

**Test:** `python -m pytest tests/workflows/test_ingest.py -x` (new test file)
**Doc:** None (doc update in step 10)
**Commit message:** `feat: unified ingest workflow with extractor registry`

---

## Step 5 — Tests for unified workflow

**Files:** `tests/workflows/test_ingest.py` (new)
**Do:**
- Test `ingest()` with mocked extractors for each source type
- Test extractor registry dispatch (known type, unknown type → ValueError)
- Test common pipeline: source creation, chunk+embed, status transitions
- Test auto_generate_note decision tree (explicit True/False/None, LLM configured or not)
- Test LargeFormatError raised when over threshold
- Test `_extract_text` identity extractor
- Test `_extract_html` calls `parse_html`
- Use `_make_ctx()` pattern from existing test files

**Test:** `python -m pytest tests/workflows/test_ingest.py -x`
**Doc:** None
**Commit message:** `test: unified ingest workflow coverage`

---

## Step 6 — Convert old workflows to thin wrappers

**Files:** `workflows/ingest_youtube.py`, `workflows/ingest_audio.py`, `workflows/ingest_pdf.py`
**Do:**
- Replace entire body with one-line delegation to `workflows.ingest.ingest()`
- Keep function signatures identical for backward compat
- Add module docstring: `"""DEPRECATED — thin wrapper. Use workflows.ingest.ingest() directly."""`
- YouTube: `return ingest("youtube", url, ctx, auto_generate_note=auto_generate_note)`
- Audio: `return ingest(source_type, file_path, ctx, title=title, auto_generate_note=auto_generate_note)`
- PDF: `return ingest(source_type, file_path, ctx, title=title, auto_generate_note=auto_generate_note)`

**Test:** `python -m pytest tests/workflows/ -x` — all existing tests must still pass through wrappers
**Doc:** None
**Commit message:** `refactor: convert old workflows to thin wrappers over unified ingest`

---

## Step 7 — API: add `/ingest/text`, unify worker functions

**Files:** `api/routers/ingest.py`, `api/models.py`
**Do:**
- Add `IngestTextRequest` to `api/models.py`: `text`, `title`, `url?`, `source_type?`, `auto_generate_note?`
- Replace `_run_youtube`, `_run_audio`, `_run_pdf` with single `_run_ingest`:
  ```python
  def _run_ingest(job_id, source_type, target, ctx, auto_generate_note=None, title=None):
      from workflows.ingest import ingest
      # ... job lifecycle (same pattern as current)
  ```
- Update existing 3 endpoints to call `_run_ingest` instead of type-specific runners
- Add `POST /ingest/text` endpoint with text size validation against `max_text_chars`
- Add `IngestError` exception handler in `api/main.py`

**Test:** `python -m pytest tests/api/ -x` — existing API tests pass + new text endpoint test
**Doc:** None
**Commit message:** `feat: add /ingest/text endpoint, unify API ingest workers`

---

## Step 8 — CLI: add text support, unify dispatch

**Files:** `cli/commands/ingest.py`
**Do:**
- Update `_detect_type()`: add `.txt` → `"texte"`, `.html`/`.htm` → `"html"`
- Simplify `_run_ingest()` to single call: `from workflows.ingest import ingest; return ingest(...)`
- Add text subcommand or extend existing command to handle `--title` for text/html input
- Keep error handling (LargeFormatError, FileNotFoundError) unchanged

**Test:** `python -m pytest tests/cli/ -x`
**Doc:** None
**Commit message:** `feat: CLI text/html ingest support, unified dispatch`

---

## Step 9 — MCP: add `ingest_text` tool

**Files:** `mcp/server.py`
**Do:**
- Add `ingest_text()` MCP tool:
  ```python
  @mcp.tool()
  def ingest_text(text: str, title: str, source_type: str = "texte") -> dict:
      """Ingest raw text into the vault. Content is chunked, embedded, and searchable."""
  ```
- Calls `ingest("texte", text, ctx, title=title)` from `workflows.ingest`
- G1/G2 compliant docstring (no library names, describe capability)

**Test:** `python -m pytest tests/mcp/ -x`
**Doc:** None
**Commit message:** `feat: add ingest_text MCP tool`

---

## Step 10 — Update API test files

**Files:** `tests/api/test_ingest.py` (or existing ingest test files), `tests/api/conftest.py`
**Do:**
- Add `texte` to test taxonomy in `conftest.py` if not already present
- Add tests for `POST /ingest/text` (happy path, empty text, too large)
- Verify existing YouTube/audio/PDF tests still pass through the unified worker
- Mock `_run_ingest` instead of type-specific `_run_youtube`, etc.

**Test:** `python -m pytest tests/api/ -x`
**Doc:** None
**Commit message:** `test: API ingest text endpoint coverage`

---

## Step 11 — Full test suite + doc updates

**Files:** `docs/architecture/ARCHITECTURE.md`, `PROJECT-STATUS.md`, `SESSION-CONTEXT.md`
**Do:**
- Run full test suite: `python -m pytest tests/ -x`
- Fix any failures
- Update ARCHITECTURE.md: workflows section to describe unified ingest
- Update PROJECT-STATUS.md: mark unified ingest as done, update roadmap
- Update SESSION-CONTEXT.md: current decisions, deferred items (crash recovery, source_assets, web ingest)
- Document thin wrappers as debt to clean up

**Test:** Full suite green
**Doc:** ARCHITECTURE.md, PROJECT-STATUS.md, SESSION-CONTEXT.md
**Commit message:** `docs: update architecture and project status for unified ingest`

---

## Dependency graph

```
Step 1 (errors) ──────────┐
Step 2 (config) ──────────┤
Step 3 (parse_html) ──────┼──→ Step 4 (unified workflow) ──→ Step 5 (tests)
                          │                                       │
                          │    Step 6 (wrappers) ←────────────────┘
                          │         │
                          └────→ Step 7 (API) ──→ Step 10 (API tests)
                                Step 8 (CLI)
                                Step 9 (MCP)
                                     │
                                     └──→ Step 11 (full suite + docs)
```

**Steps 1, 2, 3 can run in parallel** (no dependencies between them).
**Steps 7, 8, 9 can run in parallel** (independent surfaces, all depend on step 4).
**Step 6 depends on steps 4+5** (unified workflow must work before wrappers delegate to it).

---

## Risk assessment

| Risk | Mitigation |
|------|-----------|
| Existing tests break after wrapper conversion | Run tests at step 6 before touching surfaces |
| API background thread DB locks | Mock `_run_ingest` in API tests (learned from post-VaultContext cleanup) |
| `parse_html` dependency (beautifulsoup4) not installed | Add to requirements, check import in tests |
| Slug generation differs between types | Extract slug logic from each workflow carefully |

---

## Out of scope (documented in brainstorm notes)

- Crash recovery (`recover_source`)
- `source_assets` table (image handling)
- Web ingestion (requires security brainstorm for fetch layer)
- Image handling tiers 1-2
- Cleanup of thin wrappers (future session)
