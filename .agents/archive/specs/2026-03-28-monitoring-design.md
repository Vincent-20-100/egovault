# Spec: Monitoring & Rating Stack

**Date:** 2026-03-28
**Status:** Validated, ready to implement
**Dependencies:** API spec (`2026-03-27-api-design.md`), evaluation spec (`2026-03-28-evaluation-design.md`), architecture spec

---

## Context and motivation

`tool_logs` already exists in `vault.db` via the `@loggable` decorator. It captures tool_name, input/output, duration, status, and error. What is missing:

- Cross-tool correlation: impossible to know which tool calls belong to the same ingest
- Data/operational separation: monitoring logs have no business being in `vault.db` (user data)
- Cost per workflow: no tracking of tokens consumed
- Reading via API/MCP: `.system.db` is not queryable without direct file access

This spec unifies observability + monitoring into a single stack, without a new module — by enriching `@loggable` and moving data to `.system.db`.

---

## Architectural decisions and their rationale

### D1 — Approach A: extend `@loggable`, no new module

**Decision:** `@loggable` is enriched with two fields (`run_id`, `token_count`). No `monitoring/tracer.py` or `monitoring/cost_tracker.py`.

**Why not a dedicated module:** `@loggable` already does 90% of the work. Adding a delegation layer for 10% additional functionality = complexity without value.

**Why not an API/MCP middleware:** does not capture direct tool calls (outside the API), loses per-step granularity.

**Benefit:** a single tracing mechanism for workflows, direct calls, and MCP sessions.

---

### D2 — `tool_logs` → `.system.db`

**Decision:** `tool_logs` leaves `vault.db` and joins `.system.db` with `workflow_runs` and `benchmark_runs` (benchmark spec).

**Why:** operational logs are not user data. Independent backup, separately queryable, consistent with the `vault.db` / `.system.db` separation of the architecture.

**Migration:** one-shot script in `scripts/temp/001_move_tool_logs_to_system_db.py` (convention established in CLAUDE.md).

---

### D3 — `run_id` via `contextvars`

**Decision:** the `run_id` is propagated via `contextvars.ContextVar`, not via function signatures.

**Why:** modifying the signatures of all tools to pass a `run_id` = massive debt and violation of the "tools = atomic functions without implicit side-effects" convention. `contextvars` is thread-safe and async-safe — each workflow or MCP session has its own value, invisible to other parallel executions.

**Benefit:** zero changes to existing tools.

---

### D4 — Read-only API

**Decision:** `.system.db` is fed exclusively by `@loggable` and workflows. API endpoints are read-only.

**Why:** writing to logs via API would open the door to inconsistent states. The source of truth is the execution code, not an external client.

---

### D5 — No Langfuse

**Decision:** no Langfuse integration or other external LLM tracing tool.

**Why:** contradicts the project's 100% local principle. Langfuse self-hosted = additional service to run. `.system.db` + `@loggable` cover the need without external dependency.

---

### D6 — Estimated cost via tokens

**Decision:** `token_count` per tool call. Estimated cost = `token_count × price_per_token` from `config/user.yaml`. No real LLM cost tracking (the LLM is external and optional).

**Why:** with the token count, cost can be estimated for any provider. The price mapping stays in user config, not hardcoded.

---

## `.system.db` schema

```sql
CREATE TABLE workflow_runs (
    run_id      TEXT PRIMARY KEY,
    workflow    TEXT NOT NULL,
    -- values: "ingest_youtube" | "ingest_audio" | "ingest_pdf" | "mcp_session" | "api_request"
    status      TEXT NOT NULL,
    -- values: "running" | "success" | "failed"
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    source_uid  TEXT   -- optional link to the ingested source in vault.db
);

CREATE TABLE tool_logs (
    uid          TEXT PRIMARY KEY,
    run_id       TEXT REFERENCES workflow_runs(run_id),
    tool_name    TEXT NOT NULL,
    input_json   TEXT,
    output_json  TEXT,
    duration_ms  INTEGER,
    token_count  INTEGER,   -- embedding + LLM tokens if available, NULL otherwise
    status       TEXT NOT NULL,   -- "success" | "failed"
    error        TEXT,
    timestamp    TEXT NOT NULL
);

-- benchmark_runs also lives in .system.db (evaluation spec)
-- CREATE TABLE benchmark_runs (...)  → see 2026-03-28-evaluation-design.md
```

`init_user_dir.py` creates `.system.db` with the three tables (`workflow_runs`, `tool_logs`, `benchmark_runs`) on initialization.

---

## `core/logging.py` — enhancements

```python
from contextvars import ContextVar, Token

_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)


def set_run_id(run_id: str) -> Token:
    """Called by workflow or MCP server before tool calls."""
    return _run_id.set(run_id)


def reset_run_id(token: Token) -> None:
    """Called in the workflow's finally block."""
    _run_id.reset(token)


def loggable(tool_name: str):
    """
    Decorator unchanged in its interface.
    Internal enhancements: run_id read from contextvars, token_count extracted from output.
    """
```

`token_count` is extracted automatically if the Pydantic output exposes a `token_count` or `tokens_used` field. Otherwise `NULL`.

---

## Usage in workflows

```python
# workflows/ingest_youtube.py
from core.logging import set_run_id, reset_run_id
from core.uid import generate_uid
from infrastructure.db import create_workflow_run, close_workflow_run

run_id = generate_uid()
create_workflow_run(system_db_path, run_id, workflow="ingest_youtube", source_uid=source.uid)
token = set_run_id(run_id)
try:
    transcribe(...)   # @loggable → tool_log with automatic run_id
    chunk(...)
    embed(...)
    create_note(...)
    close_workflow_run(system_db_path, run_id, status="success")
except Exception:
    close_workflow_run(system_db_path, run_id, status="failed")
    raise
finally:
    reset_run_id(token)
```

---

## Usage in the MCP server

```python
# mcp/server.py — per session or per tool call request
from core.logging import set_run_id, reset_run_id
from core.uid import generate_uid

run_id = generate_uid()
create_workflow_run(system_db_path, run_id, workflow="mcp_session")
token = set_run_id(run_id)
try:
    # MCP tool calls inherit the run_id
    ...
finally:
    reset_run_id(token)
```

---

## API

### Implemented endpoints

```
GET /api/monitoring/runs
  query params: workflow, status, limit (default 50), offset
  → lists workflow_runs from .system.db

GET /api/monitoring/runs/{run_id}
  → workflow_run + list of associated tool_logs
  → { run, tools: [{ tool_name, duration_ms, token_count, status, error, timestamp }] }

GET /api/monitoring/runs/{run_id}/cost
  → { run_id, total_tokens, estimated_cost_usd }
  → price_per_token read from config/user.yaml
```

All endpoints are **read-only**. No writes via API.

---

## MCP tool

```
tool: get_run_status
  args: { run_id: str }
  → calls GET /api/monitoring/runs/{run_id}
  → returns a human-readable summary: successful steps, failed steps, total duration, tokens
  → useful for diagnosing a problem without opening the frontend
```

---

## Migration

**Script:** `scripts/temp/001_move_tool_logs_to_system_db.py`

```
1. Creates .system.db with the new schema
2. Copies data from vault.db:tool_logs → .system.db:tool_logs
   (run_id = NULL, token_count = NULL for historical entries)
3. DROP TABLE tool_logs in vault.db
```

One-shot script, no fallback. `scripts/temp/` convention established in CLAUDE.md.

---

## `config/user.yaml` — addition

```yaml
monitoring:
  token_pricing:
    embedding_per_1k: 0.0001    # price for nomic-embed-text via Ollama (≈ free local)
    llm_per_1k_input: 0.003     # example OpenAI gpt-4o — adjust per provider
    llm_per_1k_output: 0.006
```

The cost calculation is purely estimated — displayed for informational purposes in the API and frontend.

---

## What is NOT in this spec

- User rating / feedback → future extension documented in the evaluation spec (`2026-03-28-evaluation-design.md`)
- Alerts or notifications on failure → out of scope
- Frontend dashboard → upcoming frontend spec
- Advanced aggregation / analytics → out of scope
