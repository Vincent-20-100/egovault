# EgoVault — Claude Code Entry Point

> **This file is the single source of truth for any LLM working on this codebase.**
> It defines: where we are, where we're going, what the rules are, and how to work.
> Read it entirely before doing anything.

---

## 1. Project identity

EgoVault is a **personal knowledge vault** — ingest sources (YouTube, audio, PDF, text),
extract and chunk content, embed it for semantic search, and generate structured notes.

**Philosophy:** This project prioritizes **architectural elegance and scalability** over
shortcuts. It serves as both a functional tool and a portfolio-grade architecture reference.
It is also designed as a **reusable template** — the architecture, behavior files, and
project structure should be portable to any future ambitious project.

**Vision & strategy:** `docs/VISION.md` — why this project exists, competitive landscape,
buzz potential, and the north star (every decision must bring us closer to the 2-minute demo).
Read this to understand the WHY before diving into the HOW.

---

## 2. Tech stack

- Python 3.x via `.venv/Scripts/python`
- SQLite + sqlite-vec (local vector embeddings)
- Ollama or OpenAI (config-driven embedding + LLM)
- Pydantic v2 (schemas + config validation)
- FastAPI (HTTP API), Click (CLI), FastMCP (MCP server)
- pytest (test suite)

---

## 3. Document map — permanent vs provisional

### 3.1 Permanent documents (always current, updated with every code change)

| Document | Role | Authority |
|----------|------|-----------|
| **`CLAUDE.md`** (this file) | Entry point: rules, status, workflow | **Supreme** — overrides everything on conflict |
| `docs/architecture/ARCHITECTURE.md` | Technical architecture, structure, glossary | Overrides code comments on naming/structure |
| `docs/architecture/DATABASES.md` | DB schema reference | Must match `infrastructure/db.py` exactly |
| `config/system.yaml` | All tunable parameters | Single source for config values |
| `core/config.py` | Pydantic models for config | Must match `system.yaml` structure |
| `docs/superpowers/specs/2026-03-31-development-workflow.md` | The 7-phase development process | Mandatory process for all changes |
| `docs/superpowers/specs/2026-03-31-project-audit-spec.md` | Reusable audit method (8 domains) | Quality gate at Phase 6 |

### 3.2 The `docs/superpowers/` directory — all build artifacts

**Everything in `docs/superpowers/` is provisional.** It is the workspace for specs, plans,
brainstorm notes, and audits. At release, this entire directory can be cleaned or removed
from the public repo. The skill auto-generates files here.

```
docs/superpowers/
├── specs/              ← Active specs and brainstorm notes
│   └── future/         ← Validated specs NOT YET implemented
├── plans/              ← Active implementation plans
├── audits/             ← Audit results (dated)
└── archive/            ← Implemented or obsolete specs and plans
    ├── specs/
    └── plans/
```

**Lifecycle:** Spec/plan starts in `specs/` or `plans/`. Once implemented → move to `archive/`.
Once validated but deferred → move to `specs/future/`. Obsolete → move to `archive/`.

| Location | Content | Lifecycle |
|----------|---------|-----------|
| `specs/<date>-<name>.md` | Active feature specs | Implemented → `archive/specs/` |
| `specs/<date>-<name>-notes.md` | Brainstorm notes | Reference for spec, then `archive/` |
| `specs/future/<date>-<name>.md` | Validated but deferred specs | Implemented → `archive/specs/` |
| `plans/<date>-<name>.md` | Active execution plans | Implemented → `archive/plans/` |
| `audits/audit-results-<date>.md` | Dated audit results | Discarded after fixes applied |
| `archive/specs/` | Implemented or obsolete specs | Historical reference only |
| `archive/plans/` | Implemented plans | Historical reference only |

### 3.3 Reference documents (stable, rarely updated)

| Document | Role |
|----------|------|
| `docs/VISION.md` | Strategic vision: WHY we build this, market positioning, north star |
| `docs/FUTURE-WORK.md` | Ideas backlog (not yet specced) |
| `docs/mcp-setup.md` | MCP client setup guide |

**Rule:** When a provisional document contradicts a permanent document, **permanent wins**.
When CLAUDE.md contradicts ARCHITECTURE.md, **CLAUDE.md wins**.

---

## 4. Project structure

```
core/                    ← config, Pydantic schemas, context, uid, logging, errors
tools/
├── media/               ← transcribe, compress, fetch_subtitles, extract_audio
├── text/                ← chunk, embed, embed_note, summarize
├── vault/               ← create_note, update_note, search, finalize_source,
│                          delete_note, delete_source, restore_note, restore_source,
│                          generate_note_from_source, purge
└── export/              ← typst, mermaid
workflows/
├── ingest_youtube.py
├── ingest_audio.py
└── ingest_pdf.py
infrastructure/          ← db.py, vault_writer.py, embedding_provider.py, llm_provider.py
api/                     ← FastAPI HTTP layer
├── main.py
└── routers/             ← health, jobs, ingest, notes, sources, search, vault
cli/
├── main.py
├── output.py
└── commands/            ← ingest, search, notes, sources, status, purge
mcp/
└── server.py            ← exposes tools/ via MCP protocol
config/
├── system.yaml          ← algo params + taxonomy (versioned in repo)
├── user.yaml            ← user preferences (gitignored)
└── install.yaml         ← machine paths + secrets (gitignored)
scripts/
├── setup/
│   └── init_user_dir.py
└── temp/                ← one-shot scripts (migrations, punctual fixes)
tests/                   ← mirrors tools/, workflows/, api/, mcp/, core/, infrastructure/
docs/                    ← see §3 document map
```

**User storage (outside repo, never in git):**
```
egovault-user/
├── data/
│   ├── vault.db         ← SQLite source of truth (user data)
│   ├── .system.db       ← operational data (logs, jobs, cache)
│   └── media/           ← binary files (audio, video, PDF)
└── vault/               ← PRIVATE git repo (Obsidian notes)
```

---

## 5. Commands

```bash
.venv/Scripts/python scripts/setup/init_user_dir.py   # first install
.venv/Scripts/python -m pytest tests/                  # tests
.venv/Scripts/python mcp/server.py                     # MCP server (dev)
```

---

## 6. Architecture rules (G1–G12)

These rules exist because LLMs consistently make the same categories of mistakes.
**Every rule was triggered by a real incident.** Hard constraints, not suggestions.

---

### G1 — No implementation details in public-facing strings

**Public-facing** = MCP docstrings, API descriptions, error messages, CLI help, README, docs.

**Rule:** Describe **capabilities** (what), never **tools/libraries** (how).
Library names belong only in `requirements.txt`, `pyproject.toml`, imports, and internal comments.

| Wrong | Right |
|-------|-------|
| `"Transcribe using faster-whisper"` | `"Transcribe using the configured engine"` |
| `"Embed with nomic-embed-text via Ollama"` | `"Embed using the configured provider"` |
| `"Stored in sqlite-vec"` | `"Stored in the vector index"` |
| `Error: pypdf failed` | `Error: PDF parsing failed` |

---

### G2 — Describe WHAT, not HOW

Docstrings state **purpose and behavior**, not mechanism or parameter values.

| Wrong | Right |
|-------|-------|
| `"Splits text using a sliding window of 800 tokens"` | `"Splits text into overlapping chunks"` |
| `"Queries sqlite-vec with cosine similarity"` | `"Semantic search over the vault"` |

---

### G3 — Config-driven, not code-driven

Every tunable value comes from config (`system.yaml`, `user.yaml`, `install.yaml`). Never hardcode
algorithm parameters, provider names, model IDs, file paths, taxonomy values, or locale settings.

If a parameter doesn't exist in config yet, add it to `system.yaml` with a sensible default.

---

### G4 — Context-based dependency injection

**Target architecture (Direction 2 — VaultContext pattern):**

```
core/           ← schemas, interfaces, VaultContext — imports NOTHING from project
tools/          ← atomic functions — receive VaultContext, import core/ only
workflows/      ← orchestrate tools/ — build VaultContext, import tools/ + core/
infrastructure/ ← concrete implementations — import core/ only, provide VaultContext factories
mcp/            ← thin routing — build VaultContext via infrastructure/, call tools/
api/            ← thin routing — build VaultContext via infrastructure/, call tools/ + workflows/
```

**The VaultContext pattern:**
- `core/context.py` defines `VaultContext` — a dataclass holding all infrastructure dependencies
  (DB path, settings, embedding function, LLM function, vault writer)
- `infrastructure/` provides `build_context(settings) -> VaultContext`
- Tools receive `ctx: VaultContext` as parameter — they NEVER import infrastructure/ directly
- Surfaces (API, CLI, MCP) and workflows call `build_context()` then pass `ctx` to tools

**Why:** Inspired by LangGraph state passing and FastAPI dependency injection. Tools become
truly decoupled: easy to test (mock the context), easy to swap providers (change the factory),
zero import cycles.

**Hard rules:**
- A tool **never imports** `infrastructure/` — it receives what it needs via `VaultContext`
- A tool **never imports another tool** — if needed, the tool boundary is wrong
- `core/` has **zero imports** from any other project package
- `mcp/server.py` and `api/` routers contain **zero business logic** — routing only
- New Pydantic models go in `core/schemas.py`

**Current state:** Tools currently use late imports from infrastructure/ (technical debt).
This will be resolved by the VaultContext refactoring (spec pending).
See `docs/superpowers/specs/2026-03-31-unified-ingest-architecture.md` §2.

---

### G5 — No over-engineering

- No abstractions, helpers, or utilities for single-use operations
- No error handling for impossible scenarios
- No feature flags, backwards-compat shims, or re-exports
- No docstrings/comments/type annotations added to unchanged code
- No new files when editing existing ones would suffice
- 3 similar lines > 1 premature abstraction

---

### G6 — Error handling discipline

- **Every `except` block must log or re-raise.** No silent swallowing.
  - `except SpecificError as e: logger.debug("...: %s", e)` — acceptable for fallbacks
  - `except Exception: pass` — **forbidden** unless in logging/health-check code with a comment explaining why
- **Catch specific exceptions** — `except ValueError`, not `except Exception` when the failure mode is known
- **Never expose internals in user-facing errors** — no stack traces, file paths, SQL, library names
- **Use project error types** from `core/errors.py`
- **Log levels:** `error` = needs attention, `warning` = recoverable, `debug` = tracing. Never `print()`.

---

### G7 — Language and naming discipline

- **Code, SQL, comments, config keys:** English. Always.
- **Vault content** (notes, tags, slugs): French by default (configurable).
- Use **exact glossary terms** from `ARCHITECTURE.md` §1.3 — `note` not `document`, `source` not `file`, `embedding` not `vector`.
- Casing: `snake_case` Python, `kebab-case` vault slugs/tags.

---

### G8 — Test discipline

- Test files **mirror source structure**: `tools/vault/search.py` → `tests/tools/vault/test_search.py`
- Test **behavior**, not implementation
- Every new tool or workflow **must** have a corresponding test file
- Do not add tests for unchanged code (unless explicitly asked)
- Use existing `pytest` fixtures and patterns — read a neighboring test file first

---

### G9 — Pydantic everywhere at boundaries

- Tool input/output crossing a boundary (MCP, API, config) **must** be a Pydantic model
- No raw dicts as public function signatures
- Validation at the **boundary** (MCP/API), not deep inside tools
- New models in `core/schemas.py`, naming: `*Input`, `*Result`, `*Filters`

---

### G10 — Security by default

- **Never log** user content, API keys, or file paths at INFO or above
- **Always validate file paths** against allowed directories before I/O
- **Parameterized SQL exclusively** — `?` placeholders for all values.
  Column names from allowlists may use f-strings with an explicit safety comment.
- **No `eval()`, `exec()`, or dynamic import tricks**
- See `ARCHITECTURE.md` §10 for the full security model

---

### G11 — MCP/API are routing layers only

- **Zero business logic** — delegate everything to `tools/` or `workflows/`
- **Docstrings** follow G1 and G2 (capabilities only)
- **Return** `model.model_dump(mode="json")` — never construct dicts manually
- **Function bodies** should be <15 lines (build context, call tool, return result)

---

### G12 — No duplicated documentation

- A fact exists in **one place only**. Config values → `system.yaml`. Architecture → `ARCHITECTURE.md`.
- Docstrings must not repeat config/architecture docs
- On contradiction: **config/arch wins** — fix the docstring

---

### G13 — Code comments: concise, surgical, no dead weight

- **Module docstring:** role + why it exists (2-3 lines max)
- **Class/function docstring:** one line "what", not "how". Args/Returns only if the signature isn't self-explanatory
- **Inline comments:** only when the "why" isn't obvious. Never narrate the "what"
- **Never reference** file paths, library names, or config values in comments — they go stale
- **A good name replaces a comment.** If you need a comment to explain a variable, rename it first
- English only (G7). Concise > exhaustive

---

### Pre-commit checklist

Before any change is considered complete:

- [ ] G1: No library names in public strings
- [ ] G2: Docstrings describe what, not how
- [ ] G3: No hardcoded values
- [ ] G4: Architecture boundaries respected (or debt documented)
- [ ] G5: No unnecessary abstractions
- [ ] G6: Every except logs or re-raises
- [ ] G7: English code, French vault content
- [ ] G8: Tests mirror source structure
- [ ] G9: Pydantic at boundaries
- [ ] G10: No security anti-patterns
- [ ] G11: Routing layers are thin
- [ ] G12: No duplicated docs
- [ ] G13: Code is properly commented for humans and LLMs

---

## 7. Development workflow

**Mandatory process:** `docs/superpowers/specs/2026-03-31-development-workflow.md`

```
BRAINSTORM → SPEC → PLAN → IMPLEMENT → TEST → AUDIT → SHIP
```

**Key rules:**
- No implementation without a validated spec
- No spec without a brainstorm (for complex features)
- Doc updates in the **same commit** as code changes
- Audit is the quality gate (zero critical/major before shipping)
- Each phase produces a committed deliverable

**Skills:**

| Task | Skill |
|------|-------|
| Architecture brainstorming | `superpowers:brainstorming` |
| Write implementation plan | `superpowers:writing-plans` |
| Execute plan | `superpowers:executing-plans` |
| Code review | `superpowers:requesting-code-review` |
| Debug | `superpowers:systematic-debugging` |

**Before starting any spec or plan, ask:**
> "Have you re-read the spec? I can start as soon as you confirm."

---

## 8. Conventions

### Python
- `core/` = interfaces + shared models — never called directly by a client
- `tools/` = atomic functions: typed input → typed output, no side-effects beyond ctx
- `workflows/` = ordered sequences of tool calls — no own business logic
- `infrastructure/` = concrete implementations of `core/` interfaces

### Vault
- Note slugs: `kebab-case`, no accents, lowercase (e.g. `elasticite-prix.md`)
- Tags: French, lowercase, no accents, hyphens (e.g. `biais-cognitifs`)
- Commits: `feat:` / `fix:` / `docs:` / `chore:` + description **in English**

### Scripts
- One-shot scripts go in `scripts/temp/` (e.g. `001_move_tool_logs_to_system_db.py`)
- Never in `scripts/setup/` (reserved for init) nor at project root

---

## 9. Project status

**Live project state:** `PROJECT-STATUS.md` — next action, debt, roadmap, session history.
**Decision context:** `SESSION-CONTEXT.md` — WHY decisions were made, traps to avoid, open questions.

Both files live at the root of the repo. Together they give a new LLM context
everything it needs to continue work without making uninformed decisions.

### Mandatory rules for these files

1. **Read both files at the start of every session** before doing anything.
2. **Update both files at the end of every session:**
   - `PROJECT-STATUS.md`: update next action, move completed items, add session to history
   - `SESSION-CONTEXT.md`: rewrite with current decisions, reasoning, traps, and open questions.
     This file is NOT a log — it is **rewritten** each session to stay concise. Old reasoning
     that is no longer relevant is removed. New reasoning is added.
3. **When the user signals they want to stop** (or asks "can I leave?", "on arrête?", etc.),
   update both files and commit+push **before** confirming the session is safe to end.
4. **Never make autonomous decisions on topics listed in "Open questions"** in SESSION-CONTEXT.md.
   These require interactive discussion with the user.
