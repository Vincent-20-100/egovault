# Brainstorm: Monitoring Implementation

**Date:** 2026-04-05
**Status:** Brainstorm complete — spec already exists
**Existing spec:** `.meta/specs/future/2026-03-28-monitoring-design.md`

---

## Decisions

### A — Provider field
**Decision:** Add `provider` column to `tool_logs` (nullable TEXT).
- Tracks which provider (ollama, openai, anthropic) was used per tool call
- NULL for tools that don't call a provider
- Documented in ARCHITECTURE.md §7.3 but was missing from spec schema

### B — Migration
**Decision:** Drop `tool_logs` from `vault.db`, add new columns to `.system.db`.
- `tool_logs` already exists in both DBs — just clean up `vault.db`
- Add `run_id`, `token_count`, `provider` columns to `.system.db:tool_logs`
- Add `workflow_runs` table to `.system.db`

### C — API endpoints
**Decision:** Implement all 3 monitoring endpoints.
- `GET /api/monitoring/runs` — list workflow runs
- `GET /api/monitoring/runs/{run_id}` — workflow + tool_logs detail
- `GET /api/monitoring/runs/{run_id}/cost` — estimated token cost
