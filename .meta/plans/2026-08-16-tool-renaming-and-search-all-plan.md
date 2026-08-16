# Plan: Tool Renaming (query_vault), Search Mode 'all', and Interface Standardization

**Goal:** Cleanly rename `curate` to `query_vault` across all 5 layers (config, tools, MCP, CLI, API), add `mode='all'` to `search()`, align `create_note()`, and update test suite & documentation with zero legacy alias debt.

**Spec:** `.meta/specs/2026-08-16-tool-renaming-and-search-all-spec.md`

---

## Task 1: Config Layer (`query_vault` Config)

- **Files:** `core/config.py`, `config/system.yaml`, `tests/core/test_config.py`
- **Steps:**
  1. Rename `CurateConfig` $\to$ `QueryVaultConfig` (or keep alias for Pydantic backward compat) in `core/config.py`.
  2. Update `SystemConfig`: `query_vault: QueryVaultConfig = Field(default_factory=QueryVaultConfig)`.
  3. Update `config/system.yaml`: top-level key `query_vault:`.
  4. Update `tests/core/test_config.py` assertions.

---

## Task 2: Core Tools Rename & Update (`query_vault.py`, `create_note.py`)

- **Files:** `tools/vault/query_vault.py` (renamed from `curate.py`), `tools/vault/create_note.py`, `tests/tools/vault/test_query_vault.py`
- **Steps:**
  1. Move `tools/vault/curate.py` $\to$ `tools/vault/query_vault.py`. Rename public function `@loggable("query_vault") def query_vault(...)`.
  2. Update `tools/vault/create_note.py`: export `create_note()` as alias/primary name for `create_note_from_content()`.
  3. Rename test file `tests/tools/vault/test_curate.py` $\to `tests/tools/vault/test_query_vault.py` and update imports/calls.

---

## Task 3: Dual-Space Search Mode `'all'` (`tools/vault/search.py`)

- **Files:** `tools/vault/search.py`, `tests/tools/vault/test_search.py`
- **Steps:**
  1. Update `search()` mode validation to accept `("chunks", "notes", "all")`.
  2. When `mode == "all"`, query both `search_notes` and `search_chunks` (or hybrid versions if `use_hybrid_retrieval` is enabled), tag results, sort by distance, and slice to `limit`.
  3. Add TDD unit test in `tests/tools/vault/test_search.py` for `mode='all'`.

---

## Task 4: MCP Server Update (`mcp/server.py`)

- **Files:** `mcp/server.py`, `tests/mcp/test_server.py`
- **Steps:**
  1. Replace `@mcp.tool() def curate(...)` with `@mcp.tool() def query_vault(...)`.
  2. Update `search` tool docstring to explain `mode='all'`.
  3. Update MCP tests in `tests/mcp/test_server.py`.

---

## Task 5: CLI Commands Update (`cli/`)

- **Files:** `cli/commands/query.py` (renamed from `curate.py`), `cli/main.py`, `cli/commands/search.py`, `tests/cli/test_query_cmd.py`
- **Steps:**
  1. Rename `cli/commands/curate.py` $\to$ `cli/commands/query.py`.
  2. Register `query` command in `cli/main.py` (`egovault query`).
  3. Add `--mode all` support to `cli/commands/search.py`.
  4. Update CLI tests in `tests/cli/test_query_cmd.py`.

---

## Task 6: FastAPI Router Update (`api/routers/`)

- **Files:** `api/routers/query.py` (new router), `api/routers/search.py`, `api/main.py`
- **Steps:**
  1. Create `api/routers/query.py` with `POST /query`.
  2. Include `query` router in `api/main.py`.
  3. Support `mode="all"` in `api/routers/search.py`.

---

## Task 7: Notebooks, Specs & Documentation Sync

- **Files:** `notebooks/`, `docs/user-guide/`, `SESSION-CONTEXT.md`, `PROJECT-STATUS.md`
- **Steps:**
  1. Update `notebooks/demo_engine_benchmarks.py`, `notebooks/demo_cognitive_explorer_demo.py`, `.ipynb` cells.
  2. Update all user-guide chapters in `docs/user-guide/` referencing `curate` to `query_vault` / `egovault query`.
  3. Update `SESSION-CONTEXT.md` and `PROJECT-STATUS.md`.
