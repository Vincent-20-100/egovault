# EgoVault — Project Audit Specification

**Date:** 2026-03-31
**Version:** 1.0
**Purpose:** Reusable, agent-executable audit method for the EgoVault project.
**Output:** `audit-results-YYYY-MM-DD.md` with dated findings.

> This spec defines **what to check and how**. It does not contain results.
> Run this audit at every milestone, before any major implementation phase.

---

## How to use this spec

1. Read each audit domain (sections 1–8) in order
2. For each check, scan the listed files/directories
3. Record every violation in the results file with: file, line, severity, description, fix
4. Severity levels: **CRITICAL** (blocks launch), **MAJOR** (must fix before next milestone), **MINOR** (fix when convenient)
5. At the end, produce a summary table with counts per domain and severity

---

## 1. Spec coherence — are specs consistent with each other?

### What to check

| # | Check | Where to look | Violation criteria |
|---|-------|---------------|-------------------|
| 1.1 | No contradictions between specs | `docs/superpowers/specs/*.md` | Two specs describe the same thing differently |
| 1.2 | Superseded specs are marked OBSOLETE | `docs/superpowers/specs/*.md` | A superseded spec has no OBSOLETE marker |
| 1.3 | CLAUDE.md progress section matches reality | `CLAUDE.md` §Progress | A feature listed as "done" has no code, or code exists but isn't listed |
| 1.4 | Roadmap in CLAUDE.md matches spec priorities | `CLAUDE.md` §Roadmap | Roadmap order contradicts latest spec decisions |
| 1.5 | Future work items are documented | `docs/FUTURE-WORK.md`, spec §Future work | A discussed future feature has no written trace |
| 1.6 | Plans reference correct spec versions | `docs/superpowers/plans/*.md` | A plan references an obsolete spec |

### How to check

- Read all spec headers (Date, Status, Supersedes)
- Cross-reference CLAUDE.md progress with actual file existence
- Search for contradictory statements about the same concept across specs

---

## 2. Architecture conformance — does code respect G4?

### What to check

| # | Check | Where to look | Violation criteria |
|---|-------|---------------|-------------------|
| 2.1 | `core/` imports nothing from project | `core/*.py` | Any `from tools/workflows/infrastructure/mcp/api import` |
| 2.2 | `tools/` imports only `core/` | `tools/**/*.py` | Any `from workflows/mcp/api import` |
| 2.3 | No tool imports another tool | `tools/**/*.py` | Any `from tools.X import` inside a tool file |
| 2.4 | `workflows/` imports only `tools/` and `core/` | `workflows/*.py` | Any `from infrastructure/mcp/api import` |
| 2.5 | `infrastructure/` imports only `core/` | `infrastructure/*.py` | Any `from tools/workflows/mcp/api import` |
| 2.6 | `mcp/server.py` has zero business logic | `mcp/server.py` | Loops, conditionals, data transforms beyond routing |
| 2.7 | `api/` routers have zero business logic | `api/routers/*.py` | Business logic beyond routing and validation |
| 2.8 | New Pydantic models are in `core/schemas.py` | All `*.py` | Pydantic BaseModel subclass outside `core/` (except API request models) |

### How to check

- For each layer, grep all `import` and `from ... import` statements
- Verify each import targets only allowed layers
- For MCP/API: read each function body, flag anything beyond delegation

---

## 3. Guardrails G1–G12 compliance

### G1 — No implementation details in public strings

| Where | What to grep |
|-------|-------------|
| `mcp/server.py` docstrings | Library names: `faster-whisper`, `whisper`, `ollama`, `nomic`, `pypdf`, `sqlite-vec`, `yt-dlp`, `beautifulsoup`, `bs4`, `opus` (codec) |
| `api/routers/*.py` descriptions | Same library names |
| `cli/commands/*.py` help text | Same library names |
| `core/errors.py` user messages | Same library names + stack traces, file paths |
| `docs/mcp-setup.md` | Library names in tool descriptions |

### G2 — Describe WHAT not HOW

| Where | Violation |
|-------|-----------|
| All docstrings in `tools/`, `mcp/`, `api/` | Mentions algorithm parameters, window sizes, thresholds, similarity metrics |

### G3 — Config-driven

| Where | What to grep |
|-------|-------------|
| All `*.py` except `config/` and `tests/` | Hardcoded numbers that should be config: `768`, `800`, `200`, `500`, `30`, `10`, `0.7`, `0.8` |
| All `*.py` | Hardcoded model names: `nomic-embed-text`, `llama`, `gpt-`, `claude-` |
| All `*.py` | Hardcoded paths: `/data/`, `vault.db`, `.system.db` (outside config loading) |

### G4 — Architecture (covered in section 2)

### G5 — No over-engineering

| Where | Violation |
|-------|-----------|
| All `*.py` | Abstract base classes with single implementation |
| All `*.py` | Helper functions called exactly once |
| All `*.py` | Feature flags or compat shims |

### G6 — Error handling

| Where | What to check |
|-------|---------------|
| All `*.py` | Bare `except:` or `except Exception: pass` |
| All `*.py` | `print()` instead of `logger.X()` |
| All `*.py` | User-facing error messages with internal details |

### G7 — Language and naming

| Where | What to check |
|-------|---------------|
| All `*.py` comments, variable names | Non-English code comments or identifiers |
| `core/schemas.py`, config | Glossary terms: `document` vs `note`, `file` vs `source`, `vector` vs `embedding` |

### G8 — Test discipline

| Where | What to check |
|-------|---------------|
| `tools/**/*.py` vs `tests/tools/**/*.py` | Every tool has a corresponding test file |
| `workflows/*.py` vs `tests/workflows/*.py` | Every workflow has a corresponding test file |
| `api/routers/*.py` vs `tests/api/*.py` | Every router has corresponding tests |

### G9 — Pydantic at boundaries

| Where | What to check |
|-------|---------------|
| `mcp/server.py` tool functions | Input/output uses Pydantic models or primitive types (not raw dicts) |
| `api/routers/*.py` | Request/response bodies are Pydantic models |
| `tools/**/*.py` public functions | Return types are Pydantic models or primitives |

### G10 — Security

| Where | What to check |
|-------|---------------|
| All `*.py` | `logger.info()` or `logger.warning()` with user content, URLs, or API keys |
| `infrastructure/db.py`, `tools/vault/*.py` | String formatting in SQL (f-strings, .format) vs parameterized queries |
| All `*.py` | `eval()`, `exec()`, `__import__()` |
| All `*.py` | File operations without path validation |

### G11 — MCP is routing only

| Where | What to check |
|-------|---------------|
| `mcp/server.py` | Any function body longer than ~10 lines (routing should be short) |
| `mcp/server.py` | Manual dict construction instead of `model.model_dump(mode="json")` |

### G12 — No duplicated documentation

| Where | What to check |
|-------|---------------|
| Docstrings vs `system.yaml` | Docstring repeats a config value (chunk size, threshold, etc.) |
| Docstrings vs `ARCHITECTURE.md` | Docstring repeats architecture description |
| Multiple specs | Same decision documented in two places with different wording |

---

## 4. Implementation vs spec — is the code up to date?

### What to check

| # | Check | How |
|---|-------|-----|
| 4.1 | All "DONE" features in CLAUDE.md have working code | For each done item, verify the files exist and contain the described functionality |
| 4.2 | All schemas in `core/schemas.py` match spec | Compare schemas to latest specs |
| 4.3 | All config in `system.yaml` matches spec | Compare config keys to what specs describe |
| 4.4 | All MCP tools match spec | Compare `mcp/server.py` tools to spec tool lists |
| 4.5 | All API endpoints match spec | Compare `api/routers/*.py` to spec endpoint lists |
| 4.6 | All CLI commands match spec | Compare `cli/commands/*.py` to spec command lists |
| 4.7 | DB schema matches spec | Compare `infrastructure/db.py` to `docs/architecture/DATABASES.md` |

---

## 5. Documentation accuracy — is the doc up to date?

### What to check

| # | Check | Where |
|---|-------|-------|
| 5.1 | `ARCHITECTURE.md` structure section matches actual file tree | Compare §Structure to `ls -R` |
| 5.2 | `ARCHITECTURE.md` database section matches `db.py` schema | Compare table definitions |
| 5.3 | `ARCHITECTURE.md` config section matches `system.yaml` | Compare documented keys to actual keys |
| 5.4 | `DATABASES.md` matches actual schema | Compare to `_SCHEMA_SQL` in `db.py` |
| 5.5 | `CONTRACTS.md` (if exists) matches actual function signatures | Compare to code |
| 5.6 | `CLAUDE.md` commands section works | Try each listed command mentally |
| 5.7 | `docs/mcp-setup.md` tool list matches `mcp/server.py` | Compare tool names and descriptions |

---

## 6. Config integrity

### What to check

| # | Check | How |
|---|-------|-----|
| 6.1 | Every key in `system.yaml` is consumed by code | Grep each key in `*.py` |
| 6.2 | Every config access in code has a corresponding `system.yaml` key | Grep `settings.system.X` patterns, verify key exists |
| 6.3 | `core/config.py` Pydantic models match `system.yaml` structure | Compare field names and types |
| 6.4 | Default values in Pydantic match `system.yaml` defaults | Compare explicitly |
| 6.5 | Taxonomy values (`source_types`, `note_types`) used in code match config | Grep for string literals that should be taxonomy values |

---

## 7. Test health

### What to check

| # | Check | How |
|---|-------|-----|
| 7.1 | All tests pass | `python -m pytest tests/ -x` |
| 7.2 | No tests depend on external services | Grep for real URLs, API calls, network access in tests |
| 7.3 | Test fixtures match production patterns | Compare `tests/conftest.py` config to real config structure |
| 7.4 | Coverage gaps | List all tool/workflow files without corresponding test files |
| 7.5 | Pre-existing failures documented | Known failures listed with reason |

---

## 8. Security review

### What to check

| # | Check | How |
|---|-------|-----|
| 8.1 | No secrets in repo | Grep for `api_key`, `secret`, `password`, `token` in non-test code |
| 8.2 | `.gitignore` covers sensitive files | Verify `user.yaml`, `install.yaml`, `*.db`, `egovault-user/` are ignored |
| 8.3 | SQL injection surface | Grep for f-string SQL in `infrastructure/`, `tools/vault/` |
| 8.4 | Path traversal surface | File operations with user-supplied paths |
| 8.5 | Dependency audit | Check `requirements.txt` / `pyproject.toml` for known-vulnerable versions |
| 8.6 | Permission model | Verify `set_restrictive_permissions` is called on DB files |
| 8.7 | `allow_destructive_ops` gate | Verify delete operations check the gate |

---

## Results format

Each finding should be recorded as:

```markdown
### [DOMAIN]-[NUMBER] — [SHORT TITLE]

- **Severity:** CRITICAL | MAJOR | MINOR
- **File:** `path/to/file.py:line`
- **Violation:** What rule is broken
- **Description:** What's wrong
- **Fix:** How to fix it
```

Summary table at the end:

```markdown
| Domain | Critical | Major | Minor | Total |
|--------|----------|-------|-------|-------|
| 1. Spec coherence | | | | |
| 2. Architecture | | | | |
| 3. Guardrails | | | | |
| 4. Implementation | | | | |
| 5. Documentation | | | | |
| 6. Config | | | | |
| 7. Tests | | | | |
| 8. Security | | | | |
| **Total** | | | | |
```
