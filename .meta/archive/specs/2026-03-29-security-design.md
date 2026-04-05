# Spec: Security Audit — Pre-launch & Hardening

**Date:** 2026-03-29
**Status:** ✅ Implemented (Phase 1 + Phase 2) — archived 2026-04-04
**Dependencies:** all existing specs (monitoring, reranking, semantic-cache, evaluation, frontend)

---

## Context and motivation

EgoVault is a single-user, local-only tool. Before making the repo public on GitHub, we must ensure that:
- No secret is exposed in the code or git history
- Known attack surfaces are documented and addressed
- Guardrails are in place for future external API integrations

This spec covers two phases:
- **Phase 1 — Pre-launch**: blocking checklist before going public (documentation and verifications)
- **Phase 2 — Hardening**: application-level fixes (inputs, logs, permissions, resilience)

---

## Threat model

### What we protect

- The personal vault (notes, sources, embeddings) — the user's intellectual property
- API keys (OpenAI, Anthropic) stored in `config/install.yaml`
- The integrity of the open-source repo — no secrets in git history

### Realistic attack vectors

1. **Poorly cleaned public repo** — committed secrets, forgotten sensitive files
2. **Malicious input via ingest** — crafted PDF/audio/URL that exploits processing tools
3. **Local malicious process** — another program on the same machine hitting localhost:8000
4. **User data in logs** — API keys or sensitive content exposed in `.system.db`

### Out of scope (accepted by design)

- Network attacks (no internet exposure)
- Multi-tenancy / user isolation
- Distributed DDoS

### CRITICAL WARNING — Local use only

> **The security model of this spec covers EXCLUSIVELY local use (localhost, single-user).**
>
> **It is FORBIDDEN to expose EgoVault on a network (LAN, VPN, internet) without a complete, dedicated security audit covering: authentication, authorization, TLS encryption, CSRF protection, network rate limiting, data isolation, and GDPR/personal data compliance.**
>
> **This warning must be reproduced in `docs/architecture/ARCHITECTURE.md` section "Security Model".**

---

## Phase 1 — Pre-launch (blocking)

Zero application code modified — documentation and verifications only.

### P1.1 — SECURITY.md

Write with:
- Scope: local-only, single-user usage
- **Network warning** (reproduce the block above)
- Supported versions (table)
- Vulnerability reporting process (email or GitHub Security Advisory)
- Expected response time

**File:** `SECURITY.md`

### P1.2 — CONTRIBUTING.md

Write with:
- Prerequisites (Python 3.x, uv, Ollama)
- Dev setup (`uv sync`, `init_user_dir.py`, `pytest`)
- Code conventions (technical English, French vault content)
- Commit conventions (`feat:`, `fix:`, `docs:`, `chore:`)
- PR process

**File:** `CONTRIBUTING.md`

### P1.3 — Issue templates

Fill in the existing templates:
- `bug_report.md`: description, steps to reproduce, expected vs actual, environment
- `feature_request.md`: description, motivation, alternatives considered

**Files:** `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`

### P1.4 — Security Model section in ARCHITECTURE.md

Add a dedicated section in `docs/architecture/ARCHITECTURE.md`:
- Summarized threat model
- **Network warning** (full block)
- Reference to this spec for details
- List of documented attack surfaces

**File:** `docs/architecture/ARCHITECTURE.md`

### P1.5 — .gitignore audit

Verify that all sensitive files are ignored:
- `config/install.yaml` (API keys)
- `config/user.yaml` (preferences)
- `.env*` (environment variables)
- `egovault-user/` (user data)
- `*.db` in data directories

**File:** `.gitignore`

### P1.6 — Git history audit

Scan the complete history:
```bash
git log --all --oneline --diff-filter=A -- '*.yaml' '*.env' '*.json'
git log --all -p | grep -i "sk-\|api_key\|secret\|password"
```

**Expected result:** no secret found. Already verified on 2026-03-29: history is clean.

### P1.7 — Dependency audit

```bash
uv audit
```

Document CVEs found and actions taken (upgrade, pin, accept with justification).

**File:** result documented in this spec or in a dedicated file if necessary.

---

## Phase 2 — Application hardening

### 2A — Input validation (HIGH)

#### H2.1 — YouTube URL validation

**Problem:** `re.search()` in `api/routers/ingest.py` (line 58) accepts crafted URLs. Example: `http://evil.com?youtube.com/watch?v=VALIDID` passes validation.

**Fix:** Extract the `video_id` (11 alphanumeric chars), reconstruct the canonical URL `https://www.youtube.com/watch?v={video_id}`, reject everything else. Same logic in `tools/media/fetch_subtitles.py`.

**Files:** `api/routers/ingest.py`, `tools/media/fetch_subtitles.py`
**Test:** Malformed URLs rejected, valid URLs accepted (YouTube long, short, with parameters)

#### H2.2 — MCP file path validation

**Problem:** `mcp/server.py` exposes `transcribe(file_path)` and `compress_audio(file_path)` without validation — accepts any system path.

**Fix:** After `Path(file_path).resolve()`, verify that the resolved path is under `settings.media_path` or `settings.vault_path`. Reject with `ValueError` otherwise.

**File:** `mcp/server.py`
**Test:** Paths outside scope rejected (`/etc/passwd`, `../../sensitive`), valid paths accepted

#### H2.3 — Typst export quote injection

**Problem:** `tools/export/typst.py` (line 19) inserts `note.title` without escaping quotes: `f'#set document(title: "{note.title}")'`.

**Fix:** Escape `"` → `\"` and `\` → `\\` in the title before insertion.

**File:** `tools/export/typst.py`
**Test:** Titles containing `"`, `\`, and special Typst characters

#### H2.4 — YAML frontmatter URL escaping

**Problem:** `infrastructure/vault_writer.py` inserts `url: {note.url}` without quotes — a URL containing `:` or special YAML characters can break parsing.

**Fix:** Wrap the URL in quotes: `url: "{note.url}"`. Escape internal quotes.

**File:** `infrastructure/vault_writer.py`
**Test:** URLs with `:`, `"`, `#`, `?` and complex parameters

#### H2.5 — CHECK constraint on slug in DB

**Problem:** No DB constraint on slug format. If the database is corrupted or directly manipulated, a malicious slug (`../../../etc`) could cause a path traversal.

**Fix:** Add `CHECK(slug GLOB '[a-z0-9][a-z0-9-]*')` on the `sources` and `notes` tables.

**File:** `infrastructure/db.py`
**Test:** INSERT with invalid slug rejected by DB

#### H2.6 — PRAGMA foreign_keys

**Problem:** SQLite disables foreign keys by default. `ON DELETE CASCADE` does not work without `PRAGMA foreign_keys = ON`.

**Fix:** Add `PRAGMA foreign_keys = ON` after each `sqlite3.connect()`.

**File:** `infrastructure/db.py`
**Test:** Deleting a source verifies that associated chunks are cascaded

---

### 2B — Sensitive data protection (HIGH)

#### H2.7 — Sensitive log redaction

**Problem:** `core/logging.py` writes `input_json` and `output_json` in plain text in `tool_logs`. If an LLM error contains an API key, it is persisted.

**Fix:** Before writing to `tool_logs`, apply a `redact_sensitive()` function that:
- Replaces patterns `sk-[a-zA-Z0-9]{20,}` with `sk-***REDACTED***`
- Replaces values of keys containing `api_key`, `secret`, `token`, `password` with `***REDACTED***`
- Applies to `input_json`, `output_json`, and `error`

**File:** `core/logging.py`
**Test:** Strings containing API keys are redacted, normal strings unchanged

#### H2.8 — Error message sanitization

**Problem:** `str(e)` in `api/routers/ingest.py` can expose absolute system paths in stored error messages.

**Fix:** `sanitize_error(e)` wrapper that:
- Removes absolute paths (replaces with basename)
- Removes API keys (same patterns as H2.7)
- Preserves the error type and business message

**File:** `api/routers/ingest.py`, `core/logging.py`
**Test:** Errors with absolute paths sanitized, business message preserved

#### H2.9 — Documentation of sensitive data in .system.db

**Problem:** The semantic cache persists user queries. Tool_logs may contain note content. `.system.db` is a sensitive file.

**Fix:** Document in `docs/architecture/ARCHITECTURE.md` section "Security Model":
- `.system.db` contains sensitive user data (queries, logs, cache)
- Restrictive permissions recommended (see H2.10)
- Never share `.system.db` without cleaning it

**File:** `docs/architecture/ARCHITECTURE.md`

---

### 2C — File permissions (MEDIUM)

#### H2.10 — Restrictive permissions on DBs

**Problem:** `vault.db` and `.system.db` are created with the OS default permissions.

**Fix:** After creating DB files:
- Unix/macOS: `os.chmod(path, 0o600)` (owner read/write only)
- Windows: document the recommendation (ACL via `icacls` or placement in the user profile)

**Note:** Windows has no simple `chmod` equivalent. Placement in `%USERPROFILE%\Documents\egovault-user\` (user directory) provides basic protection.

**Files:** `infrastructure/db.py`, `scripts/setup/init_user_dir.py`
**Test:** On Unix, verify permissions after creation

#### H2.11 — Reranker model cache permissions

**Problem:** `model_cache_dir` could be accessible to other users.

**Fix:** Document in the reranking spec that the cache directory should have restrictive permissions. The default path (`~/.cache/egovault/reranker`) is in the user home — safe by default.

**File:** documentation only

---

### 2D — API resilience (MEDIUM)

#### H2.12 — Rate limiting

**Problem:** No rate limiting — a malicious process can spam expensive endpoints.

**Fix:** Simple rate limiter based on `slowapi` or a custom middleware:
- `/ingest/*`: 10 req/min
- `/search`: 30 req/min
- `/benchmark/run`: 2 req/min
- Other endpoints: 60 req/min

Configurable in `config/system.yaml` under `api.rate_limiting`.

**File:** `api/main.py`
**Test:** Verify that the 11th ingest call in under a minute returns 429

#### H2.13 — Upload size limit

**Problem:** No limit on uploaded file sizes (audio, PDF).

**Fix:** Add validation in ingest endpoints:
- Audio: max 500 MB
- PDF: max 100 MB
- Configurable in `config/system.yaml` under `api.max_upload_size`

**File:** `api/routers/ingest.py`
**Test:** Upload exceeding the limit returns 413

#### H2.14 — Documentation of destructive cache endpoint

**Problem:** `DELETE /api/monitoring/cache` purges the entire cache without confirmation.

**Fix:** Acceptable locally. Document in the cache spec that this endpoint is destructive and irreversible.

**File:** documentation only (cache spec)

---

### 2E — Recommendations for future specs

#### H2.15 — XSS frontend (frontend spec)

**Problem:** `react-markdown` can execute malicious HTML/JS if a note body contains it.

**Recommendation:** Use `rehype-sanitize` with `react-markdown` to block all non-standard HTML. Configure the sanitization schema to allow only pure Markdown.

**File:** to integrate into the frontend plan

#### H2.16 — CSRF protection (frontend spec)

**Problem:** Fetches from the frontend include no CSRF token. A malicious site open in the same browser could send requests to localhost:8000.

**Recommendation:** Add a custom header `X-EgoVault-Client: frontend` on the frontend side, verified by a FastAPI middleware. Browsers do not send custom headers in simple cross-origin requests — sufficient CSRF protection locally.

**File:** to integrate into the frontend plan + `api/main.py`

---

## External API guardrails (preparation)

Today everything is local (Ollama, faster-whisper). But the config already supports `openai_api_key` and `anthropic_api_key`, and future integrations are planned. Guardrails must be established now.

### Comprehensive provider inventory

| Provider | Current/future usage | Data sent | Direction |
|----------|---------------------|-----------|-----------|
| **Ollama** (local) | Embedding `nomic-embed-text`, LLM | No network output | Local only |
| **faster-whisper** (local) | Audio transcription | No network output | Local only |
| **OpenAI** (future) | Embedding (`text-embedding-3-small/large`), LLM (GPT-4o) | Raw chunk text, search queries, full RAG context | Output to `api.openai.com` |
| **Anthropic** (future) | LLM (Claude) for summaries, note writing | Full source text, RAG context | Output to `api.anthropic.com` |
| **OpenRouter** (future, to explore) | Multi-model proxy (OpenAI, Anthropic, Mistral, etc.) via a single API key | Same data as the underlying provider | Output to `openrouter.ai/api` |
| **HuggingFace Hub** | Reranker model download (sentence-transformers) | No user data (download only) | Download only |
| **YouTube** (yt-dlp) | Fetch subtitles, download audio | YouTube URL only (no vault data) | Request to YouTube |
| **PyPI / uv** | Python dependency installation | No user data | Download only |

### G6.1 — Never keys in logs

`core/logging.py`: redaction (H2.7) must cover all known key formats:
- OpenAI: `sk-[a-zA-Z0-9]{20,}`
- Anthropic: `sk-ant-[a-zA-Z0-9]{20,}`
- OpenRouter: `sk-or-[a-zA-Z0-9]{20,}`
- Any field whose name contains `api_key`, `secret`, `token`, `password`, `authorization`

Applied **before** writing, not after. Irreversible by design.

### G6.2 — Never keys in errors

Providers (`infrastructure/llm_provider.py`, `infrastructure/embedding_provider.py`, future `infrastructure/reranker_provider.py`) must:
- Catch exceptions from external SDKs (openai, anthropic)
- Re-raise with a sanitized message: error type + business message, without the key
- Pattern: `except openai.AuthenticationError as e: raise ProviderError("OpenAI authentication failed — check your API key in install.yaml") from None`

The `from None` suppresses the exception chain that might contain the key.

### G6.3 — Key validation at startup

At API boot (`api/main.py` lifespan) and MCP server (`mcp/server.py`):
- If `provider: openai` → verify that `openai_api_key` is non-null and starts with `sk-`
- If `provider: anthropic` → verify that `anthropic_api_key` is non-null and starts with `sk-ant-`
- If `provider: openrouter` (future) → verify `sk-or-` prefix
- Fail fast with a clear message: `"Provider 'openai' configured but no API key found in config/install.yaml"`

### G6.4 — Explicit warning in config

In `config/system.yaml` and `config/user.yaml.example`, when an external provider is documented:

```yaml
# WARNING: if provider != "ollama", your data (note text,
# search queries, RAG context) will be sent to an external service.
# Consult the privacy policy of the chosen provider.
provider: ollama   # ollama (local) | openai | anthropic | openrouter (future)
```

This warning must appear in config examples AND in the documentation.

### G6.5 — Provider traceability in logs

`@loggable` must capture in each `tool_log`:
- `provider: str` — which provider was used ("ollama", "openai", "anthropic")
- Allows the user to know exactly which data stayed local vs was sent externally

Addition of a `provider` field in the `tool_logs` table (nullable, NULL for tools that do not call a provider).

### G6.6 — No keys in the frontend

Absolute rule: the frontend must **never**:
- Receive an API key in a JSON response
- Store a key in `localStorage`, `sessionStorage`, or a cookie
- Send a key in a header or body

All external API calls go through the Python backend. The frontend only knows the name of the active provider (for display), never the key.

`GET /health` endpoint returns `{ provider: "ollama" }` — not the key.

### G6.7 — LLMProvider interface already abstracted

`infrastructure/llm_provider.py` already exposes an abstract interface. When we add an "internal writing" mode (LLM called directly by EgoVault without MCP), it will suffice to call the same provider. No new data path to secure.

Constraint: the internal writing mode must respect the same guardrails (G6.1–G6.6) as any other provider call.

### G6.8 — Rate limiting per external provider

Configurable in `config/system.yaml`:

```yaml
providers:
  rate_limiting:
    openai:
      max_requests_per_minute: 60
      max_tokens_per_minute: 100000
    anthropic:
      max_requests_per_minute: 50
      max_tokens_per_minute: 80000
```

Implemented in each provider via a simple token bucket. Avoids being cut off by the provider in case of a loop or massive ingestion.

### G6.9 — Dry-run mode (future recommendation)

When implementing internal LLM writing, plan a `dry_run: true` mode that:
- Shows the prompt that would be sent to the provider
- Displays the estimated token count
- Sends nothing

Allows the user to verify that no sensitive data leaves before confirming.

### Note on OpenRouter

**Out of scope for this spec.** A path to explore for future API integrations:
- Advantage: a single API key, access to all models (OpenAI, Anthropic, Mistral, Llama, etc.)
- Advantage: automatic fallback between providers
- Open question: OpenRouter data retention policy vs direct provider calls
- If retained, it would suffice to add an `OpenRouterProvider` in `infrastructure/llm_provider.py` with the same contract as existing providers

---

## Integration with existing specs

### Monitoring (`2026-03-28-monitoring-design.md`)
- **H2.7** (log redaction) must be implemented in the same plan — it is `core/logging.py` that writes the `tool_logs`
- **G6.5** (provider in logs) adds a field to `tool_logs`

### Reranking (`2026-03-28-reranking-design.md`)
- **H2.11**: document recommended permissions on `model_cache_dir`
- Verify that sentence-transformers validates the hash of the downloaded model (HuggingFace Hub does this by default)

### Semantic Cache (`2026-03-28-semantic-cache-design.md`)
- **H2.9**: document that `.system.db` contains sensitive user queries
- **H2.14**: document that `DELETE /api/monitoring/cache` is destructive
- **H2.10**: `.system.db` permissions also cover the cache

### Benchmark (`2026-03-28-evaluation-design.md`)
- **H2.12**: `POST /api/benchmark/run` must be rate-limited (CPU-intensive)
- Future write endpoints (`/rate`, `/promote`) must respect the same constraints

### Frontend (`2026-03-28-frontend-design.md`)
- **H2.15**: `rehype-sanitize` mandatory with `react-markdown`
- **H2.16**: `X-EgoVault-Client` header verified on the API side
- **G6.6**: the frontend never handles API keys

---

## Done criteria

### Phase 1 — Pre-launch
- [ ] `SECURITY.md` written with local-only scope + network warning + reporting process
- [ ] `CONTRIBUTING.md` written with dev setup + conventions + PR process
- [ ] Issue templates filled in (bug_report, feature_request)
- [ ] `docs/architecture/ARCHITECTURE.md` contains "Security Model" section with explicit network warning
- [ ] `.gitignore` verified (no missing sensitive file)
- [ ] Git history scanned (no secrets)
- [ ] `uv audit` passed (no unaddressed critical CVE)

**Gate:** Phase 1 complete = repo ready to be made public.

### Phase 2 — Hardening
- [ ] All HIGH items (H2.1–H2.9) implemented and tested
- [ ] All MEDIUM items (H2.10–H2.14) implemented or documented
- [ ] Frontend recommendations (H2.15–H2.16) integrated into the frontend spec
- [ ] Unit tests for each fix (URL regex, path validation, log redaction, slug CHECK, foreign keys)
- [ ] External API guardrails (G6.1–G6.6) implemented
- [ ] Security spec referenced in `docs/architecture/ARCHITECTURE.md` section "Security Model"

**Gate:** Phase 2 complete = hardening baseline reached for local use.

---

## What is NOT in this spec

- Network authentication (login, JWT, OAuth) → dedicated audit required if network exposure
- TLS encryption → same
- Multi-tenancy / user isolation → outside single-user design
- GDPR compliance audit → out of scope for personal use
- OpenRouter implementation → path to explore separately
- Pen-testing / fuzzing → out of scope, recommended before any network exposure
