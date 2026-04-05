# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-04
**Last session:** `claude/brainstorming-pending-ideas-5zR2H`

---

## Current state: Clean codebase, metadev-protocol adopted

All major refactoring is complete. Codebase is stable. Development process is now formalized
with the metadev-protocol patterns (split CLAUDE.md, .meta/ workspace, project skills).

**What was done this session:**
- Completed git rebase (conflicts from previous session resolved)
- Pushed metadev-protocol adoption to main
- Merged main into feature branch

**Next priority:** **B2 — Security Phase 2** — needs brainstorm

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **This project is a reusable template** — every structural decision must be portable
- **Unified ingest with extractor registry** — add a source type = add an extractor function + register it
- **create_note_from_content()** builds system fields inside the tool — MCP/CLI/API are routing-only

### metadev-protocol adoption (implemented)

- **CLAUDE.md = law** (109 lines, always loaded) — identity, structure, automatisms, key docs
- **.meta/GUIDELINES.md = mentor** (193 lines) — G1-G13 rules, conventions, pre-commit checklist
- **.meta/ = process workspace** — specs, plans, audits, scratch (drafts), archive
- **Superpowers plugin** for generic workflow skills (brainstorming, plans, code review, debugging)
- **Project skills** (.claude/skills/) for project-specific tasks: save-progress, lint, test
- **Output path redirection** — Superpowers drafts → `.meta/scratch/`, validated → `.meta/specs/` or `.meta/plans/`

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

---

## Deferred items (must be documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| Crash recovery (`recover_source`) | Archive spec §16, brainstorm note F | After B2 or web ingest |
| `source_assets` table | Archive spec §15, brainstorm note G | When image handling implemented |
| Web ingestion | Archive spec §2.1 Family C | After security brainstorm |
| API test seed fixtures | PROJECT-STATUS.md debt | When fixture pattern refactored |
| System DB facade | PROJECT-STATUS.md debt | If 3+ callers need system DB via ctx |
| PostToolUse ruff hook | `.meta/specs/2026-04-03-metadev-protocol-adoption-notes.md` | When Claude Code exposes `$FILE` in hooks |

---

## Open questions (require interactive discussion)

1. **B2 Security Phase 2** — what scope? The existing spec (`specs/future/2026-03-29-security-design.md`) needs review and brainstorm
2. **Monitoring spec gap** — run_id and token_count missing from tool_logs table
3. **Web ingestion security brainstorm** — needed before any network-facing fetch code
4. **ARCHITECTURE.md location** — move from `docs/architecture/` to `.meta/`? Or keep separate since it's a permanent doc?
