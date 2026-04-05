# VaultContext Refactoring — Implementation Plan

**Date:** 2026-03-31
**Spec:** `docs/superpowers/specs/2026-03-31-vaultcontext-refactoring-spec.md`
**Brainstorm:** `docs/superpowers/specs/2026-03-31-vaultcontext-refactoring-notes.md`
**Phase:** 3 — PLAN

---

## Pre-flight check

Before starting, verify:
- [ ] Spec decisions still hold (VaultDB facade, Protocols, build_context)
- [ ] No new tools were added since spec was written
- [ ] `infrastructure/db.py` public functions match the 22 listed in spec §3
- [ ] All 367 tests pass on current branch

---

## Steps

### Step 1 — Foundation: core/context.py

**Files:** `core/context.py` (create)
**Do:**
- Create `VaultContext` dataclass
- Create Protocols: `EmbedFn`, `GenerateFn`, `WriteNoteFn`
- Import only from `core/` (schemas, config) — zero infra imports
- Forward-reference `VaultDB` with `TYPE_CHECKING` (since VaultDB lives in infrastructure/)

**Test:** `python -c "from core.context import VaultContext, EmbedFn, GenerateFn, WriteNoteFn"`
**Doc:** None (new internal module)
**Commit message:** `feat: add core/context.py — VaultContext dataclass and Protocols`

---

### Step 2 — VaultDB facade

**Files:** `infrastructure/vault_db.py` (create), `tests/infrastructure/test_vault_db.py` (create)
**Do:**
- Create `VaultDB` class with `__init__(self, db_path: Path)`
- Add 22 one-line delegation methods (see spec §3 for complete list)
- Each method calls the corresponding `infrastructure.db` function with `self._db_path`
- Add `get_existing_slugs(table: str) -> set[str]` to replace raw `get_vault_connection` usage
- Add `get_graph_data() -> dict` for mermaid export (replaces raw connection in mermaid.py)

**Test:** Write tests that verify each VaultDB method delegates correctly to db.py.
Use a real temp SQLite DB (same pattern as `tests/infrastructure/test_db.py`).
**Doc:** None (new internal module)
**Commit message:** `feat: add infrastructure/vault_db.py — VaultDB facade (22 methods)`

---

### Step 3 — build_context() factory

**Files:** `infrastructure/context.py` (create), `tests/infrastructure/test_context.py` (create)
**Do:**
- Create `build_context(settings: Settings) -> VaultContext`
- Instantiate `VaultDB(settings.vault_db_path)`
- Create `embed` lambda wrapping `embedding_provider.embed(text, settings)`
- Create `generate` lambda wrapping `llm_provider.generate_note_content(...)` or `None`
- Extract `_llm_is_configured(settings) -> bool` helper
- Create `write_note` lambda wrapping `vault_writer.write_note(note, vault_path)`

**Test:** Test that `build_context()` returns a valid VaultContext with correct field types.
Mock the providers (no real Ollama/Anthropic needed).
**Doc:** None (new internal module)
**Commit message:** `feat: add infrastructure/context.py — build_context() factory`

---

### Step 4 — Test fixture

**Files:** `tests/conftest.py` (modify)
**Do:**
- Add `ctx` fixture that builds a VaultContext with:
  - Real temp SQLite DB (via `init_db`)
  - Mock `embed` returning zero vector
  - `generate = None`
  - Mock `write_note` returning a path
  - Temp directories for vault_path and media_path
- Keep existing `settings` fixture (some tests may still need it during migration)

**Test:** `python -m pytest tests/ -x` — all existing tests still pass (ctx fixture unused yet)
**Doc:** None
**Commit message:** `feat: add ctx fixture to tests/conftest.py`

---

### Step 5 — Fix core/logging.py debt

**Files:** `core/logging.py` (modify), `api/main.py` (modify), `mcp/server.py` (modify), `tests/core/test_logging.py` (modify)
**Do:**
- In `core/logging.py`: replace `from infrastructure.db import ...` with a callback pattern
  - Add `_log_writer: Callable | None = None`
  - `configure()` accepts a callable instead of a db_path
  - `_write_log()` calls `_log_writer(...)` if set
- In `api/main.py` lifespan: create log writer callback, pass to `log_mod.configure()`
- In `mcp/server.py`: same pattern at module level
- Update test to verify callback pattern works

**Test:** `python -m pytest tests/core/test_logging.py -x` then full suite
**Doc:** None (internal change)
**Commit message:** `fix: core/logging.py — replace infrastructure import with callback injection`

---

### Step 6 — Adapt surfaces: MCP server

**Files:** `mcp/server.py` (modify), `tests/mcp/test_server.py` (modify)
**Do:**
- Replace `settings = load_settings()` with `ctx = build_context(load_settings())`
- Update all tool wrappers: pass `ctx` instead of `settings` to tools
- Move `create_note` business logic (slug gen, UID creation) into `tools/vault/create_note.py`
  - create_note tool gets a new higher-level entry point that handles system fields
- Keep `settings` accessible as `ctx.settings` where MCP-only logic needs it (e.g., `allow_destructive_ops`)
- Update tests to patch `ctx` instead of `settings`

**Test:** `python -m pytest tests/mcp/ -x` then full suite
**Doc:** None
**Commit message:** `refactor: mcp/server.py — use VaultContext, move create_note logic to tool`

---

### Step 7 — Adapt surfaces: API

**Files:** `api/main.py` (modify), `api/routers/search.py`, `api/routers/notes.py`, `api/routers/ingest.py`, `api/routers/sources.py`, `api/routers/vault.py`, `api/routers/jobs.py` (modify), API tests (modify)
**Do:**
- In `api/main.py`: replace `app.state.settings = settings` with `app.state.ctx = build_context(settings)`
- In all routers: replace `request.app.state.settings` with `request.app.state.ctx`
- Pass `ctx` to tools/workflows instead of `settings`
- Move `approve_note` business logic from `routers/notes.py` into a tool
- Update API tests

**Test:** `python -m pytest tests/api/ -x` then full suite
**Doc:** None
**Commit message:** `refactor: api/ — use VaultContext across all routers`

---

### Step 8 — Adapt surfaces: CLI

**Files:** `cli/commands/search.py`, `cli/commands/notes.py`, `cli/commands/sources.py`, `cli/commands/ingest.py`, `cli/commands/purge.py`, `cli/commands/status.py` (modify), CLI tests (modify)
**Do:**
- Add `_build_context()` helper (calls `load_settings()` then `build_context()`)
- Replace `settings = _load_settings()` with `ctx = _build_context()` in each command
- Pass `ctx` to tools/workflows
- Update CLI tests

**Test:** `python -m pytest tests/cli/ -x` then full suite
**Doc:** None
**Commit message:** `refactor: cli/ — use VaultContext across all commands`

---

### Step 9 — Migrate vault/ tools (10 files)

**Files:** All 10 `tools/vault/*.py` files + their tests
**Do:** For each tool:
1. Change signature: `settings: Settings` → `ctx: VaultContext`
2. Remove all `from infrastructure.*` late imports
3. Replace DB calls: `func(settings.vault_db_path, ...)` → `ctx.db.func(...)`
4. Replace embed calls: `embed(text, settings)` → `ctx.embed(text)`
5. Replace generate calls: `generate_note_content(...)` → `ctx.generate(...)`
6. Replace write calls: `write_note(note, path)` → `ctx.write_note(note, ctx.vault_path)`
7. Replace config access: `settings.xxx` → `ctx.settings.xxx`
8. Update corresponding test file to use `ctx` fixture

**Order within vault/ (by dependency — simplest first):**
1. `finalize_source.py` (2 DB calls, no providers)
2. `restore_note.py` (2 DB calls)
3. `restore_source.py` (2 DB calls)
4. `delete_note.py` (4 DB calls)
5. `delete_source.py` (6 DB calls)
6. `search.py` (2 DB calls + embed)
7. `create_note.py` (3 DB calls + embed + write_note)
8. `update_note.py` (4 DB calls + embed + write_note)
9. `generate_note_from_source.py` (6 DB calls + embed + generate + write_note — most complex)
10. `purge.py` (8 DB calls)

**Test:** After each tool: `python -m pytest tests/tools/vault/test_<name>.py -x` then full suite
**Doc:** None
**Commit message:** `refactor: migrate tools/vault/<name>.py to VaultContext`

---

### Step 10 — Migrate text/ tools (2 files)

**Files:** `tools/text/embed.py`, `tools/text/embed_note.py` + their tests
**Do:** Same pattern as Step 9:
- `embed.py`: remove `embedding_provider` import, use `ctx.embed()`
- `embed_note.py`: remove DB + embedding imports, use `ctx.db` + `ctx.embed()`

**Test:** `python -m pytest tests/tools/text/ -x` then full suite
**Doc:** None
**Commit message:** `refactor: migrate tools/text/ to VaultContext`

---

### Step 11 — Migrate export/ tools (2 files)

**Files:** `tools/export/mermaid.py`, `tools/export/typst.py` + their tests
**Do:**
- `mermaid.py`: replace `get_vault_connection` with `ctx.db.get_graph_data()`
- `typst.py`: replace `get_note` import with `ctx.db.get_note()`

**Test:** `python -m pytest tests/tools/export/ -x` then full suite
**Doc:** None
**Commit message:** `refactor: migrate tools/export/ to VaultContext`

---

### Step 12 — Migrate workflows (3 files)

**Files:** `workflows/ingest_youtube.py`, `workflows/ingest_audio.py`, `workflows/ingest_pdf.py` + their tests
**Do:**
- Change signature: `settings: Settings` → `ctx: VaultContext`
- Replace all `infrastructure.db` imports with `ctx.db` calls
- Replace `embed_text(text, settings)` with tool call using `ctx`
- Workflows still import tools (that's allowed by G4)
- Update workflow tests

**Test:** `python -m pytest tests/workflows/ -x` then full suite
**Doc:** None
**Commit message:** `refactor: migrate workflows/ to VaultContext`

---

### Step 13 — Final cleanup and verification

**Files:** All tools/, workflows/, mcp/, api/, cli/
**Do:**
- Grep for `from infrastructure` in `tools/` — must return **zero results**
- Grep for `from infrastructure` in `core/` — must return **zero results**
- Grep for `settings:.*Settings` in `tools/` signatures — must return **zero results**
- Remove any unused imports
- Run full test suite

**Test:** `python -m pytest tests/ -x` — all tests pass
**Doc:** Update ARCHITECTURE.md §2.3 to document VaultContext pattern as implemented (not just spec).
**Commit message:** `chore: VaultContext migration complete — verify G4 compliance`

---

## Summary

| Step | What | New files | Modified files | Tests |
|------|------|-----------|----------------|-------|
| 1 | core/context.py | 1 | 0 | import check |
| 2 | VaultDB facade | 2 | 0 | dedicated tests |
| 3 | build_context() | 2 | 0 | dedicated tests |
| 4 | ctx fixture | 0 | 1 | full suite |
| 5 | logging debt | 0 | 4 | full suite |
| 6 | MCP surface | 0 | 2+ | full suite |
| 7 | API surface | 0 | 8+ | full suite |
| 8 | CLI surface | 0 | 6+ | full suite |
| 9 | vault/ tools | 0 | 20 | per tool + full |
| 10 | text/ tools | 0 | 4 | full suite |
| 11 | export/ tools | 0 | 4 | full suite |
| 12 | workflows | 0 | 6 | full suite |
| 13 | cleanup | 0 | 1+ | full suite |

**Total: 5 new files, ~55 modified files, 13 steps.**

---

## Parallelization notes

- Steps 1–3 are sequential (each depends on the previous)
- Step 4 depends on Step 1 (needs VaultContext)
- Step 5 is independent (can run after Step 1)
- Steps 6–8 depend on Steps 1–3 (need build_context)
- Steps 9–11 depend on Steps 6–8 (surfaces must pass ctx before tools can receive it)
- Step 12 depends on Steps 9–11 (workflows call tools)
- Step 13 depends on everything
