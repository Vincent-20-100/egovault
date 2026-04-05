# Plan: Monitoring Implementation

**Date:** 2026-04-05
**Spec:** `.meta/specs/future/2026-03-28-monitoring-design.md`
**Brainstorm:** `.meta/specs/2026-04-05-monitoring-brainstorm.md`

---

## Phase 1 — Schema + DB functions

**Step 1: Schema changes in `infrastructure/db.py`**
- Add `workflow_runs` table to `_SYSTEM_SCHEMA_SQL`
- Add `run_id`, `token_count`, `provider` columns to `.system.db:tool_logs`
- Drop `tool_logs` from `_VAULT_SCHEMA_SQL` (already in .system.db)
- Add DB functions: `create_workflow_run()`, `close_workflow_run()`, `get_workflow_runs()`, `get_workflow_run_detail()`
- Update `insert_tool_log()` to accept `run_id`, `token_count`, `provider`

## Phase 2 — Core logging enrichment

**Step 2: run_id via contextvars in `core/logging.py`**
- Add `_run_id: ContextVar[str | None]` 
- Add `set_run_id(run_id) -> Token` and `reset_run_id(token)`
- Update `@loggable` to read `_run_id.get(None)` and pass to `_write_log`

**Step 3: token_count + provider extraction in `core/logging.py`**
- Update `@loggable` to auto-extract `token_count` from result (if present)
- Add optional `provider` param to `@loggable(tool_name, provider=None)`
- Update `_write_log` signature: add `run_id`, `token_count`, `provider`
- Update callback signature + all callers (api/main.py, mcp/server.py)

## Phase 3 — Workflow integration

**Step 4: Wire `set_run_id()` in `workflows/ingest.py`**
- Create workflow run at pipeline start
- `set_run_id()` → all tool calls automatically tagged
- `close_workflow_run()` on success or failure
- `reset_run_id()` in finally block

## Phase 4 — API endpoints

**Step 5: Monitoring router `api/routers/monitoring.py`**
- `GET /monitoring/runs` — list runs with filters (status, workflow)
- `GET /monitoring/runs/{run_id}` — run detail + tool_logs
- `GET /monitoring/runs/{run_id}/cost` — token aggregation + cost estimate
- Response models in `api/models.py`
- Register router in `api/main.py`

## Phase 5 — Tests + cleanup

**Step 6: Tests**
- `tests/core/test_logging.py` — run_id propagation, token_count extraction, provider
- `tests/infrastructure/test_db.py` — workflow_runs CRUD
- `tests/workflows/test_ingest.py` — verify run_id set during pipeline
- `tests/api/routers/test_monitoring.py` — 3 endpoint tests

**Step 7: Docs + finalize**
- Update ARCHITECTURE.md (remove "not yet implemented" from monitoring)
- Update PROJECT-STATUS.md
- Archive monitoring spec
