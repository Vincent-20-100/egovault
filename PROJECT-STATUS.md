# EgoVault — Project Status

> **This file is the live project state.** Updated at the end of every session.
> Any LLM must read this file to know exactly where things stand.
> Referenced from CLAUDE.md §9.

**Last updated:** 2026-04-16
**Last session branch:** `claude/check-project-status-6VthL`

---

## Next action

**1. Push tags + run OpenTimestamps** — tags v0.1.0/v0.2.0/v0.3.0 created locally but not pushed.
Run from your machine: `git push origin --tags` then `bash scripts/timestamp-release.sh v0.X.0` for each.
OTS calendar servers are unreachable from sandbox — must be done locally.

**2. Real-world testing** — ingest actual sources (YouTube, PDF, web), test RAG + note generation quality.
The system has never been tested with real data — all tests are mocked.

**3. VaultContext brainstorm** — interactive session to design curate() tool (first step toward librarian pattern).

See `docs/VISION-KNOWLEDGE-COMPILER.md` for the full Knowledge Compiler vision.
See `docs/FUTURE-WORK.md` § "Architecture pivot" for implementation roadmap.
See `SESSION-CONTEXT.md` for detailed reasoning and open questions.

---

## Active specs and plans

| Document | Phase | Status |
|----------|-------|--------|
| `specs/2026-03-31-development-workflow.md` | Active | The process we follow |
| `specs/2026-03-31-project-audit-spec.md` | Active | Reusable audit method |
| `specs/2026-04-03-metadev-protocol-adoption-spec.md` | Implemented | Done |

## Vision documents

| Document | Topic |
|----------|-------|
| `docs/VISION-KNOWLEDGE-COMPILER.md` | Knowledge Compiler + Librarian Agent pattern — the north star |
| `docs/TIMESTAMPS.md` | OpenTimestamps verification guide |

## Future specs (validated, not yet implemented)

| Document | Topic |
|----------|-------|
| `specs/future/2026-03-28-evaluation-design.md` | RAG benchmark |
| `specs/future/2026-03-28-semantic-cache-design.md` | Query caching |
| `specs/future/2026-03-28-reranking-design.md` | Search reranking |
| `specs/future/2026-03-28-frontend-design.md` | Next.js frontend |
| `specs/2026-04-06-large-source-synthesis-spec.md` | Large source note generation (cascade, presets) |
| ~~`specs/future/2026-03-28-monitoring-design.md`~~ | ~~Monitoring~~ → **implemented & archived** |
| ~~`specs/future/2026-03-29-security-design.md`~~ | ~~Security Phase 2~~ → **archived** |

## Last audit

**Date:** 2026-04-03
**Scope:** Post-VaultContext architecture audit + G13 comments audit
**Summary:** Broken test mocks fixed, 10 test files migrated to ctx.db, 20 files cleaned for G13.
**Previous:** 2026-03-31 — 4 critical, 30 major, 13 minor (all resolved).

---

## Implemented features (verified by audit)

| Feature | Date | Status |
|---------|------|--------|
| Hexagonal architecture | 2026-03 | Done |
| **VaultContext refactoring** | **2026-03-31** | **Done — G4 fully compliant** |
| Ingest workflows (youtube, audio, pdf) | 2026-03 | Done |
| MCP server (22+ tools) | 2026-03 | Done |
| FastAPI API (8 routers, 22 endpoints) | 2026-03 | Done |
| A1 — MCP flow fix | 2026-03-30 | Done |
| A2 — CLI | 2026-03-30 | Done |
| A3 — Delete operations | 2026-03-31 | Done |
| A4 — Internal LLM path | 2026-03-31 | Done |
| B1 — embedding.dims fix | 2026-03-31 | Done |
| **Post-VaultContext cleanup** | **2026-04-01** | **Done** |
| Test suite (331 tests) | 2026-04 | Done |
| **Unified ingest workflow** | **2026-04-03** | **Done — 7 extractors, ingest_text on all surfaces** |
| **Post-VaultContext architecture audit** | **2026-04-03** | **Done — broken mocks fixed, ctx.db migration** |
| **G13 comments audit** | **2026-04-03** | **Done — 20 files cleaned** |
| **MCP/CLI create_note G11 fix** | **2026-04-03** | **Done — business logic moved to tool** |
| **Old workflow wrappers cleanup** | **2026-04-03** | **Done — deleted ingest_youtube/audio/pdf + tests** |
| **metadev-protocol adoption** | **2026-04-04** | **Done — split CLAUDE.md, .meta/ workspace, 3 skills, output paths** |
| **B2 — Security Phase 1+2** | **2026-04-04** | **Done — all hardening implemented, 30 tests pass, spec archived** |
| **Web ingestion V1** | **2026-04-05** | **Done — single URL fetch, SSRF protection, 2-tier extraction, 4 e2e tests** |
| **Monitoring (run tracking + observability)** | **2026-04-05** | **Done — run_id contextvars, token_count/provider extraction, workflow_runs table, 3 API endpoints, 6 new tests** |
| **Knowledge Compiler vision** | **2026-04-16** | **Done — VISION-KNOWLEDGE-COMPILER.md, 3-tier architecture, librarian pattern** |
| **OpenTimestamps setup** | **2026-04-16** | **Done — script, docs, v0.1.0/v0.2.0/v0.3.0 tags (awaiting user push + stamp)** |

---

## Known technical debt

| Debt | Severity | Resolution plan |
|------|----------|----------------|
| ~~tools/ → infrastructure/ late imports~~ | ~~MAJOR~~ | **RESOLVED** — VaultContext |
| ~~core/logging.py → infrastructure.db~~ | ~~CRITICAL~~ | **RESOLVED** — callback injection |
| ~~DB lock in API tests~~ | ~~MAJOR~~ | **RESOLVED** — mock _submit_job in rate limit/integration tests |
| ~~app.state.settings backward compat~~ | ~~MINOR~~ | **RESOLVED** — removed, use ctx.settings |
| ~~fetch_subtitles → transcribe (tool→tool)~~ | ~~CRITICAL~~ | **RESOLVED** — handled inside youtube extractor in ingest.py |
| ~~MCP create_note: business logic in wrapper~~ | ~~MAJOR~~ | **RESOLVED** — create_note_from_content() in tools/ |
| ~~Old workflow files (ingest_youtube/audio/pdf)~~ | ~~MINOR~~ | **RESOLVED** — deleted, all callers use workflows.ingest |
| API test fixtures: direct infrastructure.db imports | MINOR | Seed fixtures (session-scoped, no `client`) use raw DB — refactor when fixture pattern allows |
| System DB operations in tests | INFO | Jobs/system DB not in VaultDB — acceptable, consider facade later |

---

## Pending tasks

- [x] **Unified ingest workflow** — all 11 steps done, specs archived
- [x] **Post-VaultContext architecture audit** — mocks fixed, ctx.db migration done
- [x] **G13 comments audit** — 20 files cleaned in 2 passes
- [x] **MCP/CLI create_note G11 fix** — business logic moved to tool
- [x] **Archive unified ingest specs** — moved to archive/
- [x] **Clean up thin wrappers** — deleted ingest_youtube/audio/pdf + tests
- [x] **Doc sync** — ARCHITECTURE.md + DATABASES.md synced with implemented state
- [x] **Archive completed specs** — VaultContext + unified ingest specs/plans moved to archive
- [x] **metadev-protocol adoption** — DONE: split CLAUDE.md (law+mentor), renamed .meta/, added skills, output paths configured
- [x] **B2 — Security Phase 1+2** — DONE: all pre-launch docs + all hardening items already implemented. 30 security tests pass. Spec archived.
- [x] **Web ingestion V1** — DONE: fetch_web tool, SSRF protection, parse_html/trafilatura extraction, web extractor in ingest pipeline, API/CLI/MCP surfaces, 4 e2e tests.
- [x] **Monitoring (run tracking)** — DONE: run_id via contextvars, token_count/provider auto-extraction, workflow_runs table, 3 API endpoints (/monitoring/runs), 6 new tests.
- [x] **Knowledge Compiler vision doc** — DONE: `docs/VISION-KNOWLEDGE-COMPILER.md` — 3-tier knowledge architecture, librarian as smart tool, tiered curate(), pre-packaged agent for MCP clients.
- [x] **OpenTimestamps setup** — DONE: `scripts/timestamp-release.sh`, `docs/TIMESTAMPS.md`, `.meta/plans/2026-04-16-opentimestamps.md`. Tags created locally (v0.1.0, v0.2.0, v0.3.0). User must push tags + run stamps from their machine.
- [ ] **Push tags + run timestamps** — user action required: `git push origin --tags` + `bash scripts/timestamp-release.sh v0.X.0`
- [ ] **Real-world testing** — ingest actual sources, validate RAG + note generation quality
- [ ] **curate() tool** — first concrete step toward librarian pattern

---

## Roadmap (ordered by priority)

1. ~~**VaultContext refactoring**~~ — **DONE**
2. ~~**Post-VaultContext cleanup**~~ — **DONE**
3. ~~**Post-VaultContext architecture audit**~~ — **DONE**
4. ~~**Unified ingest workflow**~~ — **DONE**
5. ~~**ingest_text**~~ — **DONE** (part of unified ingest)
6. ~~**G13 comments audit**~~ — **DONE**
7. ~~**metadev-protocol adoption**~~ — **DONE**
8. ~~**B2 — Security Phase 1+2**~~ — **DONE**
9. ~~**Web ingestion V1**~~ — **DONE**
10. ~~**Monitoring (run tracking)**~~ — **DONE**
11. ~~**Knowledge Compiler vision**~~ — **DONE** (docs/VISION-KNOWLEDGE-COMPILER.md)
12. ~~**OpenTimestamps setup**~~ — **DONE** (script + docs, user must push tags + stamp)
13. **Large source synthesis** — spec written, needs plan + impl
14. **Search quality (reranking)** — needs brainstorm
15. ~~**Onboarding / DX (Getting Started guide)**~~ — **DONE** (docs/GETTING-STARTED.md)
16. **Evaluation framework** — needs brainstorm
17. **curate() tool (librarian tier 0)** — first step toward Knowledge Compiler
18. **Frontend** — see `docs/FUTURE-WORK.md`

---

## Session history

| Date | Branch | What was done |
|------|--------|---------------|
| 2026-03-31 | `claude/check-project-status-6VthL` | B1 embedding.dims fix, unified ingest spec, project audit (47 findings), CLAUDE.md rewrite, development workflow spec, audit spec |
| 2026-03-31 | `claude/brainstorm-ulBda` | VaultContext brainstorm → spec → plan → **FULL IMPLEMENTATION (13/13 steps)**. G13 rule added. Strategic vision (VISION.md). docs/superpowers/ reorganized. All tools, workflows, surfaces migrated to ctx. 355 tests pass, zero regressions. |
| 2026-04-01 | `claude/brainstorm-ulBda` | Post-VaultContext cleanup: fixed 9 DB lock errors (root cause: unmocked background threads in rate limit tests), fixed 10 ModuleNotFoundError tests (sys.modules stubs), removed app.state.settings backward compat. **374 tests pass, 0 failures.** |
| 2026-04-01 | `claude/brainstorming-pending-ideas-5zR2H` | Unified ingest brainstorm (7 decisions validated), spec updated, 11-step plan written. Phases 1-3 complete. |
| 2026-04-03 | `claude/brainstorming-pending-ideas-5zR2H` | Unified ingest Phase 4 (11 steps). All audits. MCP/CLI G11 fix. Specs archived. Old wrappers deleted. **metadev-protocol adoption brainstorm** (5 decisions: Superpowers plugin, split CLAUDE.md, rename .meta/, hooks, /ship skill). |
| 2026-04-04 | `claude/brainstorming-pending-ideas-5zR2H` | **metadev-protocol adoption executed** — split CLAUDE.md (408→109 lines law + 193 lines mentor), renamed docs/superpowers/ → .meta/, created 3 project skills (save-progress, lint, test), configured Superpowers output paths. Git rebase completed and pushed. |
| 2026-04-05 | `claude/brainstorming-pending-ideas-5zR2H` | **B2 Security marked done** (already implemented). **Web ingestion V1** — full brainstorm→spec→plan→impl (SSRF protection, fetch_web, 2-tier extraction, web extractor, all surfaces). **Monitoring** — run_id contextvars, token_count/provider extraction, workflow_runs table, 3 API endpoints. Fixed 3 pre-existing test failures. 331 tests pass. |
| 2026-04-06 | `main` | **Git history cleanup** — 115 commits → 12 squashed, all authored by Vincent. **ADR-008 metadev changes** — attribution.commit="", permissions, rules/, pre-commit, SessionStart hook. **Large source synthesis brainstorm + spec** — cascade strategy, template reuse, presets. **Vault-usage rules** for MCP guidance. **MCP parity** — added ingest_youtube/audio/pdf tools + 10 tests. **Getting Started guide** — zero-to-first-note tutorial, Ollama + Claude Desktop MCP setup. |
| 2026-04-16 | `claude/check-project-status-6VthL` → `main` | **Product vision shift** — Knowledge Compiler + Librarian Agent pattern (inspired by Karpathy LLM Wiki + agentify). Two-layer architecture (RAG on sources + compiled knowledge on notes). Librarian as smart tool with isolated LLM call, not autonomous agent. Tiered approach (tier 0 deterministic, tier 1 with LLM). Pre-packaged agent for MCP clients. OpenTimestamps for IP antériority. All documented in FUTURE-WORK.md. |
