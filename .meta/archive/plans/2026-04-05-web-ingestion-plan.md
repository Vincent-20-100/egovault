# Plan: Web Ingestion V1

**Date:** 2026-04-05
**Spec:** `.meta/specs/2026-04-05-web-ingestion-spec.md`
**Branch:** `claude/brainstorming-pending-ideas-5zR2H`

---

## Execution order

### Phase 1 — Core layer (no network, no surfaces)

**Step 1: Config + schemas**
- Add `WebSettings` to `core/config.py`
- Add `web` section to `config/system.yaml`
- Add `FetchWebResult` to `core/schemas.py`
- Test: import works, defaults are correct

**Step 2: URL validation**
- Add `validate_web_url(url: str) -> str` to `core/security.py`
- SSRF checks: scheme, private IP, cloud metadata, hostname resolution
- Test: `tests/core/test_security.py` — `TestValidateWebUrl` (15 tests)

### Phase 2 — Fetch tool

**Step 3: `tools/web/fetch_web.py`**
- Create `tools/web/__init__.py` (empty)
- Create `tools/web/fetch_web.py` — fetch_web(url, ctx) → FetchWebResult
- HTTP GET via httpx, streaming response, size/timeout/content-type checks
- Post-redirect IP re-validation
- Rate limit (module-level timestamp)
- Tier 0/1 extraction dispatch
- Add `httpx` to `pyproject.toml`
- Test: `tests/tools/web/test_fetch_web.py` (11 tests, all mocked)

### Phase 3 — Pipeline integration

**Step 4: Extractor + workflow**
- Add `_extract_web()` to `workflows/ingest.py`
- Register `"web": _extract_web` in `_EXTRACTORS`
- Test: `tests/workflows/test_ingest.py` — `test_ingest_web` (mock fetch_web)

### Phase 4 — Surfaces (thin routing)

**Step 5: API endpoint**
- Add `IngestWebRequest` to `api/models.py`
- Add `POST /ingest/web` to `api/routers/ingest.py`
- Test: `tests/api/routers/test_ingest.py` — 3 tests

**Step 6: CLI**
- Update `_detect_type()` in `cli/commands/ingest.py` — detect http/https URLs
- Test: verify detection (YouTube still wins over generic URL)

**Step 7: MCP**
- Add `ingest_web()` tool to `mcp/server.py`
- Test: `tests/mcp/test_server.py` — 1 test

### Phase 5 — Finalize

**Step 8: Integration test + docs**
- Run full test suite
- Update ARCHITECTURE.md taxonomy (remove "not yet implemented" from web)
- Update CLAUDE.md project structure (add tools/web/)
- Update PROJECT-STATUS.md

---

## Risk notes

- **httpx availability:** Check if already a transitive dep. If not, `pip install httpx`.
- **DNS resolution in tests:** All network calls mocked — no real DNS in tests.
- **Rate limit state:** Module-level variable — simple but not thread-safe. Acceptable for single-user.
