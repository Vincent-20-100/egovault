# EgoVault — Project Status

> **This file is the live project state.** Updated at the end of every session.
> Any LLM must read this file to know exactly where things stand.
> Referenced from CLAUDE.md §9.

**Last updated:** 2026-08-15
**Last session branch:** `main`

---

## Next action

1. **Execute Phase 2 (Visual & Complex Document Ingestion)** — `.meta/plans/2026-08-15-visual-and-document-ingestion-plan.md`
   - PyMuPDF4LLM structural layout parser & RapidOCR ONNX engine.
   - High-definition figure extraction & Markdown table parsing.
   - Multimodal PDF & OCR interactive inspection notebook (`notebooks/03_multimodal_pdf_and_ocr_inspection.ipynb`).

See `docs/user-guide/` for the user manual (12 chapters).
See `docs/VISION-KNOWLEDGE-COMPILER.md` for the Cognitive Architecture vision.
See `AGENTS.md` for universal multi-agent guidelines.
See `SESSION-CONTEXT.md` for detailed reasoning and active decisions.

---

## Active specs and plans

| Document | Phase | Status |
|----------|-------|--------|
| `AGENTS.md` | Universal Constitution | Active (Living Standard) |
| `.meta/WORKFLOW.md` | Development Process | Active (Living Standard) |
| `.meta/AUDIT-SPEC.md` | Audit Protocol | Active (Living Standard) |
| `.meta/plans/2026-08-15-golden-configuration-and-cleanup.md` | Milestone 0 | Shipped (v0.4.0) (518 passed / 0 failed) |
| `.meta/specs/2026-08-14-note-creation-semantic-clustering-spec.md` | Core Engine | Shipped (v0.4.0) |
| `.meta/plans/2026-08-15-note-creation-semantic-clustering-plan.md` | Phase 1 | Shipped (v0.4.0) (539 passed / 0 failed) |
| `.meta/specs/2026-08-15-interactive-visual-notebooks-spec.md` | DevTools & R&D | Shipped (v0.4.0) (Consolidated 2-Notebook Suite: 01 Benchmarks & 02 Showcase) |
| `.meta/specs/2026-08-16-tool-renaming-and-search-all-spec.md` | Core Engine | Shipped (v0.4.0) (541 passed / 0 failed) |
| `.meta/specs/2026-08-15-visual-and-document-ingestion-spec.md` | Ingest Engine | Shipped (v0.5.0) (547 passed / 0 failed) |
| `.meta/plans/2026-08-15-visual-and-document-ingestion-plan.md` | Phase 2 | Shipped (v0.5.0) (547 passed / 0 failed) |

## Vision documents

| Document | Topic |
|----------|-------|
| `docs/VISION-KNOWLEDGE-COMPILER.md` | Cognitive Architecture & Knowledge Compiler — North Star |
| `docs/TIMESTAMPS.md` | OpenTimestamps verification guide |

## Future specs (validated backlog)

| Document | Topic |
|----------|-------|
| `.meta/specs/future/2026-03-28-evaluation-design.md` | RAG benchmark |
| `.meta/specs/future/2026-03-28-semantic-cache-design.md` | Query caching |
| `.meta/specs/future/2026-03-28-reranking-design.md` | Search reranking (Cross-encoder) |
| `.meta/specs/future/2026-03-28-frontend-design.md` | Next.js frontend |
| `.meta/archive/specs/` | All implemented and superseded specs |
| `.meta/archive/plans/` | All implemented and archived plans |

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
| **README diagram overhaul** | **2026-04-27** | **Done — dual-layer RAG, parallel branches, Human/LLM Access split, color scheme** |
| **MCP Claude Desktop setup** | **2026-04-27** | **Done — `claude_desktop_config.json` + `docs/mcp/CLIENT-SETUP.md` created** |
| **curate() tier 0 (Librarian)** | **2026-05-16** | **Done — deterministic notes→chunks orchestration, MCP+CLI, 9 tests, 0 regression** |

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
| ~~RAG distance = L2 on unnormalized embeddings~~ | ~~CRITICAL~~ | **RESOLVED 2026-05-16** — cosine metric + normalized embeddings (`a30e443`), reembed script (`a1043e6`), verified semantically discriminant. curate() threshold now meaningful. |
| ~~7 pre-existing broken tests~~ | ~~MAJOR~~ | **RESOLVED 2026-05-17 (F4)** — audit (`.meta/audits/2026-05-17-pre-reinit-audit.md`) proved ZERO real product bugs: 5/7 = one test-isolation defect (TEST-C1, fixed `44f333b`), 2/7 = stale tests (TEST-M2/M3, fixed `c017db4`). **Suite now 481 pass / 0 fail / 1 skip, deterministic.** |
| **Deferred audit debt (2026-05-17)** | MAJOR/MINOR | Tracked in audit report: DB-M1 atomic purge_source, DB-M2 DB error wrapping, DB-M3 connection-leak (try/finally, ~50 funcs — the "DB lock" root cause), DB-M4 search ignores filters, SCRIPT-M1 reembed backup/probe, TEST-C2 no real semantic/ingest e2e test, TEST-M1 missing test files. Post-reinit. |
| ~~**Ollama/OpenAI LLM generation unimplemented**~~ | ~~MAJOR~~ | **RESOLVED 2026-05-17 (F5)** - ollama note generation implemented (brainstorm->spec->reviewed->plan->subagent-driven impl, ~7 tests). openai still deferred (do not implement partially). |
| ~~beautifulsoup4 + ruff undeclared in pyproject~~ | ~~MAJOR~~ | **RESOLVED 2026-05-16** — `beautifulsoup4` was already declared+committed (web-ingestion-V1, `0fab5b3`); only `ruff` was missing. Added to dev group (`chore` commit). pytest collects 476 tests, bs4 4.14.3 installed. |
| **save-progress skill missing preflight script** | MINOR | `scripts/save_progress_preflight.py` absent; skill's `uv run` fallback prunes the venv. Create script or fix skill. |
| **96 files unformatted (ruff format)** | MINOR | Pre-existing; `ruff format` not enforced. Run a formatting pass separately. |
| **`create_note` draft/active approval lifecycle has no real transitions** | MAJOR | **OPEN — NOT fixed, patched by hand.** `create_note` defaults `status="active"` (schema: `active`=human-approved). Its own docstring workflow presumes the human approved the content *before* the call — but nothing enforces that: there is no `status` param to let a caller mark a note unapproved, and no tool (`update_note` doesn't expose `status`; no other) can move a note `draft`→`active` or `active`→`draft`. Found 2026-08-14: an autonomous sub-agent created 4 notes via `create_note` with no human review step; they landed `active` (falsely "approved"). Worked around by direct SQL `UPDATE notes SET status='draft'` on the 4 rows — a stopgap, not a fix. Needs its own brainstorm→spec: `create_note status` param, `update_note` status field/approve-tool, and correcting `create_note`'s docstring + `.claude/rules/vault-usage.md` ("notes start as draft") which is only true for `generate_note_from_source`. |
| **README & pitch overhaul: Cognitive Architecture & Conceptual Vectorization** | MINOR | Overhaul `README.md` and intro docs to elevate the cognitive neuroscience parallel (hippocampus episodic buffer $\to$ sleep consolidation $\to$ neocortex semantic network $\to$ spreading activation) and the conceptual vectorization thesis (why vectorizing notes beats chunk RAG for LLM lateral reasoning) to the core product pitch. |

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
- [x] **README diagram overhaul** — dual-layer RAG pipeline, Human/LLM Access subgraphs, color scheme
- [x] **MCP Claude Desktop setup** — `claude_desktop_config.json` + `docs/mcp/CLIENT-SETUP.md`
- [x] **MCP Claude Code setup** — DONE: versioned `.mcp.json` at repo root, `CLIENT-SETUP.md` corrected (Claude Code uses `.mcp.json`, not settings.json). Active after Claude Code restart.
- [ ] **Push tags + run timestamps** — user action required: `git push origin --tags` + `bash scripts/timestamp-release.sh v0.X.0`
- [ ] **Real-world testing** — ingest actual sources, validate RAG + note generation quality
- [x] **curate() tool** — tier 0 DONE 2026-05-16 (deterministic; tier 1 LLM synthesis deferred)

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
13. **Large source synthesis** — spec written, needs plan + impl. **Principle clarified 2026-08-14** (see SESSION-CONTEXT.md): 1 source → N notes by semantic nucleus, not 1 note per source — invalidates the ad hoc single-note note-creation prompt used in this session's end-to-end test
14. **Search quality (reranking)** — needs brainstorm
15. ~~**Onboarding / DX (Getting Started guide)**~~ — **DONE** (docs/GETTING-STARTED.md)
16. **Evaluation framework** — needs brainstorm
17. ~~**curate() tool (librarian tier 0)**~~ — **DONE 2026-05-16** (tier 1 LLM synthesis deferred)
18. **Frontend** — see `docs/FUTURE-WORK.md`

---

## Session history

| Date | Branch | What was done |
|------|--------|---------------|
| 2026-05-29 | `main` | **curate() tier-1 base — brainstorm + spec + plan** (open question #7 resolved). Decided: base = librarian sub-agent + `/ask-vault` slash command shipped as a Claude Code plugin, using the host LLM (no API key). Selection method = recall-first hybrid RRF + wide net, precision delegated to the sub-agent. Output contract `{answer, used_source_uids}`. Verified MCP sampling is unsupported by Claude Code/Desktop today → tracked as debt (migrate later). Spec `0177202`, plan `4a1adf2`. No code yet — next session executes the 7-task plan. |
| 2026-05-21 | `main` | **curate() opt-in hybrid adoption** (`8911fda`) — `CurateConfig.use_hybrid_retrieval: bool = False` + `system.yaml` flag + `VaultDB.search_*_hybrid` exposed + `tools/vault/curate.py` branches on the flag. 1 TDD routing test. Suite 511/0/1skip. Then **full user-guide delivered**: `docs/user-guide/` 12 chapters (~2300 lines: concepts, install, config, providers, ingest, search-curate, notes, CLI, MCP, Obsidian, maintenance, troubleshooting) + Phase-1 synch of GETTING-STARTED/ARCHITECTURE/FUTURE-WORK/README. CLAUDE.md automatism **#8** added: doc-maintenance is non-negotiable on user-visible changes. 5 commits `ac5377b..9e92a64`. |
| 2026-05-21 | `main` | **RRF hybrid retrieval shipped** (experiment #1) — FTS5 mirror tables (`chunks_fts`/`notes_fts`, unicode61+remove_diacritics 2), `_rrf_fuse` helper, `search_chunks_hybrid`/`search_notes_hybrid`. 6 commits TDD (~85 lines prod + 13 tests, 0 new Python deps, FTS5 from SQLite stdlib). DB sync hooks on insert/update/delete; idempotent `init_db` backfill. Empirical eyeball on 4 thematic queries: 1 big win (Q2 finding-E case — exact-topic note promoted to rank 2 via BM25), 1 smaller win, 1 reorder, 5 neutral, **0 regression**. Suite 510/0/1skip. Audit: `.meta/audits/2026-05-21-rrf-hybrid-experiment-results.md`. Next: small slice to wire curate(). |
| 2026-05-20 | `main` | **Real local note-gen + tag-translit fix** — 25/25 notes (100%) on corpus; tag-slugify in both providers (NFKD→ASCII→lowercase→kebab); 2 TDD parity tests. |
| 2026-05-19 | `main` | **tech-watch ported** from metadev-protocol (skill shipped SKILL.md-only; `scripts/tech_watch/` package copied, `tech-watch` optional deps declared, operational via venv python). **uv ban LIFTED** — pyproject 100% complete (app+scripts+tests audited), `uv sync --all-extras` validated (496/0). **SOTA research**: 3 deep cards (claude-obsidian, PageIndex, TencentDB-Agent-Memory) + synthesis in `.meta/references/research/`. Emergent thesis: 3 independent projects reject pure cosine → finding E answer is hybrid/structural retrieval. Concrete next: RRF(BM25 FTS5, cosine) experiment; curate() tier-1 now needs a brainstorm (not just impl). |
| 2026-05-18 | `main` | **force_git_author hook fixed** (was appending `--author` to last segment of compound cmds; now after `commit` keyword; 5 TDD tests, suite 496/0). **History cleaned**: 8 mojibake commit messages (post-`v0.3.0`, OTS-safe) recovered via `filter-branch` + ASCII translit, tree byte-identical, force-pushed `--force-with-lease`, backup branch `backup-pre-histclean`. ASCII-commit rule + recovery recipe + OTS constraint in `.meta/GUIDELINES.md`. |
| 2026-05-17 | `main` | **F5 ollama LLM provider SHIPPED** - brainstorm->spec (architect+code reviewed, 11 fixes)->plan->subagent-driven TDD (6 tasks). `_generate_ollama` mirrors claude path, keyless local note gen, qwen2.5:7b-instruct target. Suite green. Chantier B (openai/providers.mode/wizard/OpenRouter) still open (10.4). |
| 2026-03-31 | `claude/check-project-status-6VthL` | B1 embedding.dims fix, unified ingest spec, project audit (47 findings), CLAUDE.md rewrite, development workflow spec, audit spec |
| 2026-03-31 | `claude/brainstorm-ulBda` | VaultContext brainstorm → spec → plan → **FULL IMPLEMENTATION (13/13 steps)**. G13 rule added. Strategic vision (VISION.md). docs/superpowers/ reorganized. All tools, workflows, surfaces migrated to ctx. 355 tests pass, zero regressions. |
| 2026-04-01 | `claude/brainstorm-ulBda` | Post-VaultContext cleanup: fixed 9 DB lock errors (root cause: unmocked background threads in rate limit tests), fixed 10 ModuleNotFoundError tests (sys.modules stubs), removed app.state.settings backward compat. **374 tests pass, 0 failures.** |
| 2026-04-01 | `claude/brainstorming-pending-ideas-5zR2H` | Unified ingest brainstorm (7 decisions validated), spec updated, 11-step plan written. Phases 1-3 complete. |
| 2026-04-03 | `claude/brainstorming-pending-ideas-5zR2H` | Unified ingest Phase 4 (11 steps). All audits. MCP/CLI G11 fix. Specs archived. Old wrappers deleted. **metadev-protocol adoption brainstorm** (5 decisions: Superpowers plugin, split CLAUDE.md, rename .meta/, hooks, /ship skill). |
| 2026-04-04 | `claude/brainstorming-pending-ideas-5zR2H` | **metadev-protocol adoption executed** — split CLAUDE.md (408→109 lines law + 193 lines mentor), renamed docs/superpowers/ → .meta/, created 3 project skills (save-progress, lint, test), configured Superpowers output paths. Git rebase completed and pushed. |
| 2026-04-05 | `claude/brainstorming-pending-ideas-5zR2H` | **B2 Security marked done** (already implemented). **Web ingestion V1** — full brainstorm→spec→plan→impl (SSRF protection, fetch_web, 2-tier extraction, web extractor, all surfaces). **Monitoring** — run_id contextvars, token_count/provider extraction, workflow_runs table, 3 API endpoints. Fixed 3 pre-existing test failures. 331 tests pass. |
| 2026-04-06 | `main` | **Git history cleanup** — 115 commits → 12 squashed, all authored by Vincent. **ADR-008 metadev changes** — attribution.commit="", permissions, rules/, pre-commit, SessionStart hook. **Large source synthesis brainstorm + spec** — cascade strategy, template reuse, presets. **Vault-usage rules** for MCP guidance. **MCP parity** — added ingest_youtube/audio/pdf tools + 10 tests. **Getting Started guide** — zero-to-first-note tutorial, Ollama + Claude Desktop MCP setup. |
| 2026-04-16 | `claude/check-project-status-6VthL` → `main` | **Product vision shift** — Knowledge Compiler + Librarian Agent pattern (inspired by Karpathy LLM Wiki + agentify). Two-layer architecture (RAG on sources + compiled knowledge on notes). Librarian as smart tool with isolated LLM call, not autonomous agent. Tiered approach (tier 0 deterministic, tier 1 with LLM). Pre-packaged agent for MCP clients. OpenTimestamps for IP antériority. All documented in FUTURE-WORK.md. |
| 2026-05-17 | `main` | **Étapes 5-6 DONE.** Data cleanup (live DB → `_trash`, reversible; egovault-data intact; corpus copied). Fresh DB reinit (corrected schema). **Real-condition ingest test**: 25 FR text sources, 0 fail, all rag_ready; curate() end-to-end works. Findings D (`.md` not accepted by CLI) + E (cosine ranking directional but imprecise on real FR — the TEST-C2 blind spot, made visible) → `.meta/audits/2026-05-17-real-ingest-test-results.md`. Next: étape 7 (F5 ollama gen + search-quality track). |
| 2026-05-17 | `main` | **curate() validated on live vault** (real data, end-to-end). **Pre-reinit audit** (3 parallel agents: DB/scripts/tests) → `.meta/audits/2026-05-17-pre-reinit-audit.md`: 7 F4 = ZERO product bugs. **5 critical fixes** (DB-C1 schema, SCRIPT-M2 dead migrations purged, TEST-C1 isolation, TEST-M2/M3 stale tests, DB-C2 cosine guard). **Suite 481 pass / 0 fail, deterministic.** Hook bug fixed (`664d953`). egovault-data preserved (local commit, not deleted). NEXT: étape 5 data cleanup + DB reinit (destructive, awaiting confirmation) → real ingestion test. |
| 2026-05-16 | `main` | **curate() tier 0 SHIPPED** — full plan executed (7 TDD tasks): `CuratedContext`/`CuratedSource` schema, `CurateConfig`, `tools/vault/curate.py` (deterministic notes→chunks, escalation, merge notes-first, per-item truncation), MCP `curate` tool, `egovault curate` CLI. 9 new tests, 477 pass / 7 pre-existing F4 fail / **0 regression**. Ripple docs updated (vault-usage, ARCHITECTURE, VISION). **F6 resolved** (bs4 already declared; ruff added to dev group). |
| 2026-05-16 | `main` | **F2 fully resolved** — cosine metric + normalized embeddings (`a30e443`), `reembed.py` script (`a1043e6`), dev DB migrated, verified semantically discriminant. Regression I introduced (zero-vector test embeddings under cosine) fixed (`48891bd`). curate() spec recalibrated, plan unblocked. **F6 discovered**: bs4/ruff undeclared in pyproject (save-progress skill's missing preflight script triggered `uv run` which pruned the venv). 468 pass / 7 pre-existing fail / 0 regression. |
| 2026-05-15 | `main` | **First real-world test** — curate() tier-0 brainstorm→spec→plan (`.meta/specs|plans/2026-05-15-curate-tier0-*`). Real YouTube ingest surfaced 5 findings (`.meta/audits/2026-05-15-real-world-test-findings.md`): F1 DB-bootstrap-in-build_context **fixed** (`160f27f`, verified end-to-end), F2 **CRITICAL** RAG L2/unnormalized distance breaks curate() threshold, F3 mojibake false alarm, F4 7 pre-existing broken tests, F5 ollama gen unimplemented. |
| 2026-05-15 | `main` | **MCP Claude Code setup** — versioned `.mcp.json` at repo root (project-scoped, checked in). Corrected `CLIENT-SETUP.md`: Claude Code uses `.mcp.json`, not `settings.json`; documented `claude mcp add -s user` alternative. Next: real-world testing. |
| 2026-04-27 | `main` | **README diagram overhaul** — dual-layer RAG pipeline (chunks_vec + notes_vec), parallel branches from transcription, Human/LLM Access split into separate subgraphs, green color scheme. **MCP Claude Desktop** — `claude_desktop_config.json` configured with absolute path, `docs/mcp/CLIENT-SETUP.md` created. |
