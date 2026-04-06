# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-06
**Last session:** `main`

---

## Current state: Repo public-ready, awaiting real-world testing

Git history cleaned (115 → 12 commits, all Vincent). ADR-008 metadev changes applied.
Two new specs written (large source synthesis + NotebookLM/Synapthema ideas).
Vault-usage rules added for MCP guidance.

**The system has never been tested with real data.** All tests are mocked.
The next priority is ingesting actual sources and evaluating RAG quality before
optimizing anything.

**Next priority:** Real-world testing → then iterate on search quality + large source synthesis.

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
- **Model routing (future):** modèle léger pour extraction/structure, modèle lourd pour synthèse finale

### Two distinct problems for large sources

1. **Chunking & embedding** — problème d'indexation/search. Bénéficie déjà du markdown structuré.
2. **Note synthesis** — problème de summarization quand input > context window. Spec écrite.

Ces deux problèmes sont **indépendants** et doivent rester séparés.

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
13. Don't optimize search/synthesis without real data first — test with actual sources

---

## Deferred items (must be documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| Real-world testing | SESSION-CONTEXT.md | **NEXT** — ingest real sources, evaluate RAG |
| Large source synthesis | `.meta/specs/2026-04-06-large-source-synthesis-spec.md` | After real testing validates fundamentals |
| Multi-source workflow | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §1 | High priority — brainstorm needed |
| Onboarding / DX (`egovault setup`) | SESSION-CONTEXT.md | Important — before public launch |
| Cross-document entity resolution | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §2 | Medium — reinforces multi-source |
| Source citations in notes | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §4 | Medium — template improvement |
| Model routing (light/heavy) | `.meta/specs/2026-04-06-large-source-synthesis-spec.md` §9 | Future — preset enhancement |
| Search quality (reranking) | `.meta/specs/future/2026-03-28-reranking-design.md` | After real-world testing |
| Ollama/OpenAI LLM providers | `infrastructure/llm_provider.py` | Before local testing (only Claude implemented) |
| Crash recovery (`recover_source`) | Archive spec §16 | After large source synthesis |
| API test seed fixtures | PROJECT-STATUS.md debt | When fixture pattern refactored |
| PostToolUse ruff hook | `.meta/specs/2026-04-03-metadev-protocol-adoption-notes.md` | When Claude Code exposes `$FILE` |

---

## Open questions (require interactive discussion)

1. **Real-world testing plan** — which sources to ingest first? User's existing cards, YouTube, PDFs?
2. **Onboarding DX** — `egovault setup` CLI command? Auto-write to user's Claude config? How intrusive?
3. **Token counting** — tiktoken (precise) or heuristic `words ÷ 0.75` (zero-dep)?
4. **Large source synthesis template** — separate sub_note.yaml or dynamic system_prompt enrichment?
5. **Multi-source workflow** — what UX? MCP tool? CLI command? How does the user initiate the brainstorm?
