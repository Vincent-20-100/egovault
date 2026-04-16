# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-04-16
**Last session:** `claude/check-project-status-6VthL` (merged to main)

---

## Current strategic direction: Knowledge Compiler + Librarian Agent

This session produced a **product vision shift** inspired by Andrej Karpathy's LLM Wiki
pattern and the agentify project. The core insight:

**RAG retrieves then forgets. A knowledge compiler accumulates and densifies.**

EgoVault should evolve from a RAG system to a **two-layer knowledge system** with an
intelligent retrieval agent. This is documented in detail in `docs/FUTURE-WORK.md`
(section "Architecture pivot — Knowledge compiler + Agent retrieval").

### The Two-Layer Architecture

- **Layer 1 (keep):** RAG on raw source chunks. Precise, verbatim, good for exact facts.
- **Layer 2 (new):** Compiled knowledge on notes. Dense, human-validated, cross-source synthesis.

### The Librarian Pattern

Instead of dumping top-K chunks into the conversation:

```
User ↔ Conversational LLM (via MCP, clean context window)
              ↓ calls curate("question about X")
        curate() tool inside EgoVault:
              ├── search_notes() → deterministic
              ├── search_chunks() → deterministic
              ├── ctx.get_completion(prompt) → isolated LLM call (separate context)
              └── return CuratedContext (synthesized, minimal)
```

**Key decision:** The librarian is NOT an autonomous agent or separate project. It's a
**smart tool** (`curate()`) that uses one isolated LLM call as a subroutine — same pattern
as `generate_note_from_source`. Testable, mockable, deterministic-except-one-call.

### Tiered — works without LLM

| Tier | What curate() does | Dependency |
|------|-------------------|------------|
| 0 | Search + rank + truncate → sorted raw results | Nothing (deterministic) |
| 1 | Tier 0 + LLM synthesis | LLM local or API key |

**Principle:** Every feature has a tier 0 deterministic baseline. LLM = accelerator, not prerequisite.

### Pre-packaged agent for MCP clients

For Claude Code users: provide `.claude/rules/vault-usage.md` + `AGENTS.md` so the user's
own LLM becomes the librarian via prompt. Zero extra infrastructure.

---

## OpenTimestamps — setup complete, awaiting user action

**OpenTimestamps** is set up: script (`scripts/timestamp-release.sh`), docs (`docs/TIMESTAMPS.md`),
and tags (v0.1.0, v0.2.0, v0.3.0) are all created. OTS calendar servers were unreachable from
sandbox. **User must run from their machine:**

```bash
git push origin --tags
bash scripts/timestamp-release.sh v0.1.0
bash scripts/timestamp-release.sh v0.2.0
bash scripts/timestamp-release.sh v0.3.0
git add .timestamps/ && git commit -m "chore: add OTS proofs for v0.1.0, v0.2.0, v0.3.0"
```

Rule: only v0.X.0 tags are timestamped. Script enforces the pattern.

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **Unified ingest with extractor registry** — add source type = add extractor + register
- **create_note_from_content()** builds system fields inside the tool
- **N pipeline families** — 2 implemented (document + media), architecture supports N
- **Web ingestion V1** — implemented with SSRF protection + 2-tier extraction

### Large source synthesis (spec written, not yet implemented)

- **Cascade:** web search (opt) → TOC+chapters → map-reduce → final synthesis
- **Template reuse:** same template per sub-generation → merge/dedup final
- **Presets:** `provider_mode` (local/api) × `quality_preset` (quick/balanced/quality)

---

## Traps to avoid

1. Don't write specs without brainstorming with the user
2. Use analogies for architecture jargon (restaurant kitchen worked for VaultContext)
3. Don't forget the north star: 2-minute demo video
4. Don't mix features with refactoring
5. Rate limit / background thread tests MUST mock `_submit_job` to avoid DB locks
6. When editing CLAUDE.md, keep it ≤110 lines — detailed rules go in GUIDELINES.md
7. Don't optimize search/synthesis without real data first
8. **Don't assume the user understands the technical distinction between "agent" and "tool with LLM call"** — always explain concretely
9. **The system has never been tested with real data** — all tests are mocked. Real-world testing is prerequisite for any quality optimization.
10. **OpenTimestamps BEFORE publishing the vision** — establish antériority first.

---

## Deferred items (documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| ~~**Vision spec + OpenTimestamps**~~ | ~~SESSION-CONTEXT.md~~ | **DONE** — vision doc committed, OTS set up (user must push tags + stamp) |
| **Real-world testing** | SESSION-CONTEXT.md | **NEXT PRIORITY** — validate fundamentals with real data |
| **Knowledge compiler (`curate()` tool)** | `docs/VISION-KNOWLEDGE-COMPILER.md` | After real-world testing |
| Pre-packaged librarian agent (AGENTS.md) | `docs/FUTURE-WORK.md` | After curate() exists |
| Large source synthesis | `.meta/specs/2026-04-06-large-source-synthesis-spec.md` | After real testing |
| Multi-source workflow | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §1 | High priority brainstorm |
| Search quality (reranking) | `.meta/specs/future/2026-03-28-reranking-design.md` | After real-world testing |
| Crash recovery (`recover_source`) | Archive spec §16 | After large source synthesis |

---

## Open questions (require interactive discussion)

1. ~~**Vision spec scope**~~ — **RESOLVED**: concise vision doc (docs/VISION-KNOWLEDGE-COMPILER.md), not a whitepaper.
2. ~~**OpenTimestamps setup**~~ — **RESOLVED**: v0.X.0 tags only, script enforces pattern, user must run from machine.
3. **Real-world testing plan** — which sources first? YouTube, PDFs, web pages? What quality metrics?
4. **curate() design** — what goes in the synthesis prompt? How to handle "no relevant results"?
5. **AGENTS.md format** — follow agentify convention? Custom format? What agent definitions?
