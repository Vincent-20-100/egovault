# EgoVault — User Guide

> The full operating manual. For a 10-minute zero-to-first-note tutorial, read
> [`docs/GETTING-STARTED.md`](../GETTING-STARTED.md) first. This guide goes
> deeper — concepts, configuration, workflows, references, and troubleshooting.

## Table of contents

| # | Chapter | What it covers |
|---|---|---|
| 01 | [Concepts](01-concepts.md) | Sources, chunks, notes, tags, the two-tier RAG-vs-compiled model, the Librarian (`curate()`) |
| 02 | [Installation](02-installation.md) | Prerequisites, venv, `uv sync --all-extras`, `init_user_dir`, sanity check |
| 03 | [Configuration](03-configuration.md) | Full reference of the three yaml files — every flag explained |
| 04 | [Providers](04-providers.md) | LLM and embedding personas (local Ollama / cloud / hybrid / MCP-only), model recommendations |
| 05 | [Ingest](05-ingest.md) | YouTube, audio, PDF, text, web — pipeline stages, large-format gate, queue patterns |
| 06 | [Search and curate](06-search-and-curate.md) | Tier-0/1/2 retrieval, escalation, **hybrid (RRF + BM25)**, when to enable |
| 07 | [Notes](07-notes.md) | Generation, draft → active approval, templates, tag rules, lifecycle |
| 08 | [CLI reference](08-cli.md) | Every `egovault` command with options and examples |
| 09 | [MCP integration](09-mcp.md) | Claude Desktop, Claude Code, exposed tools, safety gates |
| 10 | [Obsidian](10-obsidian.md) | Vault layout, sync watcher, tags, links, graph view |
| 11 | [Maintenance](11-maintenance.md) | Re-embedding, backup, FTS5 backfill, OpenTimestamps, monitoring |
| 12 | [Troubleshooting](12-troubleshooting.md) | Known pitfalls (Ollama down, RAM tight, mojibake, encoding, `gh` missing, etc.) |

## How this guide is maintained

This user-guide is **load-bearing documentation**: any change in code that
affects user-visible behavior (new config flag, new provider, new CLI command,
new MCP tool, breaking change) MUST update the relevant chapter(s) in the
same change. This rule is enforced in `CLAUDE.md` § Automatisms.

If you find a discrepancy between code and a chapter, the code is authoritative
— please open an issue or PR fixing the doc.

## Related documents

- [`docs/VISION-KNOWLEDGE-COMPILER.md`](../VISION-KNOWLEDGE-COMPILER.md) — the
  product thesis (RAG retrieves and forgets; a compiler accumulates)
- [`docs/architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md) —
  developer/architect view
- [`docs/architecture/DATABASES.md`](../architecture/DATABASES.md) — DB schema
- [`docs/FUTURE-WORK.md`](../FUTURE-WORK.md) — backlog / decided-not-implemented
- [`.meta/audits/`](../../.meta/audits/) — historical audits (real-world test
  findings, RRF experiment results, etc.)
