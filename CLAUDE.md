# EgoVault — Claude Code Entry Point (CLAUDE.md)

> **The Law.** High-signal, non-negotiable rules for working in this repository.
> For the universal multi-agent constitution, see [`AGENTS.md`](AGENTS.md).

---

## 1. Project Identity & Cognitive Architecture

EgoVault is a **personal knowledge compiler and cognitive memory engine** based on human neuroscience:
- **Tier 1 (Chunks):** Raw verbatim evidence in SQLite + `chunks_vec`.
- **Tier 2 (Notes):** Distilled conceptual nuclei in Obsidian Markdown + `notes_vec`.
- **Tier 3 (Working Memory):** High-density conceptual context retrieved via `curate()`.

Core Vision: [`docs/VISION-KNOWLEDGE-COMPILER.md`](docs/VISION-KNOWLEDGE-COMPILER.md)

---

## 2. Tech Stack

Python 3.13+ · SQLite + sqlite-vec · FTS5 BM25 · Ollama / Anthropic · Pydantic v2 · FastAPI · FastMCP · Typer CLI · pytest

---

## 3. Project Structure

```
core/           ← schemas, errors, config, context, uid, logging, security, sanitize
tools/
├── media/      ← transcribe, compress, fetch_subtitles, extract_audio, parse_document, ocr
├── text/       ← chunk, embed, embed_note, parse_html, segment
├── web/        ← fetch_web (SSRF protected)
├── vault/      ← create_note, update_note, search, curate, finalize_source, delete_*, restore_*, purge
└── export/     ← typst, mermaid
workflows/      ← ingest.py (unified extraction & segmentation pipeline)
infrastructure/ ← db.py, vault_writer.py, embedding_provider.py, llm_provider.py
api/            ← FastAPI routers: health, jobs, ingest, notes, sources, search, vault, monitoring
cli/            ← Typer CLI commands
mcp/            ← FastMCP server exposing tools/
config/         ← system.yaml (versioned), user.yaml + install.yaml (gitignored)
tests/          ← mirrors source structure
.meta/          ← process workspace: specs, plans, audits, scratch, archive
```

---

## 4. Commands

```bash
uv run pytest tests/           # Full deterministic test suite
uv run python mcp/server.py    # FastMCP server in dev mode
uv run egovault --help         # Typer CLI entrypoint
```

---

## 5. Non-Negotiable Automatisms

1. **Session Start:** Read `PROJECT-STATUS.md` and `SESSION-CONTEXT.md` before taking any action.
2. **No Code Without a Plan:** Never edit or write code without an approved plan in `.meta/plans/`.
3. **Zero-Hardcode (Rule G3):** No magic numbers or hardcoded model/algorithm values in Python. Everything is configured in `config/`.
4. **Error Architecture V2 (Rule G6):** All exceptions inherit from `EgoVaultError` with mandatory `error_code`, `user_message`, `actionable_hint`, and `http_status`.
5. **Doc-Maintenance Synchronized (Automatism):** Any change impacting user-visible behavior MUST update `docs/user-guide/` in the same commit.
6. **Session End:** Update `PROJECT-STATUS.md` and rewrite `SESSION-CONTEXT.md` before confirming stop.

---

## 6. Engineering Lifecycle

```
BRAINSTORM → SPEC → PLAN → IMPLEMENT (TDD) → TEST → AUDIT → SHIP
```

- Process Specification: [`.meta/WORKFLOW.md`](.meta/WORKFLOW.md)
- Audit Specification: [`.meta/AUDIT-SPEC.md`](.meta/AUDIT-SPEC.md)
- Universal Constitution: [`AGENTS.md`](AGENTS.md)
