# Unified Ingest Architecture — Discussion Notes

**Date:** 2026-03-31
**Context:** User feedback on `2026-03-31-unified-ingest-architecture.md`
**Status:** Working notes — to be integrated into final spec before planning

---

## User feedback and decisions

### 1. Crash recovery — future upgrade path

**V1 (to implement):** Reset to `raw`, delete partial state, restart from scratch.

**Future work (to document, NOT implement):** Resume-in-progress with checkpoint management.
- Each pipeline step writes a checkpoint (e.g., `extracted`, `chunked`, `embedded`)
- On crash, recovery detects the last checkpoint and resumes from there
- Requires idempotent steps and checkpoint storage in `.system.db`
- Significantly more complex — only justified when ingest times become long (large files, batch)

**Action:** Add explicit "future upgrade" note in spec section 16 + add to FUTURE-WORK.md.

---

### 2. N pipeline families, not just 2

**Current design says "2 families"** — user correctly points out this should be "N families" with extensibility hooks.

**Known families:**
- **Document pipeline:** text-based sources → extract → chunk → embed
- **Media pipeline:** audio/video → prepare → transcribe → (document pipeline)
- **Potential future:** Structured data (JSON, CSV, DB) → parse → transform → chunk → embed
- **Potential future:** Interactive (chat exports, threads) → parse → chunk → embed

**Architecture implication:** The extractor registry should be family-aware. Each family defines:
- A pipeline (ordered sequence of steps)
- A set of source types it handles
- Configuration specific to that family

**V1:** Implement 2 families (document + media). Design the registry so adding a 3rd family is a config+code change, not a refactor.

**Action:** Rewrite spec section 2 to use "N families" language, implement 2 for now.

---

### 3. Web extraction — tiered approach

**User question:** BS4 alone — is it even useful? Need tiers like image handling.

**Tier design:**

| Tier | Strategy | Coverage | Dependency |
|------|----------|----------|------------|
| 0 | Basic HTML parser (BS4): strip scripts/nav/footer, find article/main/body, extract p/h1-6/li | ~60-70% (blogs, docs, structured news) | beautifulsoup4 + requests |
| 1 | Readability algorithm (trafilatura or readability-lxml) — auto-detect main content vs noise | ~85% | Lightweight third-party lib |
| 2 | LLM-assisted — send truncated HTML to LLM with extraction prompt | ~95%+ | Configured LLM API |
| 3 | Browser rendering (Playwright) + LLM — for JavaScript-heavy SPAs | ~99% | Playwright + LLM |

**V1 decision (pending user confirmation):** Implement Tier 0 only. Clear error message on failure ("extraction failed — page may require a more advanced extractor"). Tiers 1-3 documented as future work.

**Config:**
```yaml
extraction:
  web_tier: 0    # 0 = basic HTML, 1 = readability, 2 = LLM, 3 = browser+LLM
```

**Open question:** User may prefer to do a dedicated brainstorm on web extraction + security before implementing anything web-related.

---

### 4. Config changes — clarification

Section 4 of the spec just adds:
- `texte` and `web` to `taxonomy.source_types` in system.yaml
- New upload limits: `max_text_chars`, `max_web_response_mb`, `web_timeout_seconds`
- New extraction config: `image_handling` tier, `web_tier`

Purely mechanical config additions. No architectural complexity.

---

### 5-7. Surfaces (CLI/API/MCP) — needs dedicated brainstorm

The spec describes the surface changes at a high level but a **dedicated brainstorm** is needed to think through:
- CLI UX for web and text ingestion (stdin, file, inline, URL detection)
- API request/response schemas
- MCP tool descriptions and parameters
- Error presentation per surface
- Progress/status feedback per surface

**Action:** Schedule brainstorm before implementation.

---

### 8. Web ingestion security — needs dedicated brainstorm

SSRF prevention, HTML sanitization, rate limiting, DNS rebinding, redirect following, etc.

This is a **standalone security topic** that must be brainstormed before any web fetch code is written.

**Action:** Schedule brainstorm before implementing extract_web.

---

### 9. Error hierarchy — to verify

IngestError hierarchy in spec section 9 looks correct but needs verification against:
- Existing error patterns in core/errors.py
- Actual failure modes of each extractor
- G6 compliance (no internal details in user messages)

**Action:** Verify during plan writing, before implementation.

---

### 10. File map — plan feasibility

The file map (spec section 10) lists all files to create/modify. Going straight to a plan is feasible **if the spec is finalized**. The plan would sequence the file map into ordered phases.

---

### 17. "Hors scope" → "Chantiers futurs documentés"

Rename section 17 from "What this does NOT include" to "Future work — documented intentions".

Each item must have:
- Clear description of the intention
- Estimated complexity (S/M/L/XL)
- Hooks needed in current architecture
- Dependencies on other work

---

## New requirement: Audit spec

User wants a **systematic audit specification** that an agent can execute to:
1. Check all specs for contradictions/interference
2. Verify architecture boundaries (G4) across entire codebase
3. Check G1-G12 compliance everywhere
4. Security review (G10)
5. Test coverage verification (G8)
6. Config-driven verification (G3)
7. Documentation consistency (G12)

This should be a standalone spec: `2026-03-31-project-audit-spec.md`

**Format:** Step-by-step checklist with:
- What to check
- Where to check (files/directories)
- What constitutes a violation
- Severity (critical/major/minor)
- How to fix

---

## Pending brainstorms (proposed order)

1. **(c) Project audit spec** — reveals current state, informs all other decisions
2. **(a) Web ingestion security** — blocks web extraction implementation
3. **(b) Surfaces UX** — depends on (a) for web-specific decisions

## Independent work (no brainstorm needed)

- **ingest_text** — trivial pipeline (text → chunk → embed), no network, no security risk
- Can be implemented immediately as a quick win
- Tests are straightforward

---

## Decisions (2026-03-31 — session 2)

### Web ingestion → FUTURE WORK
- Web fetching (HTTP requests, SSRF prevention, security) is deferred entirely
- Optional: build a **local HTML parser tool** (HTML string in → text out, zero network)
  - Becomes Tier 0 extractor when web fetch is added later
  - Useful independently (can parse HTML from any local source)
- Web security brainstorm happens when web ingestion is scheduled, not before

### Brainstorm order (confirmed)
1. **Architecture** — N families, unified workflow, extractor registry, extensibility hooks
2. **Surfaces** — CLI/API/MCP for new types (ingest_text + future hooks)
3. **Web security** — deferred, goes with web ingestion feature

### Implementation priority
- ingest_text = immediate (trivial, no network, no security risk)
- Unified workflow architecture = immediate (reduces duplication, enables all future types)
- Web ingestion = future work (needs dedicated security brainstorm first)

### Audit spec
- Still needed but not blocking implementation
- Can run after architecture + surfaces brainstorms
- Agent-executable: step-by-step checklist for full project scan
