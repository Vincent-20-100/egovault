# EgoVault — Strategic Positioning Brief

**Purpose:** External strategic review. No code. No implementation details.
The question is whether the vision is right, not whether the code is correct.

---

## The vision in one sentence

A personal knowledge vault, MCP-native by design, that gives individuals
the same LLM-ready knowledge infrastructure that companies are starting
to build internally — local-first, private, extensible to any ingestion
source.

---

## The core insight behind the project

Companies are building internal RAG pipelines over their documents (Confluence,
Notion, email, Slack, meeting recordings). These systems let their LLMs answer
questions grounded in company knowledge. There is no clean personal equivalent.

Individuals accumulate knowledge across YouTube videos, podcasts, PDFs, web
articles, books, and increasingly email and messages — but have no infrastructure
to make that knowledge queryable by an LLM in a structured, controlled way.

EgoVault's thesis: **the personal knowledge stack is 2–3 years behind the
enterprise knowledge stack, for the same structural reasons enterprise AI adoption
is ahead.** The gap is real and will be filled.

---

## Why MCP specifically

MCP (Model Context Protocol) is the emerging standard for LLMs to interact with
external tools and data sources. Designing around MCP means:

- Any LLM client (Claude, future clients) can call EgoVault tools natively
- The vault becomes part of the LLM's tool ecosystem, not a silo it talks to
- New capabilities (new search modes, ingestion sources, export formats) are
  exposed automatically to any MCP-compatible client
- The user doesn't need a frontend — the LLM interface IS the interface

This is not "we added an MCP wrapper." The MCP server is a primary surface,
designed alongside the data model, not bolted on.

---

## What EgoVault exposes today via MCP

A complete toolkit for personal knowledge:
- Ingest: YouTube, audio, PDF, web pages, plain text (email, Slack next)
- Process: chunk, embed, generate structured notes via LLM
- Retrieve: semantic search over chunks and notes; curate() for prioritized context
- Manage: create, update, delete, restore notes and sources
- Export: Obsidian markdown with frontmatter and tags

The design goal: one MCP server, full toolkit, so the user's LLM can manage
their knowledge base end-to-end through natural conversation.

---

## Differentiation axes

| Axis | EgoVault | NotebookLM | Khoj | Obsidian plugins |
|------|----------|------------|------|-----------------|
| Local-first, private | Yes | No (cloud) | Yes | Yes |
| MCP-native design | Yes | No | Partial | No |
| Multi-source ingestion | Yes (8 types) | Limited | Yes | No |
| Structured note generation | Yes (LLM draft) | Yes | No | Plugins |
| Open, self-hostable | Yes | No | Yes | Yes |
| Obsidian integration | Yes | No | No | Native |
| Personal (not enterprise) | Yes | Yes | Yes | Yes |

---

## The extensibility bet

Once the core ingestion + retrieval + MCP layer is solid, adding new sources
is a single extractor module:
- Email (IMAP/Gmail)
- Slack / Discord messages
- Calendar + meeting notes
- Kindle highlights / Readwise
- Browser bookmarks

The value of EgoVault grows with the number of sources connected. This is
the same compounding dynamic as enterprise knowledge bases — richer input,
better retrieval, more useful LLM interactions.

---

## What we do NOT know

1. **Is the market timing right?** MCP is very new (2024–2025). Is the ecosystem
   mature enough for this to be useful to anyone other than early adopters?

2. **Is local-first the right bet?** Privacy is a real value for some users.
   For others, a cloud solution with better UX wins. Which user is the target?

3. **Who else is doing this well?** The competitive landscape may have shifted.
   Are there projects we are unaware of that already fill this gap?

4. **Build vs. compose?** Should EgoVault be built from scratch, or built on
   top of an existing project (Khoj? Fabric? something else)? We may be
   reinventing infrastructure that already exists.

5. **Is the Obsidian integration an asset or a constraint?** It covers the UI
   need for the current user but ties the project to a niche audience.

---

## The question for this review

Please assess:

1. **Is this a real gap?** Does a personal MCP-native knowledge vault with
   local-first + extensible ingestion fill a space that is genuinely underserved?

2. **Who is closest?** Which existing projects — open source or commercial —
   come closest to this vision? What do they do well or poorly?

3. **Is "build on top of X" smarter than build from scratch?** If a strong
   foundation already exists, EgoVault should compose, not compete.

4. **Is the vision coherent?** Does "personal enterprise knowledge stack via MCP"
   hold together as a positioning, or is it trying to be too many things?

5. **What is the one thing that would make this genuinely compelling** vs.
   a competent but forgettable tool in a crowded space?
