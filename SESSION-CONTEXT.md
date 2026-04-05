# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-05
**Last session:** `claude/brainstorming-pending-ideas-5zR2H`

---

## Current state: Web ingestion + Monitoring shipped

Codebase is stable with two major features added this session:
1. **Web ingestion V1** — full pipeline from URL to RAG-ready source
2. **Monitoring** — workflow run tracking with observability

**331 tests pass, 0 failures.**

**Next priority:** **Search quality (reranking)** — needs brainstorm

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **This project is a reusable template** — every structural decision must be portable
- **Unified ingest with extractor registry** — add a source type = add an extractor function + register it
- **create_note_from_content()** builds system fields inside the tool — MCP/CLI/API are routing-only

### Web ingestion architecture (new)

- **SSRF protection** in `core/security.py` — private IP rejection, DNS rebinding defense, cloud metadata blocking
- **2-tier extraction** — Tier 0 (parse_html/bs4, always available), Tier 1 (trafilatura, optional dep)
- **tools/web/ package** — separate from tools/text/ because web content is mixed (text+structure), not pure text
- **httpx streaming** with size limits and post-redirect DNS re-validation

### Monitoring architecture (new)

- **run_id via contextvars** — zero changes to tool signatures, transparent to all @loggable-decorated tools
- **Token count auto-extraction** — checks result for `token_count`/`tokens_used`/`total_tokens` attributes
- **Provider captured from @loggable decorator** — `@loggable("embed_tool", provider="ollama")`
- **workflow_runs table** — tracks pipeline runs with status, timing, source_uid linkage
- **tool_logs.run_id is plain TEXT** (no FK) — allows standalone tool calls without a workflow run

---

## Traps to avoid

1. Don't write specs without brainstorming with the user
2. Use analogies for architecture jargon
3. Don't forget the north star: 2-minute demo video
4. Don't over-engineer VaultDB — one-line delegations only
5. Don't mix features with refactoring
6. Rate limit / background thread tests MUST mock `_submit_job` to avoid DB locks
7. Mock `_run_ingest` (not old `_run_youtube`) in integration tests
8. `create_note` (low-level) takes NoteSystemFields; `create_note_from_content` (high-level) builds them
9. When editing CLAUDE.md, keep it ≤110 lines — detailed rules go in GUIDELINES.md
10. Superpowers output paths override is in CLAUDE.md §7, NOT in skill wrappers
11. PostToolUse ruff hook was deferred — `$FILE` variable doesn't exist in hook context
12. pypdf tests need `patch.dict(sys.modules, {"pypdf": mock})` — env has broken cryptography module
13. tool_logs.run_id must NOT have FK to workflow_runs — standalone tool calls have no run

---

## Deferred items (must be documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| Crash recovery (`recover_source`) | Archive spec §16, brainstorm note F | After web ingest or monitoring |
| `source_assets` table | Archive spec §15, brainstorm note G | When image handling implemented |
| Web ingestion V2 (batch, JS rendering) | `.meta/specs/2026-04-05-web-ingestion-spec.md` §Future | When single-page is validated |
| API test seed fixtures | PROJECT-STATUS.md debt | When fixture pattern refactored |
| System DB facade | PROJECT-STATUS.md debt | If 3+ callers need system DB via ctx |
| PostToolUse ruff hook | `.meta/specs/2026-04-03-metadev-protocol-adoption-notes.md` | When Claude Code exposes `$FILE` in hooks |

---

## Open questions (require interactive discussion)

1. **Search quality (reranking)** — what approach? The spec (`specs/future/2026-03-28-reranking-design.md`) needs brainstorm
2. **Evaluation framework** — priority vs search quality? User said "monitoring then search quality, we'll decide next later"
3. **ARCHITECTURE.md location** — move from `docs/architecture/` to `.meta/`? Or keep separate since it's a permanent doc?
