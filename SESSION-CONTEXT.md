# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-06
**Last session:** `main`

---

## Current state: Clean repo, ready for public + real testing

Git history cleaned (115 → 12 commits, all Vincent). ADR-008 metadev changes applied.
Large source synthesis spec written. Vault-usage rules added for MCP guidance.

**What was done this session:**
- Git history squash (115 → 12 commits, author cleanup)
- ADR-008: attribution.commit="", permissions, rules/, pre-commit, SessionStart hook
- Large source synthesis brainstorm + spec (cascade, presets, template reuse)
- Vault-usage rules (.claude/rules/vault-usage.md)

**Next priority:** **Real-world testing** — ingest actual sources, test RAG quality, then iterate.
User couldn't test this session (no local env ready).

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **This project is a reusable template** — every structural decision must be portable
- **Unified ingest with extractor registry** — add a source type = add an extractor function + register it
- **create_note_from_content()** builds system fields inside the tool — MCP/CLI/API are routing-only

### Large source synthesis (spec written, not yet implemented)

- **Cascade:** web search (opt) → TOC+chapitres → map-reduce → synthèse finale
- **Template reuse:** même template à chaque sous-génération → merge/dédup final
- **Seuil:** auto-detect context window (~60% ratio), configurable
- **Cache intermédiaire:** mémoire par défaut, debug persisté en option
- **Presets:** 2 axes indépendants — `provider_mode` (local/api) × `quality_preset` (quick/balanced/quality)

### Monitoring (implemented)

- **run_id via contextvars** — zero changes to tool signatures
- **Token count auto-extraction** from @loggable results
- **workflow_runs table** — pipeline tracking with status/timing

### Web ingestion (implemented)

- **SSRF protection** in core/security.py
- **2-tier extraction** — Tier 0 (parse_html), Tier 1 (trafilatura)
- **httpx streaming** with size limits + post-redirect DNS re-validation

---

## Traps to avoid

1. Don't write specs without brainstorming with the user
2. Use analogies for architecture jargon
3. Don't forget the north star: 2-minute demo video
4. Don't over-engineer VaultDB — one-line delegations only
5. Don't mix features with refactoring
6. Rate limit / background thread tests MUST mock `_submit_job` to avoid DB locks
7. Mock `_run_ingest` in integration tests
8. `create_note` (low-level) takes NoteSystemFields; `create_note_from_content` (high-level) builds them
9. When editing CLAUDE.md, keep it ≤110 lines — detailed rules go in GUIDELINES.md
10. pypdf tests need `patch.dict(sys.modules, {"pypdf": mock})` — env has broken cryptography module
11. tool_logs.run_id must NOT have FK to workflow_runs — standalone tool calls have no run
12. attribution.commit="" in settings.json — prevents Claude co-author trailer on commits

---

## Deferred items (must be documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| Crash recovery (`recover_source`) | Archive spec §16 | After large source synthesis |
| `source_assets` table | Archive spec §15 | When image handling implemented |
| Large source synthesis | `.meta/specs/2026-04-06-large-source-synthesis-spec.md` | Next impl priority |
| Onboarding / DX (`egovault setup`) | SESSION-CONTEXT.md | Important — before public launch |
| Search quality (reranking) | `.meta/specs/future/2026-03-28-reranking-design.md` | After real-world testing |
| API test seed fixtures | PROJECT-STATUS.md debt | When fixture pattern refactored |
| System DB facade | PROJECT-STATUS.md debt | If 3+ callers need system DB via ctx |
| PostToolUse ruff hook | `.meta/specs/2026-04-03-metadev-protocol-adoption-notes.md` | When Claude Code exposes `$FILE` |
| Ollama/OpenAI LLM providers | `infrastructure/llm_provider.py` | Before local testing (only Claude implemented) |

---

## Open questions (require interactive discussion)

1. **Real-world testing plan** — which sources to ingest first? User's existing cards, YouTube, PDFs?
2. **Onboarding DX** — `egovault setup` CLI command? Auto-write to user's Claude config? How intrusive?
3. **Token counting** — tiktoken (precise) or heuristic `words ÷ 0.75` (zero-dep)?
4. **Large source synthesis template** — separate sub_note.yaml or dynamic system_prompt enrichment?
