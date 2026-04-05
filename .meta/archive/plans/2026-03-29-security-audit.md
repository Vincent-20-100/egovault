# Security Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Secure EgoVault for open-source release (Phase 1: documentation/verification) and harden the application against local attack vectors (Phase 2: code changes).

**Architecture:** Two sequential phases. Phase 1 is documentation-only (no code changes) and gates the repo going public. Phase 2 adds input validation, log redaction, DB constraints, file permissions, and rate limiting. All changes follow TDD.

**Tech Stack:** Python 3.x, FastAPI, SQLite, pytest

**Spec:** `.meta/specs/2026-03-29-security-design.md`

---

## File Map

### Phase 1 — Documentation only
| Action | File |
|--------|------|
| Rewrite | `SECURITY.md` |
| Rewrite | `CONTRIBUTING.md` |
| Rewrite | `.github/ISSUE_TEMPLATE/bug_report.md` |
| Rewrite | `.github/ISSUE_TEMPLATE/feature_request.md` |
| Modify | `docs/architecture/ARCHITECTURE.md` (add section 10: Security Model) |
| Modify | `.gitignore` (add `.env*` pattern) |
| Modify | `config/user.yaml.example` (add provider warning comment) |
| Modify | `config/install.yaml.example` (add provider warning comment) |

### Phase 2 — Code changes
| Action | File | Responsibility |
|--------|------|---------------|
| Create | `core/sanitize.py` | `redact_sensitive()` + `sanitize_error()` utilities |
| Create | `tests/core/test_sanitize.py` | Tests for redaction and error sanitizing |
| Modify | `core/logging.py:41-64` | Apply redaction before writing logs |
| Create | `core/security.py` | `validate_file_path()` + `validate_youtube_url()` + `set_restrictive_permissions()` |
| Create | `tests/core/test_security.py` | Tests for path validation, URL validation, permissions |
| Modify | `api/routers/ingest.py:15,30-31,42,53,58` | Use strict URL validation + sanitized errors |
| Modify | `api/main.py` | Add rate limiting middleware |
| Create | `tests/api/test_rate_limiting.py` | Rate limiting tests |
| Modify | `tools/media/fetch_subtitles.py:18-22` | Use strict video ID extraction |
| Modify | `mcp/server.py:112-123` | Add file path validation |
| Create | `tests/mcp/test_path_validation.py` | MCP path validation tests |
| Modify | `tools/export/typst.py:19` | Escape quotes in title |
| Modify | `infrastructure/vault_writer.py:61` | Quote URL in frontmatter |
| Modify | `infrastructure/db.py:21-30,33-39,44-46,60-62` | Add PRAGMA foreign_keys + CHECK on slug |
| Create | `tests/infrastructure/test_db_constraints.py` | FK cascade + slug constraint tests |
| Modify | `scripts/setup/init_user_dir.py` | Set restrictive permissions on created dirs |

---

## Phase 1 — Pre-launch Documentation

### Task 1: SECURITY.md

**Files:**
- Rewrite: `SECURITY.md`

- [ ] **Step 1: Write SECURITY.md**

```markdown
# Security Policy

## Scope — Local Use Only

EgoVault is designed for **local, single-user use** on a personal machine. The API server binds to `127.0.0.1:8000` and is not intended for network exposure.

> **WARNING: Do NOT expose EgoVault on any network (LAN, VPN, internet) without a dedicated security audit covering: authentication, authorization, TLS encryption, CSRF protection, network-aware rate limiting, data isolation, and GDPR/personal data compliance. The current security model provides NO protection against network-based attacks.**

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | Yes       |
| 1.x     | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in EgoVault:

1. **Do NOT open a public issue.**
2. Use [GitHub Security Advisories](../../security/advisories/new) to report privately.
3. Include: description of the vulnerability, steps to reproduce, potential impact.
4. Expected response time: **72 hours** for acknowledgment, **30 days** for a fix or mitigation plan.

## Security Model

EgoVault's security audit (`.meta/specs/2026-03-29-security-design.md`) covers:
- Input validation (URLs, file paths, user-provided content)
- Log redaction (API keys, system paths)
- Database constraints (slug format, foreign key enforcement)
- File permissions (restrictive on DB files)
- Rate limiting (local API endpoints)

This audit assumes **localhost-only deployment**. See `docs/architecture/ARCHITECTURE.md` section 10 for the full security model.
```

- [ ] **Step 2: Commit**

```bash
git add SECURITY.md
git commit -m "docs: write SECURITY.md — local-only scope, reporting process, network warning"
```

---

### Task 2: CONTRIBUTING.md

**Files:**
- Rewrite: `CONTRIBUTING.md`

- [ ] **Step 1: Write CONTRIBUTING.md**

```markdown
# Contributing to EgoVault

Thank you for your interest in contributing to EgoVault!

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [Ollama](https://ollama.ai/) running locally with `nomic-embed-text` model pulled
- SQLite 3.40+ (ships with Python)

## Development Setup

```bash
# Clone and install dependencies
git clone https://github.com/Vincent-20-100/egovault.git
cd egovault
uv sync

# Initialize user data directory
.venv/Scripts/python scripts/setup/init_user_dir.py

# Run tests
.venv/Scripts/python -m pytest tests/
```

## Code Conventions

- **Code, SQL, comments, config keys:** English
- **Vault content (notes, tags, slugs):** French (configurable via `user.yaml`)
- **Architecture:** `core/` (interfaces), `tools/` (atomic functions), `workflows/` (orchestration), `infrastructure/` (implementations)
- A tool **never imports** another tool
- See `docs/architecture/ARCHITECTURE.md` for the full reference

## Commit Messages

Format: `prefix: description in English`

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Maintenance, refactoring, CI |
| `test:` | Test-only changes |

## Pull Request Process

1. Fork the repo and create a branch from `main`
2. Add tests for any new functionality
3. Ensure all tests pass: `.venv/Scripts/python -m pytest tests/`
4. Update `docs/architecture/ARCHITECTURE.md` if you changed behavior, schema, or contracts
5. Open a PR with a clear description of what and why

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities. **Do not open public issues for security bugs.**
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: write CONTRIBUTING.md — dev setup, conventions, PR process"
```

---

### Task 3: Issue Templates

**Files:**
- Rewrite: `.github/ISSUE_TEMPLATE/bug_report.md`
- Rewrite: `.github/ISSUE_TEMPLATE/feature_request.md`

- [ ] **Step 1: Write bug_report.md**

```markdown
---
name: Bug report
about: Report a bug to help improve EgoVault
title: '[BUG] '
labels: bug
assignees: ''
---

## Description

A clear description of the bug.

## Steps to Reproduce

1. ...
2. ...
3. ...

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened. Include error messages or logs if available.

## Environment

- OS: [e.g., Windows 11, macOS 14, Ubuntu 24.04]
- Python version: [e.g., 3.12.3]
- EgoVault version/commit: [e.g., commit hash or tag]
- Ollama version: [e.g., 0.3.0]
```

- [ ] **Step 2: Write feature_request.md**

```markdown
---
name: Feature request
about: Suggest an idea or improvement for EgoVault
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Description

A clear description of the feature or improvement you'd like.

## Motivation

Why is this useful? What problem does it solve?

## Alternatives Considered

Any alternative solutions or features you've considered.

## Additional Context

Any other context, mockups, or references.
```

- [ ] **Step 3: Commit**

```bash
git add .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md
git commit -m "docs: remplir issue templates (bug report + feature request)"
```

---

### Task 4: Security Model in ARCHITECTURE.md

**Files:**
- Modify: `docs/architecture/ARCHITECTURE.md` (append section 10 before the final `---` line at the end)

- [ ] **Step 1: Add section 10 at the end of ARCHITECTURE.md**

Insert before the final `*Spec initiale...` lines (after line 1130 `---`):

```markdown
## 10. Security Model

**Last updated:** 2026-03-29
**Full spec:** `.meta/specs/2026-03-29-security-design.md`

### 10.1 Scope — Local use only

EgoVault is designed for **single-user, local-only** use. The API server listens on `127.0.0.1:8000`. The MCP server is local.

> **CRITICAL WARNING: It is FORBIDDEN to expose EgoVault on any network (LAN, VPN, internet) without a dedicated full security audit covering: authentication, authorization, TLS encryption, CSRF protection, network-aware rate limiting, data isolation, and GDPR/personal data compliance. The current security model provides NO protection against network-based attacks.**

### 10.2 Sensitive data

| File | Sensitive content | Protection |
|---------|-----------------|------------|
| `config/install.yaml` | API keys (OpenAI, Anthropic) | `.gitignore`, never committed |
| `vault.db` | Notes, sources, user embeddings | Restrictive permissions (0600 Unix) |
| `.system.db` | Logs, cache queries, jobs | Restrictive permissions (0600 Unix) |
| `egovault-user/vault/` | Exported Markdown notes | User directory, `.gitignore` |

### 10.3 Documented attack surfaces

- **User inputs**: YouTube URLs, uploaded files (audio/PDF), MCP paths — validated at entry
- **Logs**: automatic redaction of API keys and system paths before writing to `tool_logs`
- **Database**: CHECK constraint on slug, PRAGMA foreign_keys enabled, parameterized queries
- **API**: rate limiting on expensive endpoints, upload size limit
- **External providers**: if `provider != ollama`, data (text, queries) is sent to an external service — documented in config files

### 10.4 External providers — guardrails

When an external provider is configured (OpenAI, Anthropic):
- API keys are **never** logged, exposed in errors, or returned by the API
- The provider used is tracked in each `tool_log` (field `provider`)
- The frontend **never** receives an API key
- An explicit warning is displayed in the config files
```

- [ ] **Step 2: Update the history line at the bottom of the file**

Find the last `*Last updated...` line and add after it:

```markdown
*Last updated 2026-03-29: added section 10 Security Model (pre-launch security spec + hardening).*
```

- [ ] **Step 3: Update the Table of Contents**

Add after line `9. [Note Conventions](#9-note-conventions)`:

```markdown
10. [Security Model](#10-security-model)
```

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/ARCHITECTURE.md
git commit -m "docs: add Security Model section to ARCHITECTURE.md"
```

---

### Task 5: Audit .gitignore + config warnings

**Files:**
- Modify: `.gitignore`
- Modify: `config/user.yaml.example`
- Modify: `config/install.yaml.example`

- [ ] **Step 1: Add .env* pattern to .gitignore**

Add after line 19 (`config.yaml`):

```gitignore
.env*
```

- [ ] **Step 2: Add provider warning to user.yaml.example**

Replace lines 6-8 in `config/user.yaml.example`:

```yaml
# ATTENTION: if provider != "ollama", your data (note text, search queries,
# RAG context) will be sent to an external service.
# Check the privacy policy of the chosen provider.
embedding:
  provider: ollama           # ollama (local) | openai (external)
  model: nomic-embed-text    # model name for chosen provider

# ATTENTION: same warning — if provider != "ollama", data is sent externally.
llm:
  provider: claude           # claude (external) | openai (external) | ollama (local)
  model: claude-sonnet-4-6
```

- [ ] **Step 3: Add provider warning to install.yaml.example**

Replace lines 15-18 in `config/install.yaml.example`:

```yaml
providers:
  ollama_base_url: "http://localhost:11434"
  # API keys for external providers — NEVER commit real keys.
  # If set, your data (note text, queries) will be sent to the provider's API.
  openai_api_key: null
  anthropic_api_key: null
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore config/user.yaml.example config/install.yaml.example
git commit -m "docs: add .env* to .gitignore + provider warnings in config examples"
```

---

### Task 6: Audit git history + dependencies

**Files:** None modified — verification only.

- [ ] **Step 1: Scan git history for secrets**

```bash
.venv/Scripts/python -c "
import subprocess, sys
# Check for secret patterns in all committed content
result = subprocess.run(
    ['git', 'log', '--all', '-p', '--diff-filter=A'],
    capture_output=True, text=True, errors='replace'
)
import re
patterns = [
    r'sk-[a-zA-Z0-9]{20,}',
    r'sk-ant-[a-zA-Z0-9]{20,}',
    r'OPENAI_API_KEY\s*=\s*[\"'\''][^\"'\'']+',
]
findings = []
for i, line in enumerate(result.stdout.split('\n')):
    for pat in patterns:
        if re.search(pat, line):
            findings.append(line.strip()[:120])
if findings:
    print(f'ALERT: {len(findings)} potential secrets found!')
    for f in findings[:10]:
        print(f'  {f}')
    sys.exit(1)
else:
    print('OK: No secrets found in git history.')
"
```

Expected: `OK: No secrets found in git history.`

- [x] **Step 2: Run dependency audit**

```bash
uv audit
```

**Result (2026-03-29):** 2 CVEs found, 1 fixed, 1 accepted.

| Package | CVE | Action |
|---------|-----|--------|
| `requests` 2.32.5 | CVE-2026-25645 — Insecure Temp File Reuse in `extract_zipped_paths()` | ✅ **Fixed** — upgraded to 2.33.0 in `pyproject.toml` |
| `pygments` 2.19.2 | CVE-2026-4539 — ReDoS via GUID regex | ⚠️ **Accepted** — transitive dep of `pytest`/`rich`, not in user data path, no fix available |

- [x] **Step 3: Verify .gitignore coverage**

```bash
git status --porcelain | grep -E "install\.yaml|user\.yaml|\.env|vault\.db|\.system\.db" && echo "ALERT: sensitive files not ignored!" || echo "OK: All sensitive files properly ignored."
```

Expected: `OK: All sensitive files properly ignored.`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .meta/plans/2026-03-29-security-audit.md
git commit -m "chore: security Phase 1 — upgrade requests 2.33 (CVE-2026-25645), document pygments CVE-2026-4539 accepted"
```

---

## Phase 2 — Hardening

### Task 7: Core sanitization utilities

**Files:**
- Create: `core/sanitize.py`
- Create: `tests/core/test_sanitize.py`

- [ ] **Step 1: Write tests for redact_sensitive()**

```python
# tests/core/test_sanitize.py
"""Tests for core.sanitize — redaction and error sanitizing."""

from core.sanitize import redact_sensitive, sanitize_error


class TestRedactSensitive:
    def test_redacts_openai_key(self):
        text = '{"api_key": "sk-abc123def456ghi789jkl012mno345pqr678"}'
        result = redact_sensitive(text)
        assert "sk-abc123" not in result
        assert "sk-***REDACTED***" in result

    def test_redacts_anthropic_key(self):
        text = "error: sk-ant-api03-abcdef1234567890abcdef1234567890 is invalid"
        result = redact_sensitive(text)
        assert "sk-ant-api03" not in result
        assert "sk-***REDACTED***" in result

    def test_redacts_openrouter_key(self):
        text = "key=sk-or-v1-abcdef1234567890abcdef"
        result = redact_sensitive(text)
        assert "sk-or-v1" not in result
        assert "sk-***REDACTED***" in result

    def test_redacts_json_key_fields(self):
        text = '{"openai_api_key": "my-secret-key-value", "name": "test"}'
        result = redact_sensitive(text)
        assert "my-secret-key-value" not in result
        assert '"name": "test"' in result

    def test_redacts_password_fields(self):
        text = '{"password": "hunter2", "user": "admin"}'
        result = redact_sensitive(text)
        assert "hunter2" not in result

    def test_preserves_normal_text(self):
        text = '{"query": "what is antifragility?", "mode": "chunks"}'
        assert redact_sensitive(text) == text

    def test_handles_none(self):
        assert redact_sensitive(None) is None

    def test_handles_empty_string(self):
        assert redact_sensitive("") == ""


class TestSanitizeError:
    def test_strips_absolute_paths_unix(self):
        err = FileNotFoundError("/home/user/Documents/egovault-user/data/vault.db")
        result = sanitize_error(err)
        assert "/home/user" not in result
        assert "vault.db" in result

    def test_strips_absolute_paths_windows(self):
        err = FileNotFoundError("C:\\Users\\Vincent\\Documents\\egovault-user\\data\\vault.db")
        result = sanitize_error(err)
        assert "C:\\Users\\Vincent" not in result
        assert "vault.db" in result

    def test_strips_api_keys_from_error(self):
        err = RuntimeError("Auth failed with key sk-abc123def456ghi789jkl012mno345pqr678")
        result = sanitize_error(err)
        assert "sk-abc123" not in result
        assert "sk-***REDACTED***" in result

    def test_preserves_error_type_and_message(self):
        err = ValueError("invalid youtube url")
        result = sanitize_error(err)
        assert "ValueError" in result
        assert "invalid youtube url" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_sanitize.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.sanitize'`

- [ ] **Step 3: Implement core/sanitize.py**

```python
# core/sanitize.py
"""
Redaction and sanitization utilities for EgoVault.

redact_sensitive() — strips API keys and sensitive field values from strings.
sanitize_error() — produces safe error messages without system paths or keys.

Applied BEFORE writing to logs/DB. Irreversible by design.
"""

import re
from pathlib import PurePosixPath, PureWindowsPath

# API key patterns — sk-xxx with 20+ alphanumeric chars
_KEY_PATTERN = re.compile(r"sk-[a-zA-Z0-9_-]{20,}")

# JSON field names whose values should be redacted
_SENSITIVE_FIELDS = re.compile(
    r'"(api_key|secret|token|password|authorization|openai_api_key|anthropic_api_key)'
    r'"\s*:\s*"[^"]*"',
    re.IGNORECASE,
)

# Absolute paths — Unix or Windows
_ABS_PATH_UNIX = re.compile(r"/(?:home|usr|tmp|etc|var|opt|root)/[^\s,;\"')\]]+")
_ABS_PATH_WIN = re.compile(r"[A-Z]:\\[^\s,;\"')\]]+", re.IGNORECASE)

_REDACTED = "sk-***REDACTED***"


def redact_sensitive(text: str | None) -> str | None:
    """
    Remove API keys and sensitive JSON field values from a string.
    Returns None if input is None.
    """
    if text is None:
        return None
    if not text:
        return text

    # Redact bare API key patterns
    result = _KEY_PATTERN.sub(_REDACTED, text)

    # Redact JSON fields with sensitive names
    def _redact_field(match: re.Match) -> str:
        field_name = match.group(1)
        return f'"{field_name}": "***REDACTED***"'

    result = _SENSITIVE_FIELDS.sub(_redact_field, result)
    return result


def sanitize_error(err: Exception) -> str:
    """
    Produce a safe error string: ErrorType: message.
    Strips absolute paths (keeps basename only) and redacts API keys.
    """
    msg = str(err)

    # Replace absolute paths with basename
    def _basename_unix(match: re.Match) -> str:
        return PurePosixPath(match.group(0)).name

    def _basename_win(match: re.Match) -> str:
        return PureWindowsPath(match.group(0)).name

    msg = _ABS_PATH_WIN.sub(_basename_win, msg)
    msg = _ABS_PATH_UNIX.sub(_basename_unix, msg)

    # Redact API keys
    msg = redact_sensitive(msg) or msg

    return f"{type(err).__name__}: {msg}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_sanitize.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/sanitize.py tests/core/test_sanitize.py
git commit -m "feat: core/sanitize.py — API key redaction + error sanitizing"
```

---

### Task 8: Apply redaction to logging

**Files:**
- Modify: `core/logging.py:41-64`

- [ ] **Step 1: Write test for redacted logging**

Add to `tests/core/test_logging.py`:

```python
def test_write_log_redacts_sensitive_data(tmp_path, monkeypatch):
    """Tool logs must redact API keys before writing."""
    from core import logging as log_mod
    from core.sanitize import redact_sensitive

    db_path = tmp_path / ".system.db"

    # Init system DB
    from infrastructure.db import init_system_db
    init_system_db(db_path)
    log_mod.configure(db_path)

    # Write a log entry with a fake API key
    log_mod._write_log(
        tool_name="test_tool",
        input_json='{"api_key": "sk-abc123def456ghi789jkl012mno345pqr678"}',
        output_json=None,
        duration_ms=100,
        status="success",
        error=None,
    )

    # Read back and check redaction
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT input_json FROM tool_logs ORDER BY rowid DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    assert "sk-abc123" not in row[0]
    assert "***REDACTED***" in row[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/core/test_logging.py::test_write_log_redacts_sensitive_data -v
```

Expected: FAIL — key is not redacted yet

- [ ] **Step 3: Modify core/logging.py to apply redaction**

In `core/logging.py`, modify `_write_log()` to import and apply redaction. Replace the function (lines 41-64):

```python
def _write_log(
    tool_name: str,
    input_json: str | None,
    output_json: str | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
) -> None:
    """Write a tool_log entry to .system.db. Redacts sensitive data before writing."""
    if _db_path is None:
        return
    try:
        from infrastructure.db import get_system_connection
        from core.uid import generate_uid
        from core.sanitize import redact_sensitive

        conn = get_system_connection(_db_path)
        conn.execute(
            """INSERT INTO tool_logs (uid, tool_name, input_json, output_json, duration_ms, status, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_uid(), tool_name,
             redact_sensitive(input_json),
             redact_sensitive(output_json),
             duration_ms, status,
             redact_sensitive(error)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # logging must never crash the tool
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python -m pytest tests/core/test_logging.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/logging.py tests/core/test_logging.py
git commit -m "fix: redact sensitive data in tool_logs before writing"
```

---

### Task 9: YouTube URL strict validation

**Files:**
- Create: `core/security.py`
- Create: `tests/core/test_security.py`
- Modify: `api/routers/ingest.py:15,58`
- Modify: `tools/media/fetch_subtitles.py:18-22`

- [ ] **Step 1: Write tests for URL validation**

```python
# tests/core/test_security.py
"""Tests for core.security — input validation utilities."""

from core.security import validate_youtube_url


class TestValidateYoutubeUrl:
    def test_standard_url(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42") == "dQw4w9WgXcQ"

    def test_url_with_playlist(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest") == "dQw4w9WgXcQ"

    def test_rejects_crafted_url(self):
        # This is the attack vector: evil domain with youtube in query string
        assert validate_youtube_url("http://evil.com?youtube.com/watch?v=dQw4w9WgXcQ") is None

    def test_rejects_no_video_id(self):
        assert validate_youtube_url("https://www.youtube.com/") is None

    def test_rejects_short_video_id(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=short") is None

    def test_rejects_empty(self):
        assert validate_youtube_url("") is None

    def test_rejects_non_youtube(self):
        assert validate_youtube_url("https://vimeo.com/123456") is None

    def test_mobile_url(self):
        assert validate_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_security.py::TestValidateYoutubeUrl -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.security'`

- [ ] **Step 3: Implement validate_youtube_url in core/security.py**

```python
# core/security.py
"""
Security utilities for EgoVault.

validate_youtube_url() — strict YouTube URL validation.
validate_file_path() — path containment check.
set_restrictive_permissions() — set 0600 on files (Unix only).
"""

import os
import re
import sys
from pathlib import Path

# YouTube URL must have youtube.com or youtu.be as the actual host
_YOUTUBE_HOST_RE = re.compile(
    r"^https?://(?:www\.|m\.)?(?:youtube\.com/watch\?.*v=|youtu\.be/)"
)
_VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def validate_youtube_url(url: str) -> str | None:
    """
    Extract YouTube video ID from a URL using strict host validation.
    Returns the 11-char video ID, or None if the URL is invalid.
    """
    if not url or not _YOUTUBE_HOST_RE.match(url):
        return None

    # Extract video ID
    if "youtu.be/" in url:
        # Short URL: https://youtu.be/VIDEO_ID
        path_part = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    else:
        # Long URL: https://www.youtube.com/watch?v=VIDEO_ID
        match = re.search(r"[?&]v=([^&]+)", url)
        if not match:
            return None
        path_part = match.group(1)

    # Validate video ID format (exactly 11 alphanumeric + _-)
    if _VIDEO_ID_RE.fullmatch(path_part):
        return path_part
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_security.py::TestValidateYoutubeUrl -v
```

Expected: All PASS

- [ ] **Step 5: Update api/routers/ingest.py to use strict validation**

Replace lines 1-2 and 15 (remove old regex):

```python
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from api.models import IngestYoutubeRequest, IngestResponse
from core.uid import generate_uid
from core.security import validate_youtube_url
from core.sanitize import sanitize_error
from infrastructure.db import insert_job, update_job_status, update_job_done, update_job_failed
```

Remove line 15 (`_YOUTUBE_RE = ...`).

Replace the youtube endpoint validation (line 58):

```python
@router.post("/youtube", status_code=202, response_model=IngestResponse)
def ingest_youtube_endpoint(body: IngestYoutubeRequest, request: Request):
    video_id = validate_youtube_url(body.url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="invalid youtube url")
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    settings = request.app.state.settings
    executor = request.app.state.executor
    job_id = generate_uid()
    insert_job(settings.system_db_path, job_id, "youtube", {"url": canonical_url})
    _submit_job(executor, _run_youtube, job_id, canonical_url, settings)
    return IngestResponse(job_id=job_id)
```

Replace `str(e)` with `sanitize_error(e)` in the three `_run_*` functions (lines 31, 42, 53):

```python
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))
```

- [ ] **Step 6: Update tools/media/fetch_subtitles.py**

Replace `_extract_video_id` (lines 18-22):

```python
def _extract_video_id(url: str) -> str:
    from core.security import validate_youtube_url
    video_id = validate_youtube_url(url)
    if video_id is None:
        raise ValueError(f"Cannot extract video ID from URL: {url}")
    return video_id
```

- [ ] **Step 7: Run existing tests to verify no regressions**

```bash
.venv/Scripts/python -m pytest tests/api/test_ingest.py tests/tools/ -v
```

Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add core/security.py tests/core/test_security.py api/routers/ingest.py tools/media/fetch_subtitles.py
git commit -m "fix: validation stricte URL YouTube + sanitizing erreurs ingest"
```

---

### Task 10: MCP file path validation

**Files:**
- Modify: `core/security.py` (add `validate_file_path`)
- Create: `tests/mcp/test_path_validation.py`
- Modify: `mcp/server.py:112-123`

- [ ] **Step 1: Write tests for path validation**

```python
# tests/core/test_security.py — append to existing file

from core.security import validate_file_path


class TestValidateFilePath:
    def test_valid_path_under_media(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        target = media / "test.mp3"
        target.touch()
        assert validate_file_path(str(target), [media]) == target

    def test_rejects_path_outside_allowed(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        outside = tmp_path / "outside.txt"
        outside.touch()
        assert validate_file_path(str(outside), [media]) is None

    def test_rejects_traversal(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        assert validate_file_path(str(media / ".." / "etc" / "passwd"), [media]) is None

    def test_rejects_nonexistent(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        assert validate_file_path(str(media / "ghost.mp3"), [media]) is None

    def test_multiple_allowed_dirs(self, tmp_path):
        media = tmp_path / "media"
        vault = tmp_path / "vault"
        media.mkdir()
        vault.mkdir()
        target = vault / "note.md"
        target.touch()
        assert validate_file_path(str(target), [media, vault]) == target
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_security.py::TestValidateFilePath -v
```

Expected: FAIL — `ImportError: cannot import name 'validate_file_path'`

- [ ] **Step 3: Add validate_file_path to core/security.py**

Append to `core/security.py`:

```python
def validate_file_path(file_path: str, allowed_dirs: list[Path]) -> Path | None:
    """
    Validate that a file path resolves to a location under one of the allowed directories.
    Returns the resolved Path if valid, None otherwise.
    """
    try:
        resolved = Path(file_path).resolve()
    except (OSError, ValueError):
        return None

    if not resolved.exists():
        return None

    for allowed in allowed_dirs:
        try:
            resolved.relative_to(allowed.resolve())
            return resolved
        except ValueError:
            continue
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_security.py::TestValidateFilePath -v
```

Expected: All PASS

- [ ] **Step 5: Add path validation to MCP server**

In `mcp/server.py`, modify the `transcribe` and `compress_audio` tools (lines 112-123):

```python
@mcp.tool()
def transcribe(file_path: str, language: str = "fr") -> dict:
    """Transcribe audio/video to text."""
    from core.security import validate_file_path
    validated = validate_file_path(file_path, [settings.media_path])
    if validated is None:
        raise ValueError(f"File path not allowed — must be under media directory")
    result = _transcribe_tool(str(validated), language)
    return result.model_dump(mode="json")


@mcp.tool()
def compress_audio(file_path: str, bitrate_kbps: int = 12) -> dict:
    """Compress audio to Opus mono."""
    from core.security import validate_file_path
    validated = validate_file_path(file_path, [settings.media_path])
    if validated is None:
        raise ValueError(f"File path not allowed — must be under media directory")
    result = _compress_audio_tool(str(validated), bitrate_kbps)
    return result.model_dump(mode="json")
```

- [ ] **Step 6: Run existing MCP tests**

```bash
.venv/Scripts/python -m pytest tests/mcp/ -v
```

Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add core/security.py tests/core/test_security.py mcp/server.py
git commit -m "fix: MCP file path validation — restricted to media directory"
```

---

### Task 11: Typst + YAML frontmatter escaping

**Files:**
- Modify: `tools/export/typst.py:19`
- Modify: `infrastructure/vault_writer.py:61`
- Tests in existing test files

- [ ] **Step 1: Write test for Typst quote escaping**

Add to `tests/tools/test_export_typst.py` (or create if needed):

```python
def test_note_to_typst_escapes_quotes():
    """Titles with quotes must be escaped in Typst document()."""
    from tools.export.typst import _note_to_typst
    from unittest.mock import MagicMock

    note = MagicMock()
    note.title = 'Test "with quotes" and \\backslash'
    note.docstring = None
    note.tags = []
    note.body = "Body text"

    result = _note_to_typst(note)
    assert r'\"with quotes\"' in result
    assert r'\\backslash' in result
```

- [ ] **Step 2: Write test for YAML frontmatter URL quoting**

Add to `tests/infrastructure/test_vault_writer.py` (or create if needed):

```python
def test_frontmatter_quotes_url_with_special_chars():
    """URLs with colons and special chars must be quoted in YAML frontmatter."""
    from infrastructure.vault_writer import build_frontmatter
    from core.schemas import Note

    note = Note(
        uid="test-uid", slug="test", title="Test", body="Body",
        date_created="2026-01-01", date_modified="2026-01-01",
        url='https://example.com/path?q=hello&t=42#section"quoted'
    )
    result = build_frontmatter(note)
    # URL should be quoted
    assert 'url: "' in result
    # Internal quotes should be escaped
    assert '\\"quoted' in result
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/test_export_typst.py::test_note_to_typst_escapes_quotes tests/infrastructure/test_vault_writer.py::test_frontmatter_quotes_url_with_special_chars -v
```

Expected: FAIL

- [ ] **Step 4: Fix Typst escaping in tools/export/typst.py**

Replace line 19:

```python
    lines = [
        f'#set document(title: "{note.title.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}")',
```

Cleaner — add a helper at the top of `_note_to_typst`:

```python
def _note_to_typst(note) -> str:
    """Generate Typst source from a Note record."""
    safe_title = note.title.replace("\\", "\\\\").replace('"', '\\"')
    lines = [
        f'#set document(title: "{safe_title}")',
        '#set page(margin: 2cm)',
        '#set text(font: "Linux Libertine", size: 11pt)',
        '',
        f'= {note.title}',
        '',
    ]
    if note.docstring:
        lines += [f'#quote[{note.docstring}]', '']
    if note.tags:
        lines += [f'#text(gray)[Tags: {", ".join(note.tags)}]', '']
    lines += ['---', '', note.body]
    return '\n'.join(lines)
```

- [ ] **Step 5: Fix YAML URL quoting in infrastructure/vault_writer.py**

Replace line 61:

```python
    if note.url is not None:
        safe_url = note.url.replace('"', '\\"')
        lines.append(f'url: "{safe_url}"')
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/tools/test_export_typst.py tests/infrastructure/test_vault_writer.py -v
```

Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add tools/export/typst.py infrastructure/vault_writer.py tests/
git commit -m "fix: escape Typst quotes + quote URL in YAML frontmatter"
```

---

### Task 12: Database constraints (foreign keys + slug CHECK)

**Files:**
- Modify: `infrastructure/db.py:21-30,33-39,44-46,60-62`
- Create: `tests/infrastructure/test_db_constraints.py`

- [ ] **Step 1: Write tests for foreign key enforcement**

```python
# tests/infrastructure/test_db_constraints.py
"""Tests for database security constraints."""

import sqlite3
import pytest
from pathlib import Path
from infrastructure.db import get_vault_connection, init_db, insert_source, insert_chunks
from core.schemas import Source, ChunkResult


def test_foreign_keys_enabled(tmp_path):
    """PRAGMA foreign_keys must be ON for all vault connections."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    conn.close()
    assert result[0] == 1


def test_cascade_delete_chunks_when_source_deleted(tmp_path):
    """Deleting a source must cascade-delete its chunks."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)

    # Insert a source
    conn.execute(
        "INSERT INTO sources (uid, slug, source_type, status, date_added) VALUES (?, ?, ?, ?, ?)",
        ("s1", "test-source", "youtube", "raw", "2026-01-01"),
    )
    # Insert a chunk referencing the source
    conn.execute(
        "INSERT INTO chunks (uid, source_uid, position, content, token_count) VALUES (?, ?, ?, ?, ?)",
        ("c1", "s1", 0, "chunk text", 10),
    )
    conn.commit()

    # Delete the source
    conn.execute("DELETE FROM sources WHERE uid = ?", ("s1",))
    conn.commit()

    # Chunk should be gone (cascade)
    row = conn.execute("SELECT * FROM chunks WHERE uid = ?", ("c1",)).fetchone()
    conn.close()
    assert row is None


def test_slug_check_constraint_rejects_invalid(tmp_path):
    """Slugs with path traversal characters must be rejected by CHECK constraint."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO sources (uid, slug, source_type, status, date_added) VALUES (?, ?, ?, ?, ?)",
            ("s1", "../../../etc", "youtube", "raw", "2026-01-01"),
        )
    conn.close()


def test_slug_check_constraint_accepts_valid(tmp_path):
    """Valid kebab-case slugs must be accepted."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    conn.execute(
        "INSERT INTO sources (uid, slug, source_type, status, date_added) VALUES (?, ?, ?, ?, ?)",
        ("s1", "valid-slug-123", "youtube", "raw", "2026-01-01"),
    )
    conn.commit()
    row = conn.execute("SELECT slug FROM sources WHERE uid = 's1'").fetchone()
    conn.close()
    assert row[0] == "valid-slug-123"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db_constraints.py -v
```

Expected: FAIL — foreign keys not enabled, no CHECK constraint

- [ ] **Step 3: Add PRAGMA foreign_keys to both connection functions**

In `infrastructure/db.py`, modify `get_vault_connection` (add after line 29):

```python
def get_vault_connection(db_path: Path) -> sqlite3.Connection:
    """vault.db — loads sqlite-vec, WAL mode, 5s busy timeout, foreign keys ON."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

Modify `get_system_connection` (add after line 38):

```python
def get_system_connection(db_path: Path) -> sqlite3.Connection:
    """.system.db — plain SQLite, WAL mode, 5s busy timeout, foreign keys ON."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

- [ ] **Step 4: Add CHECK constraint on slug in schema**

In `_SCHEMA_SQL`, modify the sources table (line 46):

```sql
    slug         TEXT UNIQUE NOT NULL CHECK(slug GLOB '[a-z0-9][a-z0-9-]*'),
```

And the notes table (line 62):

```sql
    slug                TEXT UNIQUE NOT NULL CHECK(slug GLOB '[a-z0-9][a-z0-9-]*'),
```

- [ ] **Step 5: Run constraint tests**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db_constraints.py -v
```

Expected: All PASS

- [ ] **Step 6: Run ALL tests to check for regressions**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: All PASS. If any tests insert slugs with uppercase or special chars, fix the test data.

- [ ] **Step 7: Commit**

```bash
git add infrastructure/db.py tests/infrastructure/test_db_constraints.py
git commit -m "fix: PRAGMA foreign_keys=ON + CHECK constraint slug kebab-case"
```

---

### Task 13: Rate limiting

**Files:**
- Modify: `api/main.py`
- Create: `tests/api/test_rate_limiting.py`

- [ ] **Step 1: Write rate limiting test**

```python
# tests/api/test_rate_limiting.py
"""Tests for API rate limiting."""

from fastapi.testclient import TestClient


def test_ingest_rate_limited(test_app_client):
    """Ingest endpoints should return 429 after exceeding rate limit."""
    client = test_app_client

    # Send 11 requests rapidly (limit is 10/min)
    responses = []
    for _ in range(11):
        resp = client.post("/ingest/youtube", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        responses.append(resp.status_code)

    # At least one should be 429
    assert 429 in responses, f"Expected 429 in responses, got: {set(responses)}"
```

Note: This test depends on having a `test_app_client` fixture. Check `tests/api/conftest.py` for the existing fixture name and adapt.

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/api/test_rate_limiting.py -v
```

Expected: FAIL — no 429 returned

- [ ] **Step 3: Add rate limiting middleware to api/main.py**

Add import at top:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
```

Add after `pyproject.toml` — first check if `slowapi` is in dependencies. If not, use a simpler approach with a custom middleware:

```python
# In create_app(), after the CORSMiddleware:

# Rate limiting — simple in-memory counter (local-only, no Redis needed)
from collections import defaultdict
import time as _time

_rate_limits: dict[str, tuple[int, int]] = {}  # prefix → (max_per_min, window_seconds)
_RATE_LIMITS = {
    "/ingest": 10,
    "/search": 30,
    "/benchmark": 2,
}
_DEFAULT_RATE = 60
_request_counts: dict[str, list[float]] = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    path = request.url.path
    now = _time.time()
    window = 60  # 1 minute

    # Find matching rate limit
    limit = _DEFAULT_RATE
    for prefix, max_req in _RATE_LIMITS.items():
        if path.startswith(prefix):
            limit = max_req
            break

    key = f"{request.client.host}:{path.split('/')[1] if '/' in path[1:] else path}"
    # Clean old entries
    _request_counts[key] = [t for t in _request_counts[key] if now - t < window]

    if len(_request_counts[key]) >= limit:
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})

    _request_counts[key].append(now)
    return await call_next(request)
```

Note: Review whether `slowapi` is already a dependency. If so, prefer it over the custom middleware. If not, the custom middleware avoids adding a new dependency.

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python -m pytest tests/api/test_rate_limiting.py -v
```

Expected: PASS

- [ ] **Step 5: Run all API tests**

```bash
.venv/Scripts/python -m pytest tests/api/ -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add api/main.py tests/api/test_rate_limiting.py
git commit -m "feat: API rate limiting — 10/min ingest, 30/min search, 60/min default"
```

---

### Task 14: Upload size limits

**Files:**
- Modify: `api/routers/ingest.py`

- [ ] **Step 1: Write test for upload size limit**

Add to `tests/api/test_ingest.py`:

```python
def test_audio_upload_too_large_returns_413(test_app_client):
    """Uploads exceeding size limit should return 413."""
    # Create a fake file just over the limit header
    import io
    # We test via Content-Length header, not actual bytes
    client = test_app_client
    # The actual check is on Content-Length or file size after read
    large_content = b"x" * (500 * 1024 * 1024 + 1)  # 500MB + 1 byte
    resp = client.post(
        "/ingest/audio",
        files={"file": ("test.mp3", io.BytesIO(large_content), "audio/mpeg")},
    )
    assert resp.status_code == 413
```

Note: This test may be slow due to large payload. Consider a smaller limit for testing or mocking the size check.

- [ ] **Step 2: Add size validation to ingest endpoints**

In `api/routers/ingest.py`, add after the extension check in both audio and pdf endpoints:

```python
_MAX_AUDIO_BYTES = 500 * 1024 * 1024  # 500 MB
_MAX_PDF_BYTES = 100 * 1024 * 1024    # 100 MB
```

In `ingest_audio_endpoint`, after `suffix` check:

```python
    content = await file.read()
    if len(content) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 500 MB)")
    # ... then write content instead of file.read()
    dest.write_bytes(content)
```

Same pattern for `ingest_pdf_endpoint` with `_MAX_PDF_BYTES`.

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/api/test_ingest.py -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add api/routers/ingest.py tests/api/test_ingest.py
git commit -m "feat: limite taille upload — 500MB audio, 100MB PDF"
```

---

### Task 15: File permissions on DB creation

**Files:**
- Modify: `core/security.py` (add `set_restrictive_permissions`)
- Modify: `infrastructure/db.py` (apply after DB creation)
- Modify: `scripts/setup/init_user_dir.py` (apply on created directories)

- [ ] **Step 1: Write test for permissions**

Add to `tests/core/test_security.py`:

```python
import sys
import os
import stat

from core.security import set_restrictive_permissions


class TestSetRestrictivePermissions:
    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not effective on Windows")
    def test_sets_0600_on_file(self, tmp_path):
        f = tmp_path / "test.db"
        f.touch()
        set_restrictive_permissions(f)
        mode = stat.S_IMODE(os.stat(f).st_mode)
        assert mode == 0o600

    def test_does_not_crash_on_windows(self, tmp_path):
        """On Windows, the function should be a no-op (no crash)."""
        f = tmp_path / "test.db"
        f.touch()
        set_restrictive_permissions(f)  # Should not raise
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/core/test_security.py::TestSetRestrictivePermissions -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Add set_restrictive_permissions to core/security.py**

Append to `core/security.py`:

```python
def set_restrictive_permissions(path: Path) -> None:
    """
    Set file permissions to owner-only read/write (0600) on Unix.
    No-op on Windows (relies on user profile directory placement).
    """
    if sys.platform == "win32":
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # Best effort — don't crash if permissions can't be set
```

- [ ] **Step 4: Apply in infrastructure/db.py after DB creation**

In `init_db()` (after line 174 `conn.close()`):

```python
def init_db(db_path: Path) -> None:
    conn = get_vault_connection(db_path)
    conn.executescript(_SCHEMA_SQL)
    conn.executescript(_METADATA_SQL)
    conn.commit()
    conn.close()
    from core.security import set_restrictive_permissions
    set_restrictive_permissions(db_path)
```

In `init_system_db()` (after line 161 `conn.close()`):

```python
def init_system_db(db_path: Path) -> None:
    conn = get_system_connection(db_path)
    conn.executescript(_SYSTEM_SCHEMA_SQL)
    conn.commit()
    conn.close()
    from core.security import set_restrictive_permissions
    set_restrictive_permissions(db_path)
```

- [ ] **Step 5: Run tests**

```bash
.venv/Scripts/python -m pytest tests/core/test_security.py::TestSetRestrictivePermissions tests/infrastructure/ -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add core/security.py infrastructure/db.py
git commit -m "fix: restrictive permissions (0600) on vault.db and .system.db after creation"
```

---

### Task 16: Provider error sanitization

**Files:**
- Modify: `infrastructure/llm_provider.py:70-107`
- Modify: `infrastructure/embedding_provider.py:22-30`

- [ ] **Step 1: Write test for LLM provider error sanitization**

Add to `tests/infrastructure/test_llm_provider.py` (or create):

```python
def test_anthropic_auth_error_does_not_leak_key(monkeypatch):
    """Auth errors from Anthropic SDK must not contain the API key."""
    import anthropic
    from infrastructure.llm_provider import _generate_anthropic
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.install.providers.anthropic_api_key = "sk-ant-api03-realkey123456789012345678901234567890"
    settings.system.llm.max_retries = 0
    settings.user.llm.model = "claude-sonnet-4-6"

    # Simulate an auth error that includes the key
    def mock_create(**kwargs):
        raise anthropic.AuthenticationError(
            message=f"Invalid API key: sk-ant-api03-realkey123456789012345678901234567890",
            response=MagicMock(status_code=401),
            body=None,
        )

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: MagicMock(messages=MagicMock(create=mock_create)))

    with pytest.raises(Exception) as exc_info:
        _generate_anthropic("test", {}, "standard", settings)

    error_msg = str(exc_info.value)
    assert "sk-ant-api03-realkey" not in error_msg
```

- [ ] **Step 2: Modify infrastructure/llm_provider.py to catch and sanitize**

Wrap the `client.messages.create` call in `_generate_anthropic`:

```python
def _generate_anthropic(
    source_content: str,
    source_metadata: dict,
    template_name: str,
    settings: Settings,
) -> NoteContentInput:
    import anthropic

    template = _load_template(template_name)
    api_key = settings.install.providers.anthropic_api_key
    client = anthropic.Anthropic(api_key=api_key)
    max_retries = settings.system.llm.max_retries
    user_message = _build_user_message(source_content, source_metadata, template)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        error_context = (
            f"\n\nPrevious attempt failed with: {last_error}. "
            "Fix the JSON and try again."
            if last_error else ""
        )
        try:
            message = client.messages.create(
                model=settings.user.llm.model,
                max_tokens=4096,
                system=template["system_prompt"] + error_context,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e:
            from core.sanitize import sanitize_error
            raise RuntimeError(sanitize_error(e)) from None

        raw = message.content[0].text
        try:
            data = json.loads(raw)
            return NoteContentInput(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e

    raise ValueError(
        f"LLM failed to produce valid NoteContentInput after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )
```

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/ -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add infrastructure/llm_provider.py infrastructure/embedding_provider.py
git commit -m "fix: sanitize provider errors — API keys never exposed in exceptions"
```

---

### Task 17: Final verification

**Files:** None — verification only.

- [ ] **Step 1: Run the full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: All PASS (205+ tests)

- [ ] **Step 2: Verify Phase 1 checklist**

```bash
echo "=== Phase 1 Checklist ==="
test -s SECURITY.md && echo "OK: SECURITY.md filled" || echo "FAIL: SECURITY.md empty"
test -s CONTRIBUTING.md && echo "OK: CONTRIBUTING.md filled" || echo "FAIL: CONTRIBUTING.md empty"
grep -q "Steps to Reproduce" .github/ISSUE_TEMPLATE/bug_report.md && echo "OK: bug_report template" || echo "FAIL: bug_report template"
grep -q "Motivation" .github/ISSUE_TEMPLATE/feature_request.md && echo "OK: feature_request template" || echo "FAIL: feature_request template"
grep -q "Security Model" docs/architecture/ARCHITECTURE.md && echo "OK: ARCHITECTURE.md has Security Model" || echo "FAIL: no Security Model"
grep -q ".env" .gitignore && echo "OK: .env in .gitignore" || echo "FAIL: .env not in .gitignore"
```

- [ ] **Step 3: Verify Phase 2 checklist**

```bash
echo "=== Phase 2 Checklist ==="
.venv/Scripts/python -c "from core.sanitize import redact_sensitive; print('OK: sanitize module')"
.venv/Scripts/python -c "from core.security import validate_youtube_url, validate_file_path, set_restrictive_permissions; print('OK: security module')"
grep -q "PRAGMA foreign_keys" infrastructure/db.py && echo "OK: foreign_keys pragma" || echo "FAIL"
grep -q "CHECK(slug" infrastructure/db.py && echo "OK: slug CHECK constraint" || echo "FAIL"
grep -q "redact_sensitive" core/logging.py && echo "OK: log redaction" || echo "FAIL"
grep -q "rate_limit\|RateLimit\|_request_counts" api/main.py && echo "OK: rate limiting" || echo "FAIL"
```

- [ ] **Step 4: Final commit if any remaining changes**

```bash
git status
# If clean, done. If changes, commit appropriately.
```
