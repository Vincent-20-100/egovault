---
mode: deep
date: 2026-05-19
slug: tencentdb-agent-memory
url: https://github.com/Tencent/TencentDB-Agent-Memory
angle: local 4-tier progressive memory vs EgoVault knowledge-compiler tiers + progressive-disclosure
status: active
---

# Deep — Tencent/TencentDB-Agent-Memory

## 1. Fingerprint

- **Primary lang:** TypeScript
- **Repo type:** agent memory layer (OpenClaw plugin + Hermes gateway)
- **License:** present (see LICENSE)
- **Stars / last commit:** unknown (`gh` unavailable)
- **Pitch:** "Fully local long-term memory for AI agents via a 4-tier
  progressive [semantic pyramid]."

## 2. Structure map

```
src/  core/ adapters/ gateway/ offload/ cli/ utils/ config.ts   ← engine (TS)
hermes-plugin/memory/                                           ← gateway adapter
scripts/  memory-tencentdb-ctl.sh install_hermes_memory...sh setup-offload.sh
docker/opensource/      openclaw.plugin.json  SKILL.md          ← deploy + skill
vitest.config.ts / vitest.e2e.config.ts                         ← tests
```

## 3. Key findings

### 3.1 Extension points
- `src/adapters/` + `src/gateway/`: storage backends are pluggable
  (SQLite+sqlite-vec default; Tencent Cloud Vector DB optional). *Why it
  matters:* same adapter seam EgoVault has via `infrastructure/` — and the
  **default backend is literally SQLite + sqlite-vec, identical to EgoVault**.
- `src/offload/`: a self-contained context-compression module. *Why:*
  cleanly separable concept (see 3.5).

### 3.2 Safety & governance
- Lower tiers (L0/L1) "persist as evidence layers for traceability"; drill
  down via `node_id` on error/verification. *Why:* same provenance principle
  as EgoVault (sources immutable, notes cite source UIDs) — independently
  arrived at; reinforces keeping verbatim UIDs through curate().

### 3.3 Documentation quality
- README precisely specifies tiers, promotion cadences, storage split, recall
  strategy with concrete config keys. Bilingual (EN/CN). *Why:* reusable as a
  reference spec; the tier/cadence numbers are concrete enough to compare.

### 3.4 Developer workflow
- OpenClaw plugin: `openclaw plugins install @tencentdb-agent-memory/...`,
  auto-captures + extracts + recalls before each turn. *Why / contrast:*
  EgoVault is MCP-first + human-approval-gated (notes start `draft`);
  TencentDB is autonomous/transparent-to-the-agent. Different control model.

### 3.5 Distinctive patterns (the high-signal ones)
- **4-tier semantic pyramid:** L0 raw dialogue → L1 atomic facts → L2 scene
  blocks (themed) → L3 persona (synthesis). Promotion by *extraction cycles*
  (L1 every ~5 turns, L3 every ~50 atoms), **no decay**, lower tiers kept as
  evidence. *Why it matters:* near-isomorphic to EgoVault's
  raw-source → chunk → note → compiled-overview, and to the 4-layer
  progressive-disclosure pattern already in the EgoVault memory. Independent
  convergence = strong validation of the Knowledge Compiler architecture.
- **Heterogeneous storage split:** L0/L1 in DB for full-text retrieval;
  L2/L3 as **human-readable Markdown** for density + white-box inspection.
  *Why:* this is EXACTLY EgoVault's split (chunks in sqlite-vec; notes as
  Obsidian markdown in `egovault-user/vault/`). Two projects, same stack,
  same split, independently. The architecture is not idiosyncratic — it's
  convergent SOTA.
- **Hybrid recall: BM25 keyword + embedding, fused via RRF**, top-5 default,
  configurable. *Why it matters MOST:* this is a concrete, deterministic,
  same-stack (sqlite-vec) mitigation for EgoVault **finding E** (FR cosine
  imprecision) — add BM25 + Reciprocal Rank Fusion alongside cosine in
  curate() tier-0, no embedding-model swap. Third independent project to
  reject pure cosine.
- **"Offload" symbolic memory:** verbose tool outputs → `refs/*.md`; only a
  compact Mermaid map with `node_id` stays in context; agent greps full text
  by node_id on demand. *Why:* same token-frugal progressive-disclosure idea
  as deep #1's `hot.md`/`index.md` precedence — convergent with curate()'s
  "return minimal curated context, drill down by UID" goal.

## 4. Tiered recommendations

- **USE AS-IS:** (none) — TypeScript/OpenClaw plugin; EgoVault is Python/MCP.
- **EXTRACT PARTS:** the **BM25 + cosine → RRF fusion** recall strategy. It is
  the single most actionable, low-risk win here: deterministic, runs on the
  existing sqlite-vec stack, directly targets finding E, fits curate() tier-0
  (no LLM). Prototype in the search-quality track against the finding-E corpus.
- **BORROW CONCEPTS:** explicit promotion *cadence* (extract every N) as a
  model for batched note generation; "lower tiers as evidence, drill by
  node_id" as the curate() drill-down contract; the L0–L3 naming as a sanity
  check on EgoVault's own tier vocabulary.
- **INSPIRATION:** the DB-for-recall / Markdown-for-synthesis split as
  external validation that EgoVault's architecture is correct; "offload +
  Mermaid map + node_id grep" as a possible MCP response shape for very large
  curate() results.
- **REJECT:** the autonomous capture/recall model (EgoVault keeps the human
  approval gate); the OpenClaw/Hermes coupling; persona/L3 (EgoVault is not a
  personal-profile system — its L3 is cross-source knowledge synthesis, not a
  user model).

## 5. Open questions for follow-up

1. RRF(BM25, cosine) on the finding-E corpus: does it fix the rank-2 / missed
   exact-topic cases from `2026-05-17-real-ingest-test-results.md`? First
   experiment of the search-quality track. sqlite-vec already in place; BM25
   via SQLite FTS5 is cheap.
2. Three-way convergence: claude-obsidian (structural precedence), PageIndex
   (LLM tree reasoning), TencentDB (BM25+vector RRF) all reject pure cosine.
   These are three points on ONE design space for curate(). Synthesize into a
   single curate() retrieval redesign brainstorm (see synthesis note).
3. Does EgoVault want an explicit promotion *cadence* (auto note-gen every N
   sources) or stay manual/approval-gated? Architecture decision, not a quick
   call — defer to brainstorm.
