# EgoVault — Project Status

> **This file is the live project state.** Updated at the end of every session.
> Any LLM must read this file to know exactly where things stand.
> Referenced from CLAUDE.md §9.

**Last updated:** 2026-04-01
**Last session branch:** `claude/brainstorm-ulBda`

---

## Next action

**Post-VaultContext cleanup — DONE.** All tests passing (374), no DB lock issues.

Next priorities:
1. **Unified ingest workflow** — now unblocked by VaultContext
2. **G13 comments audit** — apply commenting standard across entire codebase

---

## Active specs and plans

| Document | Phase | Status |
|----------|-------|--------|
| `specs/2026-03-31-unified-ingest-architecture.md` | UNBLOCKED | Ready for planning |
| `specs/2026-03-31-development-workflow.md` | Active | The process we follow |
| `specs/2026-03-31-project-audit-spec.md` | Active | Reusable audit method |

## Future specs (validated, not yet implemented)

| Document | Topic |
|----------|-------|
| `specs/future/2026-03-28-evaluation-design.md` | RAG benchmark |
| `specs/future/2026-03-28-semantic-cache-design.md` | Query caching |
| `specs/future/2026-03-28-reranking-design.md` | Search reranking |
| `specs/future/2026-03-28-frontend-design.md` | Next.js frontend |
| `specs/future/2026-03-28-monitoring-design.md` | Monitoring (partial — run_id/token_count missing) |
| `specs/future/2026-03-29-security-design.md` | Security Phase 2 |

## Last audit

**Date:** 2026-03-31
**Results:** `docs/superpowers/audits/audit-results-2026-03-31.md`
**Summary:** 4 critical (architecture debt), 30 major, 13 minor.
**Main debt:** tools/ → infrastructure/ imports (22 violations) — **RESOLVED by VaultContext.**

---

## Implemented features (verified by audit)

| Feature | Date | Status |
|---------|------|--------|
| Hexagonal architecture | 2026-03 | Done |
| **VaultContext refactoring** | **2026-03-31** | **Done — G4 fully compliant** |
| Ingest workflows (youtube, audio, pdf) | 2026-03 | Done |
| MCP server (22+ tools) | 2026-03 | Done |
| FastAPI API (7 routers, 19 endpoints) | 2026-03 | Done |
| A1 — MCP flow fix | 2026-03-30 | Done |
| A2 — CLI | 2026-03-30 | Done |
| A3 — Delete operations | 2026-03-31 | Done |
| A4 — Internal LLM path | 2026-03-31 | Done |
| B1 — embedding.dims fix | 2026-03-31 | Done |
| **Post-VaultContext cleanup** | **2026-04-01** | **Done** |
| Test suite (374 tests) | 2026-04 | Done |

---

## Known technical debt

| Debt | Severity | Resolution plan |
|------|----------|----------------|
| ~~tools/ → infrastructure/ late imports~~ | ~~MAJOR~~ | **RESOLVED** — VaultContext |
| ~~core/logging.py → infrastructure.db~~ | ~~CRITICAL~~ | **RESOLVED** — callback injection |
| ~~DB lock in API tests~~ | ~~MAJOR~~ | **RESOLVED** — mock background threads in rate limit test |
| ~~app.state.settings backward compat~~ | ~~MINOR~~ | **RESOLVED** — removed, use ctx.settings |
| fetch_subtitles → transcribe (tool→tool) | CRITICAL | Workflow orchestration in unified ingest |
| MCP create_note: business logic in wrapper | MAJOR | Move to tools/ in unified ingest refactor |

---

## Pending tasks

- [ ] **G13 comments audit** — review all existing code against G13 standard
- [x] **Doc sync** — ARCHITECTURE.md + DATABASES.md synced with implemented state
- [x] **Archive completed specs** — VaultContext spec/plan moved to archive
- [x] **Fix G1 guardrail violations** — 9 library name leaks fixed
- [x] **Fix test failures** — 374 tests passing (up from 355)
- [x] **Remove backward compat** — app.state.settings removed

---

## Roadmap (ordered by priority)

1. ~~**VaultContext refactoring**~~ — **DONE**
2. ~~**Post-VaultContext cleanup**~~ — **DONE**
3. **Unified ingest workflow** — now unblocked by VaultContext
4. **ingest_text** — trivial once unified workflow exists
5. **G13 comments audit** — apply standard across codebase
6. **B2 — Security Phase 2** — needs spec + brainstorm
7. **Web ingestion** — needs dedicated security brainstorm (future)
8. **Frontend, search quality, monitoring** — see `docs/FUTURE-WORK.md`

---

## Session history

| Date | Branch | What was done |
|------|--------|---------------|
| 2026-03-31 | `claude/check-project-status-6VthL` | B1 embedding.dims fix, unified ingest spec, project audit (47 findings), CLAUDE.md rewrite, development workflow spec, audit spec |
| 2026-03-31 | `claude/brainstorm-ulBda` | VaultContext brainstorm → spec → plan → **FULL IMPLEMENTATION (13/13 steps)**. G13 rule added. Strategic vision (VISION.md). docs/superpowers/ reorganized. All tools, workflows, surfaces migrated to ctx. 355 tests pass, zero regressions. |
| 2026-04-01 | `claude/brainstorm-ulBda` | Post-VaultContext cleanup: fixed 9 DB lock errors (root cause: unmocked background threads in rate limit tests), fixed 10 ModuleNotFoundError tests (sys.modules stubs), removed app.state.settings backward compat. **374 tests pass, 0 failures.** |
