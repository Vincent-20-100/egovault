# Spec: Tool Renaming (query_vault), Dual-Space Search Mode 'all', and Function Standardization

**Date:** 2026-08-16  
**Status:** Spec-Ready  
**Related Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md` (Cognitive Architecture & Dual-Space Retrieval)  

---

## 1. Context & Motivation

1. **Eliminate Ambiguity (`curate` $\to$ `query_vault`):**
   The term `curate()` originally referred to Tier 3 Prefrontal Working Memory context assembly. However, in English and French, "curate" sounds like an administrative file maintenance action. For LLM agents (MCP) and human users (CLI), `query_vault` (CLI: `egovault query`) clearly describes the tool's true intent: **asking the knowledge vault a question and receiving assembled context with weighted confidence**.
   Per zero-alias clean code principles, `curate` will be completely renamed to `query_vault` across all layers without dragging legacy aliases.

2. **Unified Dual-Space Search (`search(mode='all')`):**
   `chunks_vec` (Tier 1) and `notes_vec` (Tier 2) share the exact same embedding model (e.g. `nomic-embed-text`, 768 dims) and live in the same metric space $[0, 2]$. Currently, `search()` only allows searching either `chunks` or `notes`. Adding `mode='all'` enables direct, non-orchestrated parametric search across both vector tables simultaneously.

3. **Tool Function Standardization:**
   Align `tools/vault/create_note.py` to export `create_note()` as its primary public function name, matching MCP and CLI conventions.

4. **Tag Vectorization (Future Gardening Backlog):**
   Document the strategic insight of vectorizing tags in `notes_vec` for semantic tag clustering, synonym normalization, and Obsidian graph gardening.

---

## 2. Comprehensive Renaming & API Surface Matrix

| Layer | Old Name / Path | New Name / Path | Usage / Signature |
|---|---|---|---|
| **Config (`system.yaml`)** | `curate:` | `query_vault:` | Settings block: `escalation_min_notes`, `escalation_max_distance`, `use_hybrid_retrieval`, etc. |
| **Core Tool (`tools/`)** | `tools/vault/curate.py` (`curate()`) | `tools/vault/query_vault.py` (`query_vault()`) | `query_vault(query, ctx, conversation_summary=None, filters=None, limit=5)` |
| **Core Tool (`tools/`)** | `tools/vault/create_note.py` (`create_note_from_content()`) | `tools/vault/create_note.py` (`create_note()`) | `create_note(content, ctx, source_uid=None)` |
| **Search Tool (`tools/`)** | `search(mode='chunks'\|'notes')` | `search(mode='chunks'\|'notes'\|'all')` | `search(query, ctx, filters=None, mode='all', limit=5)` |
| **MCP Tool (`mcp/`)** | `curate` | `query_vault` | `query_vault(query: str, filters: dict \| None = None, limit: int = 5) -> dict` |
| **CLI Command (`cli/`)** | `egovault curate <query>` | `egovault query <query>` | `cli/commands/query.py` |
| **FastAPI Router (`api/`)** | N/A | `POST /query` (`api/routers/query.py`) | `query_endpoint(body: QueryRequest, request: Request)` |

---

## 3. Detailed Technical Requirements

### 3.1 `query_vault()` Tool & Config
- Move `tools/vault/curate.py` $\to$ `tools/vault/query_vault.py`.
- Function signature: `query_vault(query: str, ctx: VaultContext, conversation_summary: str | None = None, filters: SearchFilters | None = None, limit: int = 5) -> CuratedContext`.
- Update `SystemConfig` in `core/config.py`: replace `curate: CurateConfig` with `query_vault: QueryVaultConfig` (or alias Pydantic field for config compatibility).
- Update `config/system.yaml`: top-level key `query_vault:`.

### 3.2 `search(mode='all')` Dual-Space Search
- Extend `tools/vault/search.py`: accept `mode in ("chunks", "notes", "all")`.
- When `mode == "all"`:
  - Query `search_notes` and `search_chunks` (or hybrid equivalents if enabled).
  - Convert note results to `SearchResult` with `mode="notes"` and chunk results with `mode="chunks"`.
  - Sort combined list by `distance` ascending and slice to `limit`.

### 3.3 MCP & CLI Surface Updates
- `mcp/server.py`: expose `@mcp.tool() def query_vault(...)`. Update `search` tool docstring and mode validation.
- `cli/commands/query.py`: `query` command in CLI main menu (`egovault query`).
- `cli/commands/search.py`: support `--mode all` option.

### 3.4 API Surface Updates
- Create `api/routers/query.py`: `POST /query` endpoint returning `CuratedContextResponse`.
- Update `api/routers/search.py`: support `mode="all"`.

---

## 4. Verification & Migration Strategy

1. **Unit Tests:** Update all `tests/tools/vault/test_curate.py` $\to$ `tests/tools/vault/test_query_vault.py`, `tests/cli/test_curate_cmd.py` $\to$ `tests/cli/test_query_cmd.py`, and test `search(mode='all')`.
2. **Notebook Suite:** Update `01_engine_benchmarks.ipynb` & `02_cognitive_explorer_demo.ipynb` calls from `curate` to `query_vault`.
3. **Documentation:** Update `docs/user-guide/`, `ARCHITECTURE.md`, `README.md`, `PROJECT-STATUS.md`, and `SESSION-CONTEXT.md`.
