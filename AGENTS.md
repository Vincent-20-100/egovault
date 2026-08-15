# EgoVault — Universal Agent Guidelines (AGENTS.md)

> **The Universal Constitution for AI Agents.**
> Applicable to all LLM environments: Claude Code, Antigravity, Cursor, Cline, OpenHands, and MCP clients.
> If any instruction conflicts with this document, this document takes precedence.

---

## 1. Project Identity & Cognitive Architecture

EgoVault is a **personal knowledge compiler and cognitive memory engine** designed around human neuroscience principles (memory consolidation, spreading activation, working memory constraints):

```
Tier 1: Hippocampal Chunks     → Raw, chronological, verbatim evidence in SQLite + chunks_vec
Tier 2: Neocortical Notes      → Distilled conceptual nuclei in Obsidian Markdown + notes_vec
Tier 3: Prefrontal Working Memory → Curated high-density context (4-7 slots) via curate()
```

- **Core Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md`
- **Core Motto:** *RAG retrieves then forgets. EgoVault consolidates, densifies, and connects.*

---

## 2. Hard Architecture Rules (Non-Negotiable)

```
core/           ← schemas, errors, config, context (VaultContext), uid, logging, security, sanitize (imports NOTHING from project)
tools/          ← atomic functions — receive VaultContext, import core/ only
workflows/      ← orchestrate tools/ — import tools/ + core/
infrastructure/ ← concrete SQLite, vector, and model providers — import core/ only
api/            ← thin routing layer — builds VaultContext, calls tools/ & workflows/
mcp/            ← thin routing layer — exposes tools/ via Model Context Protocol
cli/            ← thin terminal UI — delegates to tools/ & workflows/
config/         ← 3-tier configuration: system.yaml, user.yaml, install.yaml
```

1. **G1 — Public Strings Describe WHAT, Not HOW:** Never leak library names (`faster-whisper`, `sqlite-vec`, `pypdf`) in docstrings, error messages, or CLI help.
2. **G3 — Zero-Hardcode Policy:** Every parameter, model name, threshold, timeout, and buffer size comes from `ctx.settings` (`system.yaml`, `user.yaml`, `install.yaml`). **Zero magic numbers in code.**
3. **G4 — Hexagonal Context Isolation:** Tools never import `infrastructure/` directly. They receive all dependencies through [`VaultContext`](core/context.py).
4. **G6 — Error Architecture V2:** Every exception inherits from `EgoVaultError` and supplies `error_code`, `user_message`, `actionable_hint`, and `http_status`.
5. **G7 — Language Boundary:** All code, SQL, docstrings, comments, config keys, and specs are in **English**. Vault notes and slugs default to French (configurable via `user.yaml`).
6. **G9 — Pydantic at Boundaries:** All data entering or exiting tools, API, and MCP must be typed Pydantic models in `core/schemas.py`.

---

## 3. The 1 Source → N Notes Segmentation Principle

- Chunks are **mechanical cuts** (text position); notes are **semantic cuts** (one nucleus of meaning = one vector).
- `embed_note()` produces **one vector per note** (title + docstring + body concatenated).
- A multi-topic source **MUST NEVER** be reduced to 1 bloated note (which destroys retrieval recall via semantic averaging). It must be segmented into $N$ cohesive candidates via deterministic cosine TextTiling (`note_candidates`).

---

## 4. Agent Operating Personas & Workflow

When operating in this codebase, agents adopt specific modes depending on the phase:

| Persona | Role | Mandate |
|---|---|---|
| **Builder / Implementer** | Plan Execution & TDD | Follows the active plan strictly. Never improvises new features. Writes tests first. Updates documentation in the exact same commit as code. |
| **Adversarial Reviewer** | Code & Architecture Review | Proactively hunts for race conditions, unhandled edge cases, hardcoded constants, and broken contracts before merging. |
| **Librarian / Researcher** | Read-Only Vault Querying | Uses `curate()` as primary entry point. Leverages dual-space search (`search_notes` vs `search_chunks`) with proof drill-down (`get_chunks`). |
| **Vault Gardener** | Background Maintenance | Re-embeds out-of-sync notes, clusters vector space, suggests wikilinks, and normalizes tags. |

### The 7-Phase Engineering Lifecycle:
```
BRAINSTORM → SPEC → PLAN → IMPLEMENT (TDD) → TEST → AUDIT → SHIP
```
Full process specification: [`.meta/WORKFLOW.md`](.meta/WORKFLOW.md)  
Audit compliance checklist: [`.meta/AUDIT-SPEC.md`](.meta/AUDIT-SPEC.md)

---

## 5. Required Automatisms for Every Session

1. **Session Start:** Read `PROJECT-STATUS.md` and `SESSION-CONTEXT.md` before performing any action.
2. **Before Editing Code:** Verify an approved plan exists in `.meta/plans/`. Never implement code without a validated plan.
3. **Every Commit:** Format as `feat:`, `fix:`, `docs:`, `chore:`, or `test:` with clear English descriptions.
4. **Doc Synchronization:** Any user-visible change (new tool, new config key, new parameter, schema update) **MUST** update `docs/user-guide/` and architecture references in the same commit.
5. **Session End:** Update `PROJECT-STATUS.md` and rewrite `SESSION-CONTEXT.md` to reflect latest progress and active decisions.
