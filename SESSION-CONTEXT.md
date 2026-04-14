# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-14
**Last session:** `feat/large-source-synthesis`

---

## Current state: Large source synthesis shipped — needs real-world validation

The synthesis cascade is implemented end-to-end: `estimate_tokens` → `get_context_window`
(Ollama auto-detect + hardcoded map + override) → `synthesize_large_source` (auto-detects
direct / TOC / map-reduce based on transcript size vs `context_window * direct_threshold_ratio`)
→ per-section sub-generation with chapter context injected via `system_prompt_extra` →
final pass through the new `merge.yaml` template. 14 new tests, zero regressions on the
pre-existing suite. Spec archived.

**Still never tested with real data.** Next session: ingest a long-form source (book,
3h interview, long PDF) and observe branching. Tune `merge_chunk_size` and
`direct_threshold_ratio` to taste. The 3Blue1Brown GPT video remains the suggested first
real test for the small-source direct path.

**Next priority:** Real-world testing → observe TOC vs map-reduce branching → tune.

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **This project is a reusable template** — every structural decision must be portable
- **Unified ingest with extractor registry** — add a source type = add an extractor function + register it
- **create_note_from_content()** builds system fields inside the tool — MCP/CLI/API are routing-only

### Large source synthesis (implemented 2026-04-14)

- **Cascade shipped:** TOC (H1 then H2 fallback) → map-reduce (token-window split) → merge template
- **Template reuse:** same user template for each sub-note, dedicated `merge.yaml` for final synthesis
- **Chapter context:** injected per sub-note via `system_prompt_extra` on `GenerateFn` Protocol
- **Threshold:** `estimate_tokens(transcript) > context_window * direct_threshold_ratio` (default 0.6)
- **Context window:** explicit override → Ollama `/api/show` → hardcoded map (Claude 4.x, GPT-4o) → 8192
- **Cap:** `max_sub_notes` (default 40) raises ValueError before firing N LLM calls
- **Deferred:** web-search tier, persisted intermediate cache, model routing (light/heavy) — all documented

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

## Audio/token estimates (reference)

- ~150 mots/min parlées → ~200 tokens/min
- **50k tokens** (seuil `large_format_threshold_tokens`) ≈ **4h d'audio**
- Claude 200k context × 0.6 ratio ≈ ~120k tokens ≈ ~10h théorique
- Ollama local 8-32k context ≈ **20 min à 2h30**
- Vidéos YouTube **10 min à 2h** = zone confortable pour tests

### Long format status

Sources exceeding `large_format_threshold_tokens` (50k) remain blocked by `LargeFormatError`
at ingest time. Below that, the synthesis cascade handles anything that fits in ~2× the LLM
context window comfortably via map-reduce. The "split-2 + merge" quick fallback is now
superseded by the full cascade.

---

## Deferred items (must be documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| Real-world testing | SESSION-CONTEXT.md | **NEXT** — ingest real sources, evaluate RAG |
| ~~Long format fallback (split-2 + merge)~~ | ~~SESSION-CONTEXT.md~~ | **Superseded by cascade** |
| ~~Large source synthesis~~ | ~~`.meta/archive/specs/2026-04-06-large-source-synthesis-spec.md`~~ | **DONE 2026-04-14** |
| Multi-source workflow | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §1 | High priority — brainstorm needed |
| Onboarding / DX (`egovault setup`) | SESSION-CONTEXT.md | Important — before public launch |
| Cross-document entity resolution | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §2 | Medium — reinforces multi-source |
| Source citations in notes | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §4 | Medium — template improvement |
| Model routing (light/heavy) | `.meta/archive/specs/2026-04-06-large-source-synthesis-spec.md` §9 | Future — preset enhancement |
| Search quality (reranking) | `.meta/specs/future/2026-03-28-reranking-design.md` | After real-world testing |
| Ollama/OpenAI LLM providers | `infrastructure/llm_provider.py` | Before local testing (only Claude implemented) |
| Crash recovery (`recover_source`) | Archive spec §16 | After large source synthesis |
| API test seed fixtures | PROJECT-STATUS.md debt | When fixture pattern refactored |
| PostToolUse ruff hook | `.meta/specs/2026-04-03-metadev-protocol-adoption-notes.md` | When Claude Code exposes `$FILE` |

---

## Open questions (require interactive discussion)

1. **Real-world testing plan** — which sources to ingest first? User's existing cards, YouTube, PDFs?
2. **Onboarding DX** — `egovault setup` CLI command? Auto-write to user's Claude config? How intrusive?
3. ~~Token counting~~ — **RESOLVED:** heuristic `words ÷ 0.75` shipped in `core/tokens.py`.
4. ~~Large source synthesis template~~ — **RESOLVED:** dynamic `system_prompt_extra` for chapter context + dedicated `merge.yaml` for final synthesis.
5. **Multi-source workflow** — what UX? MCP tool? CLI command? How does the user initiate the brainstorm?
