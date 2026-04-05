# EgoVault — Product Audit & Improvement Reference

**Date:** 2026-03-29
**Status:** Validated by project owner — serves as reference for all future plans
**Scope:** Product logic, coherence, DX, prioritization — NOT a code or security audit
**Method:** External review of architecture, specs, implementation, README, and workflows

---

## Table of contents

Each section is a standalone file in `docs/product-audit/` for easy consumption by LLMs and humans.

| # | Section | File | Key takeaway |
|---|---------|------|-------------|
| 1 | [Executive summary](product-audit/01-executive-summary.md) | `01-executive-summary.md` | Core value loop is broken — notes are never embedded, no user-facing surface |
| 2 | [MCP critical gap](product-audit/02-mcp-critical-gap.md) | `02-mcp-critical-gap.md` | Priority A fixes (embed_note, MCP completeness, setup docs) + Priority B (internal LLM path) |
| 3 | [Workflow audit](product-audit/03-workflow-audit.md) | `03-workflow-audit.md` | Workflows work correctly — gap is downstream (note creation) |
| 4 | [Tools audit](product-audit/04-tools-audit.md) | `04-tools-audit.md` | Missing tools inventory, MCP description enrichment needed |
| 5 | [Missing features](product-audit/05-missing-features.md) | `05-missing-features.md` | 4-tier prioritization (28 items) |
| 6 | [Spec reprioritization](product-audit/06-spec-reprioritization.md) | `06-spec-reprioritization.md` | New roadmap order — user value before internal optimization |
| 7 | [Developer experience](product-audit/07-developer-experience.md) | `07-developer-experience.md` | CLI sketch, Quick Start gaps, DX wins and losses |
| 8 | [Large format handling](product-audit/08-large-format-handling.md) | `08-large-format-handling.md` | Blind spot — needs dedicated brainstorming |
| 9 | [README alignment](product-audit/09-readme-alignment.md) | `09-readme-alignment.md` | Aspirational README + beta disclaimer |
| 10 | [Open questions](product-audit/10-open-questions.md) | `10-open-questions.md` | 10 topics for future brainstorming sessions |
| 11 | [Document extraction](product-audit/11-document-extraction.md) | `11-document-extraction.md` | Tiered architecture: builtin → markitdown → chandra |
| 12 | [Provider coherence](product-audit/12-provider-coherence.md) | `12-provider-coherence.md` | One API key should unlock the full stack |
| 13 | [Extended inventory](product-audit/13-extended-inventory.md) | `13-extended-inventory.md` | Consolidated tools & workflows inventory with priorities |

---

## Quick reference — what changed in the roadmap

The audit recommended reordering the implementation roadmap (see [section 6](product-audit/06-spec-reprioritization.md)):

```
Block A — Core value loop (before optimizing anything):
  A0: Security Phase 1
  A1: MCP flow fix (embed_note, MCP completeness, setup docs)
  A2: CLI
  A3: Delete operations
  A4: Internal LLM path (auto_generate_note)

Block B — Infrastructure (after users and data exist):
  B1: embedding.dims fix
  B2: Security Phase 2
  B3: Monitoring

Block C — User surface:
  C1: Frontend

Block D — Search quality (after notes_vec is populated):
  D1: Reranking
  D2: Semantic cache
  D3: Benchmark
```

This order is now reflected in `CLAUDE.md` (Progress status section).

---

*Audit conducted 2026-03-29. Validated by project owner same day.*
*Sections 11-13 added 2026-03-29 after tools/workflows/extraction/provider analysis.*
*Split into sub-files 2026-03-30 for LLM-friendly consumption.*
