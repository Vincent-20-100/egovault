# EgoVault — Strategic Brief v2

**Purpose:** Concrete strategic decisions. The positioning is validated — now define what EgoVault is, what it is not, and what to build in what order.

---

## What we know (validated)

### The vision — confirmed

A personal knowledge vault, MCP-native, that gives individuals the same LLM-ready knowledge infrastructure companies are building internally. Local-first, private, extensible, open.

### The key insight from a first strategic review

The market is crowded on infrastructure (ingestion, RAG, MCP wrappers). The real unsolved gap is **retention and trust**: why does someone still use their vault at month nine, and how do they know what the LLM tells them is grounded in something they actually endorsed?

The correct repositioning:

> **EgoVault is the part of your memory you signed off on.** Everything the LLM tells you from it traces to a source you ingested and a note you approved. Plain markdown you own, that outlives any model, vendor, or subscription.

### The nuance that makes it concrete

The synthesis note is not just an LLM summary. It is a **two-layer object**:

1. **The raw source** — full transcript, original content, verbatim, lossless, always retrievable
2. **Your personal note** — customizable by you, your angle, your connections, your critique, your tags

The LLM generates a draft. You shape it into your own thinking. Both layers are embedded and searchable. This is what "signed off on" means in practice: not just approval, but active authorship on top of the source material.

No competitor does this combination: raw + personal synthesis + both searchable via MCP + human-approved lifecycle.

### The closest competitors

- **Open Notebook** — strongest on multi-source ingestion + MCP + UI. Weak on the human-approval lifecycle and personal annotation layer.
- **Basic Memory** — strongest on philosophy (markdown as truth, MCP-native). Weak on multimedia ingestion.
- **SurfSense** — strongest on connectors. Weak on the personal knowledge angle.
- **NotebookLM** — wins on convenience for casual use. No personal layer, no local, no MCP.
- **Claude/ChatGPT memory** — opaque, auto-generated, not auditable, vendor-locked. The opposite of what EgoVault is.

---

## What needs to be decided

### Decision 1 — What is EgoVault NOT

The first strategic review identified three products in one coat: NotebookLM alternative, MCP toolkit, Obsidian pipeline. Which of these is primary? What does EgoVault explicitly refuse to be?

### Decision 2 — Obsidian: export target or storage substrate?

Currently Obsidian is an export target (DB is truth, Obsidian is output). Basic Memory's model is the opposite: markdown files ARE the truth, SQLite is a rebuildable index. Which model is correct for EgoVault's vision?

If markdown-on-disk is truth: interoperability with every tool, no vendor dependency, the vault genuinely outlives anything.
If SQLite is truth: richer data model, embeddings, relational integrity — but Obsidian is a cosmetic layer.

This is the most consequential architectural decision still open.

### Decision 3 — Build vs. consume on connectors

Building extractors for email, Slack, calendar etc. is competitive parity with SurfSense, not differentiation. Consuming MCP servers that already exist for these sources keeps EgoVault thin and focused. Which is right?

### Decision 4 — The one metric that defines success

"LLM-ready knowledge infrastructure" is not measurable. What is the one thing a user can do at month nine that they couldn't at month one — that proves EgoVault worked?

---

## The question for this review

Given the validated vision, the competitive landscape, and the open decisions above:

1. **What should EgoVault explicitly be, and explicitly not be?** One crisp sentence each.

2. **Obsidian: export target or storage substrate?** Which model is more defensible long-term?

3. **What is the correct build order** for the next 3–6 months, given the real differentiator is provenance + personal layer, not ingestion breadth?

4. **What should EgoVault stop doing or building** immediately — things that are consuming effort but are not defensible?

5. **What does "success at month nine" look like** for the target user? Make it concrete and measurable.
