# EgoVault — Project Audit Specification (.meta/AUDIT-SPEC.md)

**Status:** LIVING STANDARD — The canonical quality audit specification for EgoVault.  
**Referenced From:** `AGENTS.md`, `CLAUDE.md`, `.meta/WORKFLOW.md`  
**Output:** `.meta/audits/audit-results-YYYY-MM-DD.md`

> This specification defines the exact 8-domain inspection protocol to execute before shipping any major phase or milestone.

---

## 1. Audit Domains

### Domain 1: Spec & Vision Coherence
- **Check 1.1:** No contradictions between active specs in `.meta/specs/` and `docs/VISION-KNOWLEDGE-COMPILER.md`.
- **Check 1.2:** All superseded specs are marked OBSOLETE and archived in `.meta/archive/specs/`.
- **Check 1.3:** `PROJECT-STATUS.md` and `SESSION-CONTEXT.md` match current repository state.
- **Check 1.4:** Active plans in `.meta/plans/` map 1-to-1 to active specifications without scope deviation.

### Domain 2: Hexagonal Architecture Conformance (Rule G4)
- **Check 2.1:** `core/` has **zero imports** from other project packages (`tools`, `workflows`, `infrastructure`, `mcp`, `api`, `cli`).
- **Check 2.2:** `tools/` import only `core/`. **No tool imports another tool.**
- **Check 2.3:** Tools receive all dependencies strictly through [`VaultContext`](../core/context.py).
- **Check 2.4:** `workflows/` import only `tools/` and `core/`.
- **Check 2.5:** `infrastructure/` concrete providers import `core/` only.
- **Check 2.6:** `mcp/server.py`, `api/routers/`, and `cli/commands/` are thin routing layers containing **zero business logic**.

### Domain 3: Guardrails & Zero-Hardcode Policy (Rules G1, G2, G3)
- **Check 3.1 (G1):** No internal library names (`faster-whisper`, `sqlite-vec`, `pypdf`, `rapidocr`, `ollama`) in public-facing strings (MCP docstrings, API descriptions, CLI help, user error messages).
- **Check 3.2 (G2):** Docstrings describe WHAT (functional capability), never HOW (internal mechanics or thresholds).
- **Check 3.3 (G3 - Zero-Hardcode):** Zero magic numbers or hardcoded algorithm parameters in `tools/`, `infrastructure/`, `workflows/`. Every tunable parameter is loaded from `ctx.settings`.

### Domain 4: Implementation vs Spec Contract
- **Check 4.1:** All Pydantic models in `core/schemas.py` strictly match active specifications.
- **Check 4.2:** Topic segmentation adheres to plateau-aware TextTiling with strict precedence merging.
- **Check 4.3:** Multi-agent candidate locks are atomic and enforce parameterized UTC expirations (`ExpiredLockError`).
- **Check 4.4:** SQLite schema in `infrastructure/db.py` matches `docs/architecture/DATABASES.md`.

### Domain 5: Documentation & User Guide Accuracy (Rule G12)
- **Check 5.1:** `docs/architecture/ARCHITECTURE.md` accurately reflects the file tree, pipeline, and cognitive tiers.
- **Check 5.2:** `docs/architecture/DATABASES.md` matches `_SCHEMA_SQL` in `infrastructure/db.py`.
- **Check 5.3:** `docs/user-guide/` (12 chapters) is synchronized with all user-visible capabilities (new config keys, CLI commands, MCP tools).

### Domain 6: Configuration Integrity & Error Architecture V2 (Rule G6)
- **Check 6.1:** `config/system.yaml`, `config/user.yaml.example`, and `config/install.yaml.example` are comprehensive and match `core/config.py` models.
- **Check 6.2:** All exceptions inherit from `EgoVaultError` with mandatory `error_code`, `user_message`, `actionable_hint`, and `http_status`.
- **Check 6.3:** No bare `except:` blocks or swallowed exceptions. `core/sanitize.py` redacts secrets without destroying error diagnostic value.

### Domain 7: Test Suite Health (Rule G8)
- **Check 7.1:** Full pytest suite passes 100% deterministically (`uv run pytest` $\to$ 0 failures).
- **Check 7.2:** No tests make unauthorized network requests or rely on unmocked external providers.
- **Check 7.3:** Every new tool or workflow has a corresponding test file in `tests/` mirroring source structure.

### Domain 8: Security & Confinement (Rule G10)
- **Check 8.1:** Strict file path validation against allowed directories before any disk read/write (`core/security.py`).
- **Check 8.2:** SSRF protection on all web URLs (blocking internal/private IPs and cloud metadata endpoints).
- **Check 8.3:** Parameterized SQL queries exclusively (`?` placeholders, zero f-string formatting in SQL).
- **Check 8.4:** Sensitive files (`user.yaml`, `install.yaml`, `*.db`, `egovault-user/`) are ignored by `.gitignore`.

---

## 2. Audit Findings Output Format

Audit results must be written to `.meta/audits/audit-results-YYYY-MM-DD.md` in the following structure:

```markdown
# EgoVault — Audit Results [YYYY-MM-DD]

## Summary
- **Critical (Blockers):** X
- **Major (Pre-Ship):** Y
- **Minor (Polish):** Z

## Findings by Domain

### [DOMAIN]-[INDEX] — [TITLE]
- **Severity:** CRITICAL | MAJOR | MINOR
- **File:** `path/to/file.py:line`
- **Violation:** Description of broken rule
- **Description:** Context and impact
- **Fix:** Concrete code/doc remedy
```
