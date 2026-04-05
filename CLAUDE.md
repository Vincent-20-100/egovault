# EgoVault — Claude Code Entry Point

**Architecture reference:** `docs/architecture/ARCHITECTURE.md`
Any ambiguity about naming, structure, or contracts → this file takes precedence over everything.

**Product audit:** `docs/PRODUCT-AUDIT.md`
Feature gaps, improvement roadmap, prioritization — validated 2026-03-29. Supersedes any prior spec ordering.

---

## Tech Stack

- Python 3.x via `.venv/Scripts/python` (Windows)
- SQLite + **sqlite-vec** (local vector embeddings, dims configurable via `system.yaml:embedding.dims`)
- **Ollama** (embedding `nomic-embed-text`) — or OpenAI (config-driven)
- **Pydantic v2** (schemas + config validation)
- `faster-whisper` (local transcription), `youtube-transcript-api`, `yt-dlp`, `pypdf`
- Tests: `pytest` in `tests/` (mirror of `tools/`, `workflows/`, `api/`, `benchmark/`)

---

## Structure

```
core/                    ← config, Pydantic schemas, uid, logging, errors
tools/
├── media/               ← transcribe, compress, fetch_subtitles, extract_audio
├── text/                ← chunk, embed, summarize
├── vault/               ← create_note, update_note, search, finalize_source
└── export/              ← typst, mermaid
workflows/
├── ingest_youtube.py
├── ingest_audio.py
└── ingest_pdf.py
infrastructure/          ← db.py, vault_writer.py, embedding_provider.py, llm_provider.py
                           reranker_provider.py [SPEC READY], semantic_cache.py [SPEC READY]
api/                     ← FastAPI HTTP layer [IMPLEMENTED]
cli/
├── main.py
├── output.py
└── commands/
    ├── ingest.py
    ├── search.py
    ├── notes.py
    ├── sources.py
    └── status.py
frontend/                ← Next.js 14 [SPEC READY, prerequisite: api/]
benchmark/               ← RAG quality framework [SPEC READY]
mcp/
└── server.py            ← exposes tools/ via MCP protocol
config/
├── system.yaml          ← algo params + taxonomy (versioned in repo)
├── user.yaml            ← user preferences (gitignored)
└── install.yaml         ← machine paths + secrets (gitignored)
scripts/
├── setup/
│   └── init_user_dir.py ← generates egovault-user/ + default Obsidian config
└── temp/                ← one-shot scripts (migrations, punctual fixes)
tests/                   ← mirror of tools/, workflows/, api/, benchmark/
docs/
├── architecture/        ← ARCHITECTURE.md, DATABASES.md, CONTRACTS.md
├── product-audit/       ← split audit sections (01–13), LLM-friendly
├── PRODUCT-AUDIT.md     ← index pointing to product-audit/
├── FUTURE-WORK.md       ← ideas backlog (not yet specced)
└── references/          ← visual inspiration, diagrams
```

**User storage (outside repo):**
```
egovault-user/           ← LOCAL, never in git
├── data/
│   ├── vault.db         ← SQLite source of truth (user data)
│   ├── .system.db       ← operational data (logs, jobs, cache, benchmark)
│   └── media/           ← binary files (audio, video, PDF)
└── vault/               ← PRIVATE git repo (Obsidian notes)
    ├── .obsidian/
    └── notes/
```

---

## Temporary scripts / migration

All one-shot scripts (DB migrations, one-time fixes, provisional scripts) go in:

```
scripts/temp/
```

Convention established in `docs/architecture/ARCHITECTURE.md` section 5.3 (e.g. `scripts/temp/001_move_tool_logs_to_system_db.py`).
Never put these scripts in `scripts/setup/` (reserved for initialization) nor at the root.

---

## Commands

```bash
# Initial setup (first installation)
.venv/Scripts/python scripts/setup/init_user_dir.py

# Tests
.venv/Scripts/python -m pytest tests/

# MCP server (dev)
.venv/Scripts/python mcp/server.py
```

---

## Python Conventions

- `core/` = abstract interfaces + shared Pydantic models — never called directly by a client
- `tools/` = atomic functions: one typed input → one typed output, zero implicit side-effects
- `workflows/` = ordered sequences of tool calls — no own business logic
- `infrastructure/` = concrete implementations of `core/` interfaces — never imported by `tools/`
- A tool **never imports** another tool — if needed, the boundary is poorly drawn
- Source code, SQL, comments, config keys: **English**
- Vault content (notes, tags, slugs): **French** (configurable)

## Vault Conventions

- Note slugs: `kebab-case` without accents, lowercase (e.g. `elasticite-prix.md`)
- Tags: French, lowercase, without accents, hyphens (e.g. `biais-cognitifs`)
- Commits: `feat:` / `fix:` / `docs:` / `chore:` + description **in English**

---

## LLM Guardrails — mandatory rules for any model working on this codebase

These rules exist because LLMs consistently make the same categories of mistakes.
**Every rule here was triggered by a real incident.** Treat them as hard constraints, not suggestions.

---

### G1 — No implementation details in public-facing strings

**Public-facing** = MCP tool docstrings, API endpoint descriptions, error messages shown to users, CLI help text, README, docs.

| Violation | Correct |
|-----------|---------|
| `"Transcribe using faster-whisper"` | `"Transcribe using the configured engine"` |
| `"Embed with nomic-embed-text via Ollama"` | `"Embed using the configured provider"` |
| `"Stored in sqlite-vec"` | `"Stored in the vector index"` |
| `"Compress to Opus mono"` | `"Compress to a low-bitrate format"` |
| `"Uses yt-dlp to download"` | `"Downloads the video"` |
| `Error: pypdf failed to parse` | `Error: PDF parsing failed` |

**Why:** Tools, providers, and libraries are swappable. Leaking their names creates coupling between documentation and implementation. When we swap a library for another, every leaked mention becomes a lie.

**Rule:** Describe **capabilities** (what), never **tools** (how). The only place library names belong is `requirements.txt`, `pyproject.toml`, import statements, and internal code comments.

---

### G2 — Describe WHAT, not HOW

Docstrings and descriptions must state the **purpose and behavior** — not the mechanism.

| Violation | Correct |
|-----------|---------|
| `"Splits text using a sliding window of 800 tokens with 200 overlap"` | `"Splits text into overlapping chunks per system.yaml config"` |
| `"Queries sqlite-vec with cosine similarity"` | `"Semantic search over the vault"` |
| `"Writes a .md file to the vault/ directory"` | `"Persists the note to the vault"` |

Parameters like chunk size, overlap, similarity metric — these live in `system.yaml`. Docstrings must not duplicate or contradict config values.

---

### G3 — Config-driven, not code-driven

Every tunable value **must** come from config (`system.yaml`, `user.yaml`, `install.yaml`). Never hardcode:

- Algorithm parameters (chunk size, overlap, similarity threshold, bitrate, dimensions)
- Provider names or model IDs
- File paths or directory names
- Taxonomy values (note_type, source_type lists)
- Language/locale settings

If a function needs a parameter that doesn't exist in config yet, add it to `system.yaml` with a sensible default and document it in `ARCHITECTURE.md`. Do not invent a local default.

---

### G4 — Respect the hexagonal architecture

```
core/           <- schemas, interfaces, pure logic — imports NOTHING from project
tools/          <- atomic functions — imports core/ only (+ infrastructure/ via late import if needed)
workflows/      <- orchestrates tools/ — imports tools/ and core/
infrastructure/ <- concrete implementations — imports core/ only
mcp/            <- thin routing — imports tools/ and infrastructure/ (read-only DB queries)
api/            <- thin routing — imports tools/, workflows/, infrastructure/
```

**Hard rules:**
- A tool **never imports another tool** — if you feel the need, the tool boundary is wrong
- `mcp/server.py` and `api/` routers contain **zero business logic** — they are routing layers only
- New Pydantic models go in `core/schemas.py`, not scattered in tool files
- `core/` has **zero imports** from any other project package

**Known technical debt:** Some tools currently import `infrastructure/` directly (via late imports). This is tracked and accepted for now. Do not add new ones without explicit approval.

---

### G5 — No over-engineering

- Do not add abstractions, helpers, or utilities for single-use operations
- Do not add error handling for scenarios that cannot happen
- Do not add feature flags, backwards-compat shims, or re-exports
- Do not add docstrings, comments, or type annotations to code you did not change
- Do not create new files when editing an existing one would suffice
- 3 similar lines of code is better than 1 premature abstraction

---

### G6 — Error handling discipline

- **Never swallow exceptions silently** — no bare `except:`, no `except Exception: pass`
- **Never expose internal details in user-facing errors** — no stack traces, no file paths, no SQL, no library names
- **Use project error types** from `core/errors.py` — do not invent new exception classes without justification
- **Log at the right level:** `logger.error` for failures that need attention, `logger.warning` for recoverable issues, `logger.debug` for tracing. Never `print()`.

---

### G7 — Language and naming discipline

- **Code, SQL, comments, config keys:** English. Always. No exceptions.
- **Vault content** (notes, tags, slugs): French by default (configurable).
- Use the **exact glossary terms** from `ARCHITECTURE.md` section 1.3 — do not invent synonyms (`document` is not `note`, `file` is not `source`, `vector` is not `embedding`).
- Casing: `snake_case` for Python, `kebab-case` for vault slugs/tags. See section 1.2.

---

### G8 — Test discipline

- Test files **mirror source structure**: `tools/vault/create_note.py` maps to `tests/tools/vault/test_create_note.py`
- Test **behavior**, not implementation — do not assert on internal calls or mock internals
- Every new tool or workflow **must** have a corresponding test file
- Do not add tests for code you did not change (unless explicitly asked)
- Use `pytest` fixtures and the existing test patterns — read a neighboring test file before writing a new one

---

### G9 — Pydantic everywhere at boundaries

- Every tool input/output that crosses a boundary (MCP, API, config) **must** be a Pydantic model
- No raw dicts as function signatures for public interfaces — use typed models
- Validation happens at the **boundary** (MCP server, API router), not deep inside tools
- New models go in `core/schemas.py`, follow existing naming conventions (`*Input`, `*Result`, `*Filters`)

---

### G10 — Security by default

- **Never log** user content, API keys, file paths, or query strings at INFO level or above
- **Always validate file paths** against allowed directories before any I/O operation
- **No string formatting in SQL** — use parameterized queries exclusively
- **No `eval()`, `exec()`, or dynamic import tricks** unless there is an existing pattern for it
- See `ARCHITECTURE.md` section 10 for the full security model

---

### G11 — MCP server is a routing layer

`mcp/server.py` must remain a thin wrapper:
- **No business logic** — delegate everything to `tools/`
- **Docstrings describe user-facing behavior** — never mention libraries, algorithms, or internal details (see G1, G2)
- **Return `model.model_dump(mode="json")`** — never construct dicts manually
- **Do not add new imports from infrastructure/** unless it is a read-only DB query with no alternative

---

### G12 — Do not duplicate documentation

- A fact should exist in **one place only**. Config values are documented in `system.yaml`. Architecture in `ARCHITECTURE.md`. Workflow in `get_workflow_guide()`.
- Docstrings must not repeat what config or architecture docs already say
- If you find contradictions between docstrings and config/arch docs, **config/arch wins** — fix the docstring

---

### Checklist before submitting any change

Before considering any implementation complete, verify:

- [ ] No library/tool names leaked in docstrings, error messages, or user-facing strings (G1)
- [ ] Docstrings describe what, not how (G2)
- [ ] No hardcoded values that should be in config (G3)
- [ ] Architecture boundaries respected (G4)
- [ ] No unnecessary abstractions or files added (G5)
- [ ] Error handling uses project patterns (G6)
- [ ] English in code, French in vault content only (G7)
- [ ] Tests exist and mirror source structure (G8)
- [ ] Pydantic models at all boundaries (G9)
- [ ] No security anti-patterns (G10)
- [ ] MCP/API layers are thin routing only (G11)
- [ ] No duplicated documentation (G12)

---

## Skills to use (superpowers — always these skills, no others)

| Task | Skill to invoke |
|---|---|
| Architecture brainstorming / decisions | `superpowers:brainstorming` |
| Write an implementation plan | `superpowers:writing-plans` |
| Execute an existing plan | `superpowers:executing-plans` |
| Code review after implementation | `superpowers:requesting-code-review` |
| Debug a complex problem | `superpowers:systematic-debugging` |

> Do not use `bmad`, `everything-claude-code`, or other skill families on this project.
> The spec was produced with `superpowers:brainstorming` — stay within the same ecosystem.

---

## ⚠️ Rule: unimplemented specs

Before invoking `superpowers:writing-plans` or `superpowers:executing-plans` on a spec, **always ask**:

> "Have you re-read the spec `docs/superpowers/specs/<name>.md`? I can start the plan as soon as you confirm."

Do not start implementation without explicit confirmation from the user.

---

## Progress status

**Architecture reference:** `docs/architecture/ARCHITECTURE.md` (consolidated on 2026-03-28)

**Implemented:**
- Complete hexagonal architecture (`core/`, `tools/`, `workflows/`, `infrastructure/`, `mcp/`)
- Workflows: `ingest_youtube`, `ingest_audio`, `ingest_pdf`
- MCP server: `mcp/server.py`
- Setup script: `scripts/setup/init_user_dir.py`
- **FastAPI API** (`api/`) — 6 routers (health, jobs, ingest, notes, sources, search), factory pattern, ThreadPoolExecutor, `.system.db` for jobs
- Full test suite: `tests/core/`, `tests/infrastructure/`, `tests/tools/`, `tests/workflows/`, `tests/mcp/`, `tests/api/` (248 tests)
- **A1 — MCP flow fix** *(2026-03-30)* — `embed_note`, auto-embed on create/update, `get_source` / `list_notes` / `list_sources` / `update_note` MCP tools, enriched docstrings, `docs/mcp-setup.md` (259 tests)

**Roadmap (revised 2026-03-30 — see `docs/PRODUCT-AUDIT.md` §6.3)**

---

### Block A — Core value loop *(complete before optimizing anything)*

**A0 — Security Phase 1** *(pre-launch, blocks going public)* ✓ DONE
- Spec: `docs/superpowers/specs/2026-03-29-security-design.md`
- Community docs, SECURITY.md, CONTRIBUTING.md, issue templates, .gitignore audit, dependency audit

**A2 — CLI** *(first human-facing surface — next up)*
- `egovault ingest <url/file>`, `egovault search "query"`, `egovault status`
- Spec: `docs/superpowers/specs/2026-03-30-cli-design.md`
- Plan: `docs/superpowers/plans/2026-03-30-a2-cli-completion.md`
- → `superpowers:executing-plans`

**A3 — Delete operations** *(basic CRUD completeness)*
- `delete_source`, `delete_note`, purge chunks, implement `pending_deletion` status
- Spec: `docs/superpowers/specs/2026-03-30-delete-operations-design.md`
- Plan: `docs/superpowers/plans/2026-03-30-a3-delete-operations.md`
- → `superpowers:executing-plans`

**A4 — Internal LLM path** *(low marginal cost after A1)*
- `generate_note_from_source` tool, `auto_generate_note` config flag, `draft | active` note status
- Depends on: A1 complete
- Spec: `docs/superpowers/specs/2026-03-30-internal-llm-path-design.md`
- Plan: `docs/superpowers/plans/2026-03-30-a4-internal-llm-path.md`
- → `superpowers:executing-plans`

---

### Block B — Infrastructure *(after Block A — now users and data exist)*

**B1 — `embedding.dims` fix** *(cross-cutting, extracted from semantic cache spec)*
- Spec: `docs/superpowers/specs/2026-03-30-embedding-dims-fix.md`
- Plan: `docs/superpowers/plans/2026-03-30-b1-embedding-dims.md`
- → `superpowers:executing-plans`

**B2 — Security Phase 2** *(application-level hardening)*
- Spec ready: `docs/superpowers/specs/2026-03-29-security-design.md`
- Input validation, log redaction, file permissions, rate limiting, external API guardrails
- → `superpowers:writing-plans` then `superpowers:executing-plans`

**B3 — Monitoring** *(observability now that users exist)*
- Spec ready: `docs/superpowers/specs/2026-03-28-monitoring-design.md`
- → `superpowers:writing-plans` then `superpowers:executing-plans`

---

### Block C — User surface

**C1 — Frontend** *(prerequisite: api/ ✓, Block A)*
- Spec ready: `docs/superpowers/specs/2026-03-28-frontend-design.md`
- → `superpowers:brainstorming` (UX/UI) first, then `superpowers:writing-plans`

---

### Block D — Search quality *(after `notes_vec` is populated — requires A1)*

**D1 — Reranking**
- Spec ready: `docs/superpowers/specs/2026-03-28-reranking-design.md`

**D2 — Semantic cache**
- Spec ready: `docs/superpowers/specs/2026-03-28-semantic-cache-design.md`

**D3 — Benchmark / RAG evaluation**
- Spec ready: `docs/superpowers/specs/2026-03-28-evaluation-design.md` *(renamed eval→benchmark)*

→ For each: `superpowers:writing-plans` then `superpowers:executing-plans`

---

### Backlog — future brainstorming sessions

- **Provider Management** — CLI to configure/swap LLM, embedder, transcriber, reranker. Security guardrails G6.1–G6.9 apply. → `superpowers:brainstorming`
- **Backend E2E tests** — pytest + temp DBs, Ollama/LLM mocks, job lifecycle. → `superpowers:writing-plans`
- **Extraction provider** — tiered architecture (builtin → markitdown → chandra). Unlocks `ingest_web`, `ingest_docx`, `ingest_epub`, `ingest_pptx`. See audit §11. → `superpowers:brainstorming`
- **Re-ingestion path** — re-process a source if transcription settings change. See audit §3.2.
- **Structural chunker** — paragraph/heading-aware, replaces fixed-window split. See audit §4.4.
- **`import_notes`** — Notion export, Obsidian, Bear → parse frontmatter → `create_note` + `embed_note`.
- **`ingest_image`** — OCR-based, requires Tier 2 extraction provider.
- **`ingest_playlist`** — batch YouTube with partial failure handling.
- **`merge_notes` / `link_notes`** — vault maintenance tools.
- **Guardrails retroactive audit** — Scan all existing code (tools/, workflows/, mcp/, api/, infrastructure/) against the G1–G12 guardrails. Fix all violations in docstrings, error messages, hardcoded values, architecture boundary crossings, and naming inconsistencies introduced before these rules existed. → `superpowers:writing-plans`
