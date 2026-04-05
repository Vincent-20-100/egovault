# Brainstorm: Web Ingestion

**Date:** 2026-04-05
**Status:** Brainstorm complete — ready for spec
**Context:** Web ingestion was deferred from unified ingest V1 pending security brainstorm.

---

## Decisions

### A — Fetch security model
**Decision:** Standard SSRF defense — sufficient for V1 (local-only tool).
- Hostname validation (reject private IPs, reserved ranges, cloud metadata endpoints)
- Post-redirect IP re-validation (DNS rebinding protection)
- Implementation: `core/security.py` (alongside `validate_youtube_url`, `validate_file_path`)

### B — Extraction tiers
**Decision:** Configurable in `system.yaml`.
- Tier 0: `parse_html` (BeautifulSoup4, builtin, ~60-70% coverage) — already implemented
- Tier 1: trafilatura or markitdown (~85% coverage) — optional dependency
- User picks tier in config. Default: Tier 0 (zero new deps).
- Config key: `web.extraction_tier: 0` (or `1`)

### C — Dynamic content (JS-rendered pages)
**Decision:** Explicitly deferred. Not in V1.
- Playwright/browser rendering = separate future scope
- Accept that SPAs and JS-heavy pages won't extract well with Tier 0/1

### D — Scope limits
**Decision:** Single URL only in V1.
- One page per ingestion call
- Text extraction only, no images
- Batch ingestion / sitemap crawling = separate future scope
- Image extraction = separate future scope (when `source_assets` table exists)

### E — Rate limiting
**Decision:** Global max frequency across all web fetches.
- Simple approach: minimum interval between any two web fetches (e.g., 2 seconds)
- Config key: `web.min_fetch_interval_seconds: 2`
- No per-domain logic in V1

### F — Tool location
**Decision:** New package `tools/web/`.
- `tools/web/fetch_web.py` — fetch URL + call parse_html → return text + metadata
- Same level as `media/`, `text/`, `vault/`, `export/`
- Rationale: web is its own domain. Future image extraction would also live here.
- SSRF validation in `core/security.py` (not in the tool itself — G4 pattern)

---

## Architecture summary

```
core/security.py          ← validate_web_url() — SSRF checks, private IP rejection
tools/web/fetch_web.py    ← fetch_web(url, ctx) → FetchWebResult(text, metadata)
tools/text/parse_html.py  ← parse_html() — already exists, called by fetch_web
workflows/ingest.py       ← add "web": _extract_web to registry
config/system.yaml        ← web.extraction_tier, web.min_fetch_interval_seconds,
                             web.max_response_mb, web.timeout_seconds
```

**Surfaces (thin routing):**
- API: `POST /ingest/web` — `IngestWebRequest(url, auto_generate_note?)`
- CLI: auto-detect `http://` / `https://` URLs → type `"web"`
- MCP: `ingest_web(url, auto_generate_note?)` tool

**Flow:**
```
URL → validate_web_url() [SSRF] → fetch_web() [HTTP GET + size/timeout limits]
    → parse_html() [extract text] → ingest() pipeline [chunk → embed → store]
```

---

## Security checklist (V1)

- [ ] Reject private/reserved IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, ::1, fc00::, etc.)
- [ ] Reject cloud metadata endpoints (169.254.169.254, metadata.google.internal)
- [ ] Re-validate IP after redirects (DNS rebinding defense)
- [ ] Max redirects (default: 5)
- [ ] No scheme downgrade (HTTPS → HTTP rejected)
- [ ] Response size limit (configurable, default: 10 MB)
- [ ] Timeout (configurable, default: 30 seconds)
- [ ] Content-Type check (accept text/html, reject binary)
- [ ] Global fetch rate limit (configurable interval)

---

## Config additions (system.yaml)

```yaml
web:
  extraction_tier: 0          # 0 = builtin (bs4), 1 = trafilatura/markitdown
  max_response_mb: 10         # max HTTP response size
  timeout_seconds: 30         # fetch timeout
  min_fetch_interval_seconds: 2  # global rate limit between fetches
  max_redirects: 5            # max redirect chain length
```

---

## What is NOT in this scope

- Batch/multi-page ingestion (sitemap, crawling)
- Image extraction from web pages
- JavaScript rendering (Playwright/Tier 3)
- Per-domain rate limiting
- Authentication/cookies for protected pages
- RSS/Atom feed parsing
