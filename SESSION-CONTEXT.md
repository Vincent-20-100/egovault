# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-01
**Last session:** `claude/brainstorm-ulBda`

---

## VaultContext — IMPLEMENTED & CLEANED UP

All 13 steps complete. Post-cleanup done. Key facts:

- **core/context.py**: VaultContext dataclass + 3 Protocols (EmbedFn, GenerateFn, WriteNoteFn)
- **infrastructure/vault_db.py**: VaultDB facade (~25 one-line delegation methods)
- **infrastructure/context.py**: build_context() factory wiring all providers
- **All tools/ receive ctx: VaultContext** — zero infrastructure/ imports in tools/
- **All workflows/ receive ctx** — zero infrastructure/ imports
- **All surfaces (MCP, API, CLI) build ctx** and pass it to tools
- **core/logging.py** uses callback injection (no infrastructure/ import)
- **app.state.settings backward compat removed** — use ctx.settings everywhere
- **374 tests pass**, 0 failures

### DB lock root cause (resolved)

`test_rate_limiting.py` fired 11 POST `/ingest/youtube` without mocking `_run_youtube`.
This spawned 11 background threads via ThreadPoolExecutor, all hitting vault.db.
Those threads held write locks when later seed fixtures tried to insert.
Fix: `@pytest.fixture(autouse=True)` that patches `_run_youtube` in that test file.

### Test stubs for optional dependencies

Tests for `anthropic`, `faster_whisper`, `youtube_transcript_api` use `sys.modules` stubs
(inject MagicMock before import) so tests pass without those packages installed.

---

## G13 — Code comments standard

Rule in CLAUDE.md §6. Applied to Wave 1 files. Full codebase audit pending.

Key principle: **concise, surgical, no dead weight**. A good name replaces a comment.

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach, upgrade if 3+ tools need LLM
- **build_context() is the single wiring point** — hooks for cache/metrics/fallback go here
- **This project is a reusable template** — every structural decision must be portable

---

## Traps to avoid

1. Don't write specs without brainstorming with the user
2. Use analogies for architecture jargon (restaurant kitchen, receptionist)
3. Don't forget the north star: 2-minute demo video
4. Don't over-engineer VaultDB — one-line delegations only
5. Don't mix features with refactoring
6. Rate limit / background thread tests MUST mock workflow functions to avoid DB locks

---

## Open questions for next session

1. **Monitoring spec gap** — run_id and token_count missing from tool_logs table
2. **Unified ingest** — now unblocked, needs brainstorm before implementation
