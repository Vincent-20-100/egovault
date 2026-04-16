# EgoVault — Vision: Knowledge Compiler + Librarian Agent

**Date:** 2026-04-16
**Status:** Vision document — validated by user, not yet specced for implementation.
**Inspired by:** Andrej Karpathy's LLM Wiki pattern, agentify project, context engineering.

---

## The problem with RAG

RAG is **stateless and noisy**:

1. **No memory** — every search starts from scratch, no capitalization
2. **No judgment** — ranking is purely mathematical (cosine similarity), no understanding of intent
3. **Context pollution** — the conversational LLM receives noise it must sort through itself,
   consuming its context window and degrading response quality

## The thesis: context is compiled, not retrieved

Knowledge densifies over time — raw observations become structured notes, which become
cross-source syntheses. Like human memory: repetition strengthens, time without use weakens.

**Stop retrieving. Start compiling.**

---

## Architecture: 3 knowledge tiers

```
Tier 3 — Compiled context (what the conversational LLM receives)
    On-the-fly syntheses, note excerpts, sourced citations.
    Minimal, relevant, ready to consume. Never noise.

Tier 2 — Compiled notes (validated knowledge)
    Structured notes, human-validated, cross-source.
    Dense, reliable, searchable by embedding.
    Densify over time (multi-source → synthesis).

Tier 1 — Raw source chunks (raw material)
    Embedded chunks from original sources (YouTube, PDF, web, text).
    Precise, verbatim, good for exact citations.
    High volume, potential noise.
```

**RAG is not dead — it changes tier.** It stays at tier 1 as raw material.
But it no longer feeds the conversation directly.

---

## The Librarian: a smart tool, not an autonomous agent

The librarian bridges the tiers. It is a **deterministic tool with one isolated LLM call
as a subroutine** — same pattern as `generate_note_from_source`.

```
User ↔ Conversational agent (clean context, never touches DB)
              │
              │ "I need info about X"
              ▼
        curate(query, conversation_summary)
              │
              ├── 1. Search compiled notes (tier 2, fast)
              ├── 2. If insufficient → search RAG chunks (tier 1, precise)
              ├── 3. Can run MULTIPLE queries, cross-reference, deduplicate
              ├── 4. Detect contradictions between sources
              ├── 5. Isolated LLM call: select + synthesize (separate context)
              │
              ▼
        Returns to conversational: CuratedContext
              ├── synthesis: synthesized text, minimal
              ├── sources: citations with UIDs (verifiable)
              └── confidence: score based on concordant sources
```

**Why a tool, not an agent:** An agent decides WHAT to do. A tool does what it's asked
WITH intelligence. `curate()` always receives the same instruction (search + synthesize),
only the input changes. No decision loop needed.

**Why an isolated LLM call:** The curation prompt is separate from the conversation.
It sees only the query + search results. No cross-pollution, unit-testable, mockable.

---

## Tiered: works without LLM

| Tier | What `curate()` does | Dependency |
|------|---------------------|------------|
| 0 | Search notes + chunks → rank by similarity → truncate → return sorted raw results | **Nothing** (pure deterministic) |
| 1 | Tier 0 + LLM selects, deduplicates, synthesizes | LLM local or API key |

A Claude Code user without a local LLM: tier 0 works. The conversational LLM (Claude
via MCP) compensates by doing its own synthesis from the raw results. Less elegant but
functional.

**Universal project principle:** every feature has a tier 0 deterministic baseline.
LLM is an accelerator, never a prerequisite.

---

## Pre-packaged librarian for MCP clients

For users with Claude Code or any MCP client:

```
.claude/rules/vault-usage.md  → "when user asks a knowledge question, call curate() first"
AGENTS.md                     → librarian agent definition, ready to use
```

The user's own LLM **becomes** the librarian via the prompt. Zero extra infrastructure.
Opens the door to other pre-packaged agents (summarizer, note-linker, etc.).

---

## What this changes for EgoVault

| Before (classic RAG) | After (Knowledge Compiler) |
|----------------------|---------------------------|
| query → chunks → context | query → librarian → compiled context |
| User receives noise | User receives signal |
| Every search starts from scratch | Notes densify over time |
| Conversational LLM does everything | Conversational converses, librarian searches |
| Works for 10 sources | Scales to 1000 sources via compilation |

---

## Incremental implementation path

1. **`curate()` tier 0** — search + rank + truncate (deterministic, zero new dependency)
2. **`curate()` tier 1** — add LLM synthesis call
3. **`compile()`** — multi-source synthesis persisted as note
4. **AGENTS.md** — pre-packaged librarian for MCP clients
5. **Confidence scores** — each fact carries a score that strengthens or decays

Each step is independently deliverable and adds value.

---

## What this does NOT mean

- Not replacing RAG — moving it to tier 1 and adding smarter layers above
- Not requiring a rewrite — incremental, builds on existing tools
- Not blocking current work — this is the north star, not a prerequisite
