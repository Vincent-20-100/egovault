# Spec: Web Ingestion — Single URL, V1

**Date:** 2026-04-05
**Status:** Draft — needs validation
**Depends on:** Unified ingest (done), parse_html (done), security hardening (done)
**Brainstorm:** `.meta/specs/2026-04-05-web-ingestion-notes.md`

---

## Context

EgoVault can ingest YouTube, audio, PDF, text, and local HTML files.
Web ingestion (fetch a URL → extract article text → chunk → embed) was deferred
from unified ingest V1 pending a security brainstorm. That brainstorm is now done.

**V1 scope:** Single URL, text only, no images, no JS rendering, no batch/crawling.

---

## 1. New files

### 1.1 — `core/security.py` — `validate_web_url(url) -> str`

Add to existing file, alongside `validate_youtube_url` and `validate_file_path`.

```python
def validate_web_url(url: str) -> str:
    """
    Validate a URL for safe web fetching.
    Returns the canonical URL or raises ValueError.
    """
```

**Checks (in order):**

1. **Scheme:** Must be `http://` or `https://`. Reject `file://`, `ftp://`, `data:`, etc.
2. **Host extraction:** Parse with `urllib.parse.urlparse`. Reject if no hostname.
3. **Private IP rejection:** Resolve hostname → IP, reject if IP is in:
   - `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
   - `169.254.0.0/16` (link-local + cloud metadata: `169.254.169.254`)
   - `0.0.0.0/8`
   - IPv6: `::1`, `fc00::/7`, `fe80::/10`
4. **Cloud metadata endpoints:** Reject hostnames `metadata.google.internal`, `metadata.gcp.internal`.
5. **Return:** Canonical URL (original URL, normalized).

**DNS rebinding defense:** IP is re-validated in the fetch function after following redirects
(see §1.2). The validation here catches the obvious cases before any network I/O.

**Implementation notes:**
- Use `ipaddress.ip_address()` for range checks — stdlib, no deps
- Use `socket.getaddrinfo()` for DNS resolution
- Raise `ValueError` with generic message (G6: no internals in errors)

---

### 1.2 — `tools/web/__init__.py` (empty)

New package.

### 1.3 — `tools/web/fetch_web.py` — `fetch_web(url, ctx) -> FetchWebResult`

**Interface:**

```python
def fetch_web(url: str, ctx: VaultContext) -> FetchWebResult:
    """
    Fetch a web page and extract its text content.
    Validates URL safety, respects size/timeout limits, extracts article text.
    """
```

**Steps:**

1. **Validate URL:** Call `validate_web_url(url)` from `core.security` — raises on invalid.
2. **Rate limit check:** Enforce `web.min_fetch_interval_seconds` from `ctx.settings`.
   - Track last fetch time in a module-level `_last_fetch_time: float` variable.
   - If interval not elapsed, `time.sleep()` the remaining time.
   - Simple and sufficient for single-user, single-process usage.
3. **HTTP GET:** Use `httpx` (already available as transitive dep, or add to deps).
   - `timeout = ctx.settings.system.web.timeout_seconds` (default: 30)
   - `max_redirects = ctx.settings.system.web.max_redirects` (default: 5)
   - `follow_redirects=True`
   - Set `User-Agent: EgoVault/1.0`
4. **Post-redirect validation:** After response, check `response.url` (final URL after redirects).
   Re-run IP validation on the final hostname to prevent DNS rebinding.
5. **Content-Type check:** Accept `text/html*` only. Reject binary, PDF, images, etc.
   Raise `ValueError("URL does not point to an HTML page")`.
6. **Size check:** `len(response.content)` must be ≤ `web.max_response_mb * 1024 * 1024`.
   Raise `ValueError("Page too large")` if exceeded.
   Use streaming response with early abort: read up to limit, abort if exceeded.
7. **Extract text:** Call `parse_html(response.text, base_url=str(response.url))`.
8. **Check extraction:** If `result.text` is empty or `result.word_count < 10`,
   raise `IngestError("Could not extract meaningful text from this page")`.
9. **Return `FetchWebResult`.**

**Return type** (add to `core/schemas.py`):

```python
class FetchWebResult(BaseModel):
    text: str
    title: str | None = None
    author: str | None = None
    date_published: str | None = None
    word_count: int
    final_url: str          # URL after redirects
    content_type: str       # original Content-Type header
```

**Why httpx over requests?**
- Async-ready (future API async migration)
- Built-in redirect limit control
- Streaming response support
- Modern stdlib-style API

If httpx is not acceptable, `requests` works too — the interface is identical.

**Dependencies:** `httpx` (add to `pyproject.toml`).

---

### 1.4 — `tools/web/fetch_web.py` — Tier 1 extraction (optional)

When `web.extraction_tier: 1` in config:
- Import `trafilatura` (optional dependency)
- Use `trafilatura.extract(response.text)` instead of `parse_html()`
- Fallback to `parse_html()` if trafilatura fails or is not installed
- `trafilatura` is NOT added to core deps — only to `[extras]` in pyproject.toml

**Pattern:**

```python
def _extract_content(html: str, url: str, tier: int) -> ParseHtmlResult:
    if tier >= 1:
        try:
            from trafilatura import extract
            text = extract(html, url=url, include_comments=False)
            if text:
                return ParseHtmlResult(text=text, word_count=len(text.split()))
        except ImportError:
            pass
    return parse_html(html, base_url=url)
```

---

## 2. Modified files

### 2.1 — `workflows/ingest.py` — Add `"web"` extractor

```python
def _extract_web(target: str, ctx: VaultContext) -> tuple[str, dict]:
    from tools.web.fetch_web import fetch_web
    result = fetch_web(target, ctx)
    metadata = {"final_url": result.final_url}
    if result.title:
        metadata["title"] = result.title
    if result.author:
        metadata["author"] = result.author
    if result.date_published:
        metadata["date_published"] = result.date_published
    return result.text, metadata
```

Add to registry:

```python
_EXTRACTORS = {
    ...
    "html": _extract_html,
    "web": _extract_web,    # NEW
}
```

**Note:** `target` for web extractor is the URL string (same pattern as YouTube where target is URL).

---

### 2.2 — `api/routers/ingest.py` — Add `POST /ingest/web`

```python
@router.post("/web", status_code=202, response_model=IngestResponse)
def ingest_web_endpoint(body: IngestWebRequest, request: Request):
    ctx = request.app.state.ctx
    from core.security import validate_web_url
    try:
        validate_web_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    executor = request.app.state.executor
    job_id = generate_uid()
    insert_job(ctx.system_db_path, job_id, "web", {"url": body.url})
    _submit_job(executor, _run_ingest, job_id, "web", body.url, ctx,
                body.auto_generate_note, body.title)
    return IngestResponse(job_id=job_id)
```

Pattern: Identical to `/youtube` endpoint — validate URL upfront, async job dispatch.

---

### 2.3 — `api/models.py` — Add `IngestWebRequest`

```python
class IngestWebRequest(BaseModel):
    url: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=200)
    auto_generate_note: bool | None = None
```

**Notes:**
- `title` is optional — if not provided, use title extracted from HTML.
- `url` is required.

---

### 2.4 — `cli/commands/ingest.py` — Auto-detect URLs

Update `_detect_type`:

```python
def _detect_type(target: str) -> str:
    if any(p in target for p in _YOUTUBE_PATTERNS):
        return "youtube"
    if target.startswith(("http://", "https://")):  # NEW — web URL detection
        return "web"
    ext = Path(target).suffix.lower()
    ...
```

**Order matters:** YouTube check first (it's also an http URL), then generic web URL, then file extensions.

Update `_run_ingest` — web type passes URL string directly (no file loading):

```python
def _run_ingest(input_type: str, target: str, ctx, auto_generate_note=None, title=None):
    from workflows.ingest import ingest
    if input_type in ("texte", "html") and Path(target).is_file():
        target = Path(target).read_text(encoding="utf-8")
    # "web" and "youtube" pass target (URL) as-is
    return ingest(input_type, target, ctx, title=title, auto_generate_note=auto_generate_note)
```

No change needed to `_run_ingest` — URLs are already passed as strings.

---

### 2.5 — `mcp/server.py` — Add `ingest_web` tool

```python
@mcp.tool()
def ingest_web(url: str, auto_generate_note: bool | None = None) -> dict:
    """
    Ingest a web page into the vault. Fetches the URL, extracts article text,
    chunks and embeds it for semantic search.
    """
    from workflows.ingest import ingest
    result = ingest("web", url, ctx, auto_generate_note=auto_generate_note)
    return result.model_dump(mode="json")
```

---

### 2.6 — `core/schemas.py` — Add `FetchWebResult`

```python
class FetchWebResult(BaseModel):
    text: str
    title: str | None = None
    author: str | None = None
    date_published: str | None = None
    word_count: int
    final_url: str
    content_type: str
```

---

### 2.7 — `config/system.yaml` — Add `web` section

```yaml
web:
  extraction_tier: 0             # 0 = builtin (bs4), 1 = trafilatura
  max_response_mb: 10            # max HTTP response size
  timeout_seconds: 30            # fetch timeout
  min_fetch_interval_seconds: 2  # global rate limit between fetches
  max_redirects: 5               # max redirect chain length
```

---

### 2.8 — `core/config.py` — Add `WebSettings` model

```python
class WebSettings(BaseModel):
    extraction_tier: int = 0
    max_response_mb: int = 10
    timeout_seconds: int = 30
    min_fetch_interval_seconds: int = 2
    max_redirects: int = 5
```

Add `web: WebSettings = WebSettings()` to the parent `SystemSettings` model.

---

### 2.9 — `pyproject.toml` — Add `httpx` dependency

```toml
dependencies = [
    ...
    "httpx>=0.27",
]

[project.optional-dependencies]
tier1 = ["trafilatura>=1.8"]
```

---

## 3. Tests

### 3.1 — `tests/core/test_security.py` — `TestValidateWebUrl`

```
test_accepts_https_url
test_accepts_http_url
test_rejects_private_ip_127
test_rejects_private_ip_10
test_rejects_private_ip_172_16
test_rejects_private_ip_192_168
test_rejects_link_local_169_254
test_rejects_cloud_metadata
test_rejects_file_scheme
test_rejects_ftp_scheme
test_rejects_data_scheme
test_rejects_no_hostname
test_rejects_empty_string
test_rejects_ipv6_loopback
test_rejects_ipv6_private
```

### 3.2 — `tests/tools/web/test_fetch_web.py`

Mock `httpx.Client.get` to avoid real network calls.

```
test_fetch_valid_page — mock 200 HTML → returns FetchWebResult with text
test_fetch_respects_timeout — verify timeout passed to httpx
test_fetch_rejects_non_html — mock Content-Type: application/pdf → ValueError
test_fetch_rejects_oversized — mock response > max_response_mb → ValueError
test_fetch_rejects_private_ip — mock URL resolving to 127.0.0.1 → ValueError
test_fetch_post_redirect_validation — mock redirect to private IP → ValueError
test_fetch_empty_extraction — mock HTML with no content → IngestError
test_fetch_rate_limit — two rapid calls respect min_fetch_interval_seconds
test_fetch_tier0_extraction — verify parse_html called
test_fetch_tier1_extraction — mock trafilatura, verify it's preferred
test_fetch_tier1_fallback — trafilatura import error → falls back to parse_html
```

### 3.3 — `tests/workflows/test_ingest.py` — Add web extractor test

```
test_ingest_web — mock fetch_web, verify full pipeline (extract → chunk → embed → store)
```

### 3.4 — `tests/api/routers/test_ingest.py` — Add /web endpoint tests

```
test_ingest_web_valid_url — 202 + job_id
test_ingest_web_invalid_url — 400
test_ingest_web_private_ip — 400
```

### 3.5 — `tests/mcp/test_server.py` — Add ingest_web tool test

```
test_ingest_web_tool — mock ingest, verify result
```

---

## 4. Done criteria

- [ ] `validate_web_url()` in `core/security.py` with SSRF protection
- [ ] `tools/web/fetch_web.py` with size/timeout/rate-limit/content-type checks
- [ ] `FetchWebResult` in `core/schemas.py`
- [ ] `WebSettings` in `core/config.py`
- [ ] `web` section in `config/system.yaml`
- [ ] `"web"` extractor in `workflows/ingest.py` registry
- [ ] `POST /ingest/web` API endpoint
- [ ] `IngestWebRequest` model in `api/models.py`
- [ ] CLI auto-detects `http://`/`https://` URLs as `"web"` type
- [ ] `ingest_web` MCP tool
- [ ] `httpx` added to `pyproject.toml`
- [ ] All tests pass (security, fetch, workflow, API, MCP)
- [ ] `trafilatura` available as optional `[tier1]` extra

---

## 5. What is NOT in this spec

- Batch/multi-page/sitemap ingestion
- Image extraction from web pages
- JavaScript rendering (Playwright/Tier 3)
- Per-domain rate limiting
- Authentication/cookies for protected pages
- RSS/Atom feed parsing
- PDF/file download via URL (use existing `/ingest/pdf` with local file)
