# EgoVault — Audit Results 2026-03-31

**Audit spec:** `.meta/specs/2026-03-31-project-audit-spec.md`
**Executed by:** 4 parallel agents (Explore type)
**Scope:** Full project — 8 domains, ~50 checks

---

## Summary

| Domain | Critical | Major | Minor | Total |
|--------|----------|-------|-------|-------|
| 1. Spec coherence | 0 | 1 | 3 | 4 |
| 2. Architecture G4 | 4 | 17 | 1 | 22 |
| 3. Guardrails G1-G12 | 0 | 7 | 6 | 13 |
| 4. Implementation vs spec | 0 | 0 | 0 | 0 |
| 5. Documentation accuracy | 0 | 4 | 2 | 6 |
| 6. Config integrity | 0 | 0 | 0 | 0 |
| 7. Test health | 0 | 1 | 0 | 1 |
| 8. Security | 0 | 0 | 1 | 1 |
| **Total** | **4** | **30** | **13** | **47** |

**Verdict:** Implementation (4), config (6), and security (8) are clean. The main debt is
architectural (domain 2) — tools/ importing infrastructure/ — which is known and accepted
but never formally documented. Documentation (5) lags behind implementation.

---

## Domain 1 — Spec coherence

### 1-1 — API router count mismatch in CLAUDE.md
- **Severity:** MINOR
- **File:** `CLAUDE.md:333`
- **Violation:** 1.3 — CLAUDE.md claims "6 routers" but 7 exist (vault.py undocumented)
- **Fix:** Update CLAUDE.md to list all 7 routers

### 1-2 — ARCHITECTURE.md references unimplemented files
- **Severity:** MAJOR
- **File:** `docs/architecture/ARCHITECTURE.md:144-145`
- **Violation:** 1.3 — `reranker_provider.py`, `semantic_cache.py`, `monitoring.py`, `benchmark.py` marked [SPEC READY] but don't exist
- **Fix:** Change to [FUTURE] or move to a "Planned" subsection

### 1-3 — Future work items not in FUTURE-WORK.md
- **Severity:** MINOR
- **File:** `docs/FUTURE-WORK.md`
- **Violation:** 1.5 — Crash recovery checkpoints, tiered web extraction, structured data family not listed
- **Fix:** Sync FUTURE-WORK.md with latest spec discussion notes

### 1-4 — OBSOLETE markers inconsistent format
- **Severity:** MINOR
- **File:** `.meta/specs/2026-03-31-extraction-provider-design.md`, `2026-03-31-ingest-text-web-design.md`
- **Violation:** 1.2 — Superseded specs use strikethrough instead of formal `Status: OBSOLETE`
- **Fix:** Standardize OBSOLETE marker format

---

## Domain 2 — Architecture conformance (G4)

> **Context:** CLAUDE.md acknowledges "Some tools currently import infrastructure/ directly
> (via late imports). This is tracked and accepted for now." However, this debt was never
> formally listed. The violations below are real but expected.

### 2-1 — core/ imports infrastructure (CRITICAL)
- **Severity:** CRITICAL
- **File:** `core/logging.py:53-55`
- **Violation:** 2.1 — core/ must NOT import from infrastructure/
- **Description:** `_write_log()` dynamically imports `infrastructure.db`
- **Fix:** Callback/registration pattern: infrastructure registers the log handler, core doesn't import it

### 2-2 — Tool imports another tool (CRITICAL)
- **Severity:** CRITICAL
- **File:** `tools/media/fetch_subtitles.py:14`
- **Violation:** 2.3 — `from tools.media.transcribe import transcribe`
- **Fix:** Extract shared transcription logic or have the workflow orchestrate both tools

### 2-3 — MCP server imports infrastructure at top level (CRITICAL)
- **Severity:** CRITICAL
- **File:** `mcp/server.py:27-30`
- **Violation:** 2.5 — Top-level imports from `infrastructure.db`
- **Fix:** Move infrastructure access to tools/ or wrap in tool functions

### 2-4 — MCP server has business logic (CRITICAL)
- **Severity:** CRITICAL
- **File:** `mcp/server.py:254-298`
- **Violation:** 2.6 — `create_note` contains 45 lines of business logic (DB queries, UID gen, slug creation)
- **Fix:** Move all logic to `tools/vault/create_note.py`, MCP calls tool only

### 2-5 through 2-14 — Tools import infrastructure (MAJOR x10)
- **Severity:** MAJOR (each)
- **Files:**
  - `tools/text/embed_note.py:22-26`
  - `tools/text/embed.py`
  - `tools/export/typst.py`
  - `tools/export/mermaid.py`
  - `tools/vault/create_note.py`
  - `tools/vault/generate_note_from_source.py:38-48`
  - `tools/vault/search.py`
  - `tools/vault/delete_source.py`
  - `tools/vault/restore_note.py`
  - `tools/vault/restore_source.py`
  - `tools/vault/update_note.py`
  - `tools/vault/finalize_source.py`
- **Violation:** 2.2 — tools/ imports infrastructure/ via late imports
- **Status:** Known technical debt, accepted. Formal documentation needed.

### 2-15 through 2-17 — Workflows import infrastructure (MAJOR x3)
- **Severity:** MAJOR (each)
- **Files:** `workflows/ingest_audio.py:19-27`, `workflows/ingest_youtube.py:7-15`, `workflows/ingest_pdf.py:7-15`
- **Violation:** 2.4 — workflows/ imports infrastructure.db directly
- **Fix:** Will be addressed by unified workflow refactor

### 2-18 — API router has business logic (MAJOR)
- **Severity:** MAJOR
- **File:** `api/routers/ingest.py:56-127`
- **Violation:** 2.7 — File validation, size checking, directory creation, file writing in router
- **Fix:** Move to infrastructure/ upload handler or tools/

### 2-19 — API notes approve has conditional logic (MINOR)
- **Severity:** MINOR
- **File:** `api/routers/notes.py:75-99`
- **Violation:** 2.7 — Approve endpoint has business logic for source finalization
- **Fix:** Create `tools/vault/approve_note.py`

---

## Domain 3 — Guardrails G1-G12

### G1-001 — Library names in docs/mcp-setup.md
- **Severity:** MINOR
- **File:** `docs/mcp-setup.md:9`
- **Violation:** G1 — "nomic-embed-text", "ollama serve" in user-facing doc
- **Fix:** Use generic: "configured embedding model"

### G1-002 — Library names in health endpoint
- **Severity:** MINOR
- **File:** `api/routers/health.py:31,35`
- **Violation:** G1 — Response has `"ollama": "up"` key
- **Fix:** Use `"embedding_provider": "ok"` instead

### G6-001 — Silent exception in health checks
- **Severity:** MAJOR
- **File:** `api/routers/health.py:13,24`
- **Violation:** G6 — `except Exception: return False` without logging
- **Fix:** Add `logger.debug("Health check failed: %s", e)`

### G6-002 — Silent exception in note deletion cascade
- **Severity:** MAJOR
- **File:** `api/routers/notes.py:131-132`
- **Violation:** G6 — `except Exception: pass` on source deletion
- **Fix:** Add debug logging

### G6-003 — Silent exception in subtitle fallback
- **Severity:** MAJOR
- **File:** `tools/media/fetch_subtitles.py:56`
- **Violation:** G6 — Silent fallback to transcription without logging why
- **Fix:** Add `logger.debug("Subtitle fetch failed, falling back: %s", e)`

### G6-004 — Silent exception in logging
- **Severity:** MINOR
- **File:** `core/logging.py:69`
- **Violation:** G6 — `except Exception: pass` in logging code
- **Fix:** `sys.stderr.write()` as last resort

### G6-005 — Broad exception in MCP module loading
- **Severity:** MINOR
- **File:** `mcp/server.py:47,66`
- **Violation:** G6 — `except Exception:` instead of specific exceptions
- **Fix:** Use `except (OSError, ValueError):` and `except ModuleNotFoundError:`

### G10-001 — f-string SQL field names
- **Severity:** MAJOR
- **File:** `infrastructure/db.py:317`
- **Violation:** G10 — f-string SQL with field names (allowlisted, but pattern is fragile)
- **Fix:** Acceptable with allowlist, but add comment explaining safety

### G10-002 — f-string SQL WHERE clause construction
- **Severity:** MAJOR
- **File:** `infrastructure/db.py:525-526`
- **Violation:** G10 — f-string WHERE clause construction
- **Fix:** Acceptable with parameterized values, but add safety comment

### G11-001 — MCP create_note business logic (duplicate of 2-4)
- **Severity:** MAJOR
- **File:** `mcp/server.py:254-298`
- **Violation:** G11 — 45-line function with DB access
- **Fix:** See 2-4

### G11-002 — MCP direct database access (duplicate of 2-3)
- **Severity:** MAJOR
- **File:** `mcp/server.py:284-287`
- **Violation:** G11 — Direct SELECT query in MCP
- **Fix:** See 2-3

### G12-001 — Docstring references config location
- **Severity:** MINOR
- **File:** `mcp/server.py:99`
- **Violation:** G12 — Docstring says "per system.yaml:chunking config"
- **Fix:** Focus on WHAT: "Split text into overlapping chunks."

### G12-002 — Duplicate default model name
- **Severity:** MINOR
- **File:** `core/config.py:49,66`
- **Violation:** G12 — `nomic-embed-text` repeated in EmbeddingConfig and EmbeddingUserConfig
- **Fix:** Define `DEFAULT_EMBEDDING_MODEL` constant

---

## Domain 4 — Implementation vs spec

**PASSED** — All features marked "DONE" have working code. Schemas, config, MCP tools,
API endpoints, and CLI commands all match specs.

---

## Domain 5 — Documentation accuracy

### 5-1 — ARCHITECTURE.md structure lists non-existent files
- **Severity:** MAJOR
- **File:** `docs/architecture/ARCHITECTURE.md:140-157`
- **Violation:** 5.1 — reranker_provider.py, semantic_cache.py, monitoring.py, benchmark.py don't exist. vault.py router undocumented.
- **Fix:** Update to actual state, move unimplemented to [FUTURE]

### 5-2 — DATABASES.md missing columns
- **Severity:** MAJOR
- **File:** `docs/architecture/DATABASES.md:48-62`
- **Violation:** 5.2 — Missing `previous_status`, `previous_sync_status`, `status` columns added by A3/A4
- **Fix:** Update table definitions

### 5-3 — ARCHITECTURE.md config section describes unimplemented features
- **Severity:** MAJOR
- **File:** `docs/architecture/ARCHITECTURE.md:245-333`
- **Violation:** 5.3 — Reranking, semantic cache, benchmark config sections described as if implemented
- **Fix:** Move to [FUTURE] subsection

### 5-4 — mcp-setup.md missing tool reference
- **Severity:** MAJOR
- **File:** `docs/mcp-setup.md`
- **Violation:** 5.7 — No tool list. 25 MCP tools exist but aren't enumerated.
- **Fix:** Add "Tools reference" section

### 5-5 — system.yaml missing `texte` source type
- **Severity:** MINOR
- **File:** `config/system.yaml:42-49`
- **Violation:** 5.3 — Spec says add `texte`, not yet done (expected — not yet implemented)
- **Fix:** Add when implementing ingest_text

### 5-6 — ARCHITECTURE.md config describes unimplemented reranking
- **Severity:** MAJOR
- **File:** `docs/architecture/ARCHITECTURE.md:268-282`
- **Violation:** 5.3 — Reranking config described as if working, but no code exists
- **Fix:** Duplicate of 5-3, same fix

---

## Domain 6 — Config integrity

**PASSED** — All keys consumed, Pydantic matches YAML, defaults consistent, taxonomy correct.

---

## Domain 7 — Test health

### 7-1 — Missing test files for 2 tools
- **Severity:** MAJOR
- **File:** `tools/media/extract_audio.py`, `tools/text/summarize.py`
- **Violation:** G8 — No corresponding test files. Both tools appear unused.
- **Fix:** Add tests or remove if unused

---

## Domain 8 — Security

### 8-1 — Library name leaked in transcribe docstring
- **Severity:** MINOR
- **File:** `tools/media/transcribe.py:16`
- **Violation:** G1 — Docstring says "using faster-whisper"
- **Fix:** Change to "using the configured transcription engine"

---

## Action plan — prioritized

### Immediate fixes (before next implementation phase)

**Documentation sync (5 items, low risk):**
1. Update ARCHITECTURE.md: mark unimplemented features as [FUTURE] (1-2, 5-1, 5-3, 5-6)
2. Update DATABASES.md: add missing columns (5-2)
3. Update CLAUDE.md: fix router count (1-1)
4. Sync FUTURE-WORK.md with new spec decisions (1-3)
5. Add tool reference to mcp-setup.md (5-4)

**Guardrail quick fixes (7 items, low risk):**
1. Add debug logging to silent exceptions (G6-001, G6-002, G6-003, G6-004)
2. Narrow exception types in MCP (G6-005)
3. Fix library name leaks (G1-001, G1-002, 8-1)
4. Fix health endpoint response keys (G1-002)
5. Add safety comments to SQL patterns (G10-001, G10-002)
6. Fix docstring config reference (G12-001)
7. Extract duplicate default constant (G12-002)

**Test gap (1 item):**
1. Decide: add tests for extract_audio.py and summarize.py, or remove if unused (7-1)

### Deferred to unified workflow refactor

**Architecture debt (22 items):**
- tools/ → infrastructure/ imports: will be restructured during unified workflow
- workflows/ → infrastructure/ imports: eliminated by unified workflow
- MCP business logic (2-4): move to tools/ during refactor
- API business logic (2-18): move to infrastructure/ during refactor
- Tool importing tool (2-2): resolve during unified workflow extractors design
- core/logging.py → infrastructure (2-1): requires callback pattern refactor

### Formal documentation of technical debt

Add to CLAUDE.md or ARCHITECTURE.md a "Known technical debt" section listing:
- tools/ → infrastructure/ late imports (accepted, tracked)
- core/logging.py → infrastructure.db (accepted, callback refactor planned)
- fetch_subtitles → transcribe cross-tool import (accepted, workflow will orchestrate)
