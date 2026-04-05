# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-03
**Last session:** `claude/brainstorming-pending-ideas-5zR2H`

---

## Current focus: Unified Ingest Workflow — doc sync (step 11)

**Phase:** IMPLEMENT (Phase 4) — steps 1-10 complete, step 11 (doc sync) in progress
**Plan:** `docs/superpowers/plans/2026-04-01-unified-ingest-plan.md` (11 steps)
**Spec:** `docs/superpowers/specs/2026-03-31-unified-ingest-architecture.md`
**Brainstorm notes:** `docs/superpowers/specs/2026-04-01-unified-ingest-notes.md`

### What is implemented (steps 1-10)

- `IngestError` hierarchy in `core/errors.py` — base class with error_code/user_message/http_status
- `workflows/ingest.py` — unified pipeline with extractor registry (youtube, audio, video, pdf, livre, texte, html)
- Single entry point: `ingest(source_type, target, ctx)` dispatches to the correct extractor
- `tools/text/parse_html.py` — local HTML string → text (no network fetch)
- Old workflow files (`ingest_youtube.py`, `ingest_audio.py`, `ingest_pdf.py`) are now thin wrappers
- `ingest_text` exposed on all surfaces: API (`POST /ingest/text`), CLI (`egovault ingest`), MCP

### What's left

- **Step 11:** Doc sync — ARCHITECTURE.md, PROJECT-STATUS.md, SESSION-CONTEXT.md, CLAUDE.md (current step)
- **Test suite verification** — blocked by sqlite_vec in CI; must run locally to confirm pass count

### Key decisions from brainstorm (2026-04-01)

1. **`ctx: VaultContext` everywhere** — spec was written pre-VaultContext, all code uses ctx now
2. **Extractors = private functions** in `workflows/ingest.py` (G5, no premature abstraction)
3. **`parse_html` included in V1** — local only (HTML string → text), no security concern.
   Web *fetching* (SSRF etc.) is what requires the security brainstorm, not local parsing
4. **`IngestError` structured hierarchy** — base class with error_code/user_message/http_status,
   `LargeFormatError` migrated to inherit from it
5. **Thin wrappers for backward compat** — old workflow files become one-line delegations.
   Tracked as debt to clean up in a future session
6. **Crash recovery deferred** — not critical for refactoring, documented in spec §16
7. **`source_assets` table deferred** — no empty tables for unimplemented features, spec §15

---

## VaultContext — IMPLEMENTED & STABLE

All tools/workflows/surfaces use `ctx: VaultContext`. 374 tests pass.
No need to revisit — this is the foundation for unified ingest.

Key facts for reference:
- `core/context.py`: VaultContext dataclass + 3 Protocols
- `infrastructure/context.py`: `build_context()` factory
- Tools receive `ctx`, never import `infrastructure/`

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **This project is a reusable template** — every structural decision must be portable

---

## Traps to avoid

1. Don't write specs without brainstorming with the user
2. Use analogies for architecture jargon
3. Don't forget the north star: 2-minute demo video
4. Don't over-engineer VaultDB — one-line delegations only
5. Don't mix features with refactoring
6. Rate limit / background thread tests MUST mock workflow functions to avoid DB locks
7. **Spec was pre-VaultContext** — all code examples in spec use `settings`, actual code uses `ctx`
8. **Mock `_run_ingest` in API tests** (not type-specific runners) to avoid DB locks

---

## Deferred items (must be documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| Crash recovery (`recover_source`) | Spec §16, brainstorm note F | After unified ingest stable |
| `source_assets` table | Spec §15, brainstorm note G | When image handling implemented |
| Web ingestion | Spec §2.1 Family C | After security brainstorm |
| Clean up thin wrappers | PROJECT-STATUS.md pending tasks | After all callers migrated |
| Post-VaultContext architecture audit | PROJECT-STATUS.md | After unified ingest |
| G13 comments audit | PROJECT-STATUS.md | After unified ingest |

---

## Open questions (require interactive discussion)

1. **Monitoring spec gap** — run_id and token_count missing from tool_logs table
2. **Web ingestion security brainstorm** — needed before any network-facing fetch code
