# EgoVault — Architecture & Strategy Review Brief

**Version:** 1.0 — 2026-08-10
**Purpose:** Strategic and architectural review by an external agent. Honest account of current state, choices made, and open questions. Not a user manual.

---

## 1. What EgoVault is

A **personal knowledge vault** for a single user. The user ingests content (YouTube videos, audio files, PDFs, web pages, text), EgoVault processes it into embedded chunks and structured notes, and the user can later retrieve that knowledge via semantic search, an MCP server (for Claude/LLM clients), or a CLI.

The long-term vision: evolve from a RAG system into a **knowledge compiler** — a system that accumulates, densifies, and surfaces knowledge progressively better over time, rather than treating every query as stateless retrieval.

**Stack:** Python 3.x, SQLite + sqlite-vec, Pydantic v2, FastAPI, FastMCP, Click CLI. No JavaScript frontend yet. Embedding via Ollama (local, default) or OpenAI. LLM generation via Claude, Ollama, or OpenAI.

---

## 2. What is actually built (vs what is planned)

### Built and tested (511 tests, mostly mocked)

| Component | Status | Notes |
|-----------|--------|-------|
| Ingest pipeline | Done | youtube, audio, video, pdf, web, text. 8 extractors via registry. |
| Chunking + embedding | Done | ~800 token chunks, L2-normalized cosine embeddings in sqlite-vec. |
| `generate_note_from_source()` | Done | LLM generates a draft note from source. Ollama + Claude. |
| `curate()` tier 0 | Done | Deterministic: search notes → escalate to chunks → return sorted raw results. No synthesis. |
| RRF hybrid retrieval | Done | FTS5 BM25 + cosine via Reciprocal Rank Fusion. Opt-in flag, default **false**. |
| MCP server | Done | 22+ tools exposed to Claude/MCP clients. |
| FastAPI API | Done | 8 routers, 22 endpoints. |
| CLI | Done | ingest, search, notes, sources, status, purge. |
| Obsidian export | Done | `vault_writer.py` generates `.md` files with frontmatter and tags. |
| Monitoring | Done | run_id via contextvars, workflow_runs table, cost tracking. |
| Security (SSRF, path validation) | Done | Local-only design, no auth. |

### Planned but not built

| Component | Status | Notes |
|-----------|--------|-------|
| `curate()` tier 1 (Librarian) | Plan written, not implemented | Sub-agent delegation + `/ask-vault` command. MCP sampling deferred (unsupported by Claude Code/Desktop today). |
| Frontend | Spec ready | Next.js. Not started. |
| Cross-encoder reranking | Spec ready | RRF shipped as a lighter alternative. Cross-encoder still deferred. |
| Semantic cache | Spec ready | Not implemented. |
| Multi-source note synthesis | Spec written | "compile multiple sources into one note." No plan yet. |
| Semantic clustering (`vault_map`) | Brainstorm only | HDBSCAN on embeddings to produce cluster tags. No spec. |
| RAG benchmark / evaluation | Framework spec ready | `benchmark/` dir exists as stubs. No golden dataset. No real evaluation. |
| Confidence scores + temporal decay | Vision only | No spec, no plan. |

---

## 3. Architecture

### 3.1 Data model

```
source        — ingested content (url, file). One per ingest.
  └── chunks  — text fragments (~800 tokens) from the source transcript.
                Each chunk is embedded → stored in chunks_vec (sqlite-vec).

note          — generated Markdown document. One per source (currently).
                Embedded → stored in notes_vec.
                Exported as .md to the Obsidian vault.
```

Two embedding spaces: **chunks** (raw, noisy, many) and **notes** (compiled, validated, few).

### 3.2 Two-layer retrieval vision

```
Layer 2 — notes_vec    (compiled knowledge, dense, reliable)
Layer 1 — chunks_vec   (raw material, precise, verbatim, noisy)
```

The vision: search notes first; fall back to chunks only when notes are sparse. Implemented in `curate()` tier 0. The escalation threshold (`escalation_max_distance = 0.5`) is a **guess** — never calibrated on real data.

### 3.3 Code architecture (hexagonal)

```
surfaces (CLI, MCP, FastAPI)
    ↓ call build_context() → VaultContext
tools/ + workflows/     ← receive ctx: VaultContext, import core/ only
core/                   ← VaultContext, schemas, Protocols — zero project imports
infrastructure/         ← VaultDB, providers, build_context() — imports core/ only
```

`VaultContext` is the dependency injection container. Tools never import infrastructure directly. This makes provider swaps (SQLite → Postgres, Ollama → OpenAI) a single-file change.

### 3.4 The Librarian pattern (tier 1, not yet built)

```
User ↔ Conversational LLM (Claude via MCP, clean context)
              │
              ▼ calls curate(query, generous=True)
        curate() — recall-first wide net: hybrid RRF, both notes + chunks, untruncated
              │
              ▼ returns raw pile to a librarian subagent
        librarian subagent (isolated Claude Code subagent or /ask-vault command)
              │ triages the pile, synthesizes, keeps only relevant UIDs
              ▼
        {answer, used_source_uids}  → back to main conversation
```

**Key dependency:** the Librarian relies on Claude Code's subagent mechanism. MCP sampling (the architecturally clean path) is verified unsupported by Claude Code/Desktop today (tracked as debt). The current plan is a workaround.

---

## 4. Strategic choices and their rationale

| Choice | Rationale | Risk / Assumption |
|--------|-----------|-------------------|
| SQLite + sqlite-vec over a vector DB | Local-only, zero infra, single file backup | Does not scale past ~1M vectors. Acceptable for personal PKM. |
| Two embedding spaces (notes + chunks) | Notes are denser, more reliable; chunks are precise, verbatim | Notes quality depends entirely on LLM generation quality. Unverified at scale. |
| `curate()` as the preferred entry point | Hides RAG complexity, returns signal not noise | Currently tier 0 = sorted raw results. The "signal" claim is aspirational. |
| RRF hybrid opt-in (default false) | Conservative — only 1 real win in initial experiment, 0 regressions | May be leaving recall gains on the table for FR-language content. |
| Ollama-first (local, keyless) | No API cost, no data sent externally | Ollama model quality is lower than Claude/GPT-4. Note quality varies. |
| Obsidian as the UI | Zero frontend work, already battle-tested by user | Bidirectional sync not implemented. DB is source of truth; Obsidian is export only. |
| Notes: one per source | Simple, predictable | No cross-source synthesis. "Knowledge densification" (the vision) doesn't happen. |

---

## 5. The honest state of the "Knowledge Compiler" vision

The vision describes three tiers of knowledge (raw chunks → compiled notes → curated synthesis). In practice:

- **Tier 1** (chunks): implemented and working.
- **Tier 2** (notes): implemented but quality is LLM-dependent and untested at scale. Notes are currently one-per-source, never multi-source.
- **Tier 3** (curated synthesis): `curate()` tier 0 returns a sorted list — not a synthesis. Tier 1 (actual synthesis) is not built. The "Librarian" is a plan with a workaround dependency.

The claim "stop retrieving, start compiling" is the north star, not the current state. The system is today a **well-structured RAG** with Obsidian export and an MCP interface.

---

## 6. What has never been tested

- **Semantic quality at scale**: 25 sources tested in real conditions (2026-05-17). No benchmark. The evaluation framework exists as stubs only (TEST-C2 debt acknowledged).
- **curate() retrieval quality**: escalation threshold (0.5) is unvalidated. No recall/precision metrics on real queries.
- **Note generation quality**: Ollama qwen2.5:7b-instruct produces notes, but their quality relative to Claude or GPT-4 is unknown and unmeasured.
- **RRF hybrid benefit at scale**: validated on 4 queries with 25 sources. Not a meaningful sample.
- **The Librarian pattern**: the `/ask-vault` subagent plan has never been executed. The design assumes a Claude Code context with a capable host LLM.

---

## 7. Roadmap (current order) and its rationale

```
1. curate() tier 1 — Librarian base (plan written, ready to execute)
   → Adds isolated synthesis; uses host LLM via subagent delegation.
   → Workaround for missing MCP sampling.

2. Semantic clustering (vault_map)  [brainstorm only, no spec]
   → HDBSCAN on note/chunk embeddings → cluster tags → gap analysis.
   → Would also improve curate() pre-filtering.

3. Search quality (reranking)  [spec ready, not prioritized]
   → Cross-encoder after RRF. Deferred because RRF covered the main gap.

4. Large source synthesis  [spec written, no plan]
   → Map-reduce for long documents. Blocked by curate() maturity.

5. Frontend  [spec ready]
   → Next.js. Low urgency while Obsidian + MCP cover the UI need.

6. OpenAI provider + provider management  [brainstorm only]
   → Chantier B. Deferred because Ollama covers the local case.

7. Evaluation framework  [stubs only]
   → No golden dataset. Blocked by lack of real-world data.
```

---

## 8. Open questions and unresolved tensions

1. **Is the two-layer architecture the right bet?** Notes quality depends on LLM generation. If generated notes are mediocre, Layer 2 adds noise rather than signal. There is no mechanism to detect or flag low-quality notes.

2. **curate() as "the preferred entry point" — is this justified?** Tier 0 returns sorted raw results with no deduplication or synthesis. A simple `search()` call is functionally equivalent. The differentiation only exists in tier 1, which is not built.

3. **The Librarian workaround**: the subagent delegation plan (Claude Code plugin + `/ask-vault`) assumes the user has Claude Code. Users with other MCP clients (Claude Desktop, custom) get no Librarian. This creates an implicit platform dependency that is not stated in the vision.

4. **One note per source**: the "densification" thesis requires notes to accumulate and synthesize across sources. The current model creates exactly one note per source, which never merges with others. The thesis is structurally blocked.

5. **Calibration problem**: `escalation_max_distance = 0.5` is the most important parameter in curate() and it is a pure guess. Wrong values mean either: always returning notes (missing relevant chunks) or always escalating to chunks (defeating the two-layer point).

6. **The evaluation gap**: 511 tests pass, but they are all mocked at the LLM/embedding boundary. There is no test that validates semantic relevance. The suite gives confidence in plumbing, not in quality.

7. **Target user**: one user, local machine, Obsidian, French-language notes. The architecture is general but every real-world decision (FR tokenizer, kebab-case tags, Obsidian export) reflects a single-user profile. Is this a product or a personal tool?

8. **Semantic clustering**: the brainstorm from 2026-08-10 (HDBSCAN on embeddings → cluster tags in Obsidian) could be a cheaper and more reliable path to "emergent connections" than LLM-based synthesis. Its relationship to the existing roadmap is undefined.

---

## 9. What a review should challenge

- Is the curate()/Librarian pattern actually solving the right problem, or is it complexity added to compensate for inadequate retrieval?
- Does the "two-layer" thesis hold if note quality is unverified?
- Is the roadmap order correct? Should evaluation come before feature work?
- Is the workaround Librarian (subagent delegation) worth shipping before MCP sampling exists?
- Are there architectural patterns in comparable systems (NotebookLM, Mem.ai, Obsidian Smart Connections) that EgoVault is ignoring?
- What is the single most important thing that would make this system meaningfully better for a real user today?
