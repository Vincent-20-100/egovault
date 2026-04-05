# EgoVault — Project Status

> **This file is the live project state.** Updated at the end of every session.
> Any LLM must read this file to know exactly where things stand.
> Referenced from CLAUDE.md §9.

**Last updated:** 2026-04-03
**Last session branch:** `claude/brainstorming-pending-ideas-5zR2H`

---

## Next action

**Unified ingest workflow — PHASE 4 (IMPLEMENT) steps 1-10 done, step 11 (doc sync) in progress.**

Steps 1-10 complete: `IngestError` hierarchy, extractor registry, `workflows/ingest.py`, thin wrappers,
`parse_html` tool, `ingest_text` on all surfaces (API/CLI/MCP), tests.
Plan: `docs/superpowers/plans/2026-04-01-unified-ingest-plan.md` — step 11 = doc sync (current step).

Next priorities:
1. **Verify full test suite** — blocked by sqlite_vec availability in CI; run locally to confirm
2. **G13 comments audit** — apply commenting standard across entire codebase

---

## Active specs and plans

| Document | Phase | Status |
|----------|-------|--------|
| `specs/2026-03-31-unified-ingest-architecture.md` | VALIDATED | Steps 1-10 implemented |
| `plans/2026-04-01-unified-ingest-plan.md` | EXECUTING | Steps 1-10 done, step 11 in progress |
| `specs/2026-04-01-unified-ingest-notes.md` | DONE | Brainstorm decisions |
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
| **Unified ingest workflow** | **2026-04-03** | **Done — ingest.py + 7 extractors + thin wrappers** |

---

## Known technical debt

| Debt | Severity | Resolution plan |
|------|----------|----------------|
| ~~tools/ → infrastructure/ late imports~~ | ~~MAJOR~~ | **RESOLVED** — VaultContext |
| ~~core/logging.py → infrastructure.db~~ | ~~CRITICAL~~ | **RESOLVED** — callback injection |
| ~~DB lock in API tests~~ | ~~MAJOR~~ | **RESOLVED** — mock background threads in rate limit test |
| ~~app.state.settings backward compat~~ | ~~MINOR~~ | **RESOLVED** — removed, use ctx.settings |
| ~~fetch_subtitles → transcribe (tool→tool)~~ | ~~CRITICAL~~ | **RESOLVED** — handled inside youtube extractor in ingest.py |
| MCP create_note: business logic in wrapper | MAJOR | Move to tools/ in unified ingest refactor (not yet done) |
| Old workflow files (ingest_youtube/audio/pdf) | MINOR | Now thin wrappers — remove once all callers migrated |

---

## Pending tasks

- [x] **Unified ingest workflow** — steps 1-10 done; step 11 (doc sync) in progress
- [ ] **Post-VaultContext architecture audit** — verify all code (source + tests) uses ctx correctly, consistent fixture patterns, no stale infrastructure.db imports in tests, background threads always mocked
- [ ] **G13 comments audit** — review all existing code against G13 standard
- [ ] **Clean up thin wrappers** — remove `ingest_youtube.py`, `ingest_audio.py`, `ingest_pdf.py` once all callers migrated
- [x] **Doc sync** — ARCHITECTURE.md + DATABASES.md synced with implemented state
- [x] **Archive completed specs** — VaultContext spec/plan moved to archive
- [x] **Fix G1 guardrail violations** — 9 library name leaks fixed
- [x] **Fix test failures** — 420 tests passing (up from 355)
- [x] **Remove backward compat** — app.state.settings removed

---

## Roadmap (ordered by priority)

1. ~~**VaultContext refactoring**~~ — **DONE**
2. ~~**Post-VaultContext cleanup**~~ — **DONE**
3. **Post-VaultContext architecture audit** — catch stale patterns before they spread
4. ~~**Unified ingest workflow**~~ — **DONE** (steps 1-10; doc sync step 11 completing)
5. **ingest_text** — trivial once unified workflow exists
6. **G13 comments audit** — apply standard across codebase
7. **B2 — Security Phase 2** — needs spec + brainstorm
8. **Web ingestion** — needs dedicated security brainstorm (future)
9. **Frontend, search quality, monitoring** — see `docs/FUTURE-WORK.md`

---

## Session history

| Date | Branch | What was done |
|------|--------|---------------|
| 2026-03-31 | `claude/check-project-status-6VthL` | B1 embedding.dims fix, unified ingest spec, project audit (47 findings), CLAUDE.md rewrite, development workflow spec, audit spec |
| 2026-03-31 | `claude/brainstorm-ulBda` | VaultContext brainstorm → spec → plan → **FULL IMPLEMENTATION (13/13 steps)**. G13 rule added. Strategic vision (VISION.md). docs/superpowers/ reorganized. All tools, workflows, surfaces migrated to ctx. 355 tests pass, zero regressions. |
| 2026-04-01 | `claude/brainstorm-ulBda` | Post-VaultContext cleanup: fixed 9 DB lock errors (root cause: unmocked background threads in rate limit tests), fixed 10 ModuleNotFoundError tests (sys.modules stubs), removed app.state.settings backward compat. **374 tests pass, 0 failures.** |
| 2026-04-01 | `claude/brainstorming-pending-ideas-5zR2H` | Unified ingest brainstorm (7 decisions validated), spec updated, 11-step plan written. Phases 1-3 complete. |
