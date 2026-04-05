# EgoVault — Claude Code Entry Point

> **The law.** Few rules, non-negotiable. Read this, then read what it points to.

---

## 1. Project identity

EgoVault is a **personal knowledge vault** — ingest sources (YouTube, audio, PDF, text),
extract and chunk content, embed it for semantic search, and generate structured notes.

**Vision & strategy:** `docs/VISION.md`

---

## 2. Tech stack

Python 3.x · SQLite + sqlite-vec · Ollama/OpenAI · Pydantic v2 · FastAPI · Click CLI · FastMCP · pytest

---

## 3. Project structure

```
core/                    ← config, schemas, context, uid, logging, errors
tools/
├── media/               ← transcribe, compress, fetch_subtitles, extract_audio
├── text/                ← chunk, embed, embed_note, summarize, parse_html
├── web/                 ← fetch_web (URL fetch + extract with SSRF protection)
├── vault/               ← create_note, update_note, search, finalize_source,
│                          delete_note, delete_source, restore_note, restore_source,
│                          generate_note_from_source, purge
└── export/              ← typst, mermaid
workflows/
└── ingest.py            ← unified pipeline — ingest(source_type, target, ctx)
infrastructure/          ← db.py, vault_writer.py, embedding_provider.py, llm_provider.py
api/                     ← FastAPI — routers: health, jobs, ingest, notes, sources, search, vault, monitoring
cli/                     ← Click CLI — commands: ingest, search, notes, sources, status, purge
mcp/server.py            ← exposes tools/ via MCP protocol
config/                  ← system.yaml (versioned), user.yaml + install.yaml (gitignored)
tests/                   ← mirrors source structure
.meta/                   ← process workspace (specs, plans, audits, scratch, archive)
```

---

## 4. Commands

```bash
python -m pytest tests/          # tests
python mcp/server.py             # MCP server (dev)
```

---

## 5. Automatisms

These behaviors are hard-wired. Do them without being asked.

1. **Session start** — read `PROJECT-STATUS.md` + `SESSION-CONTEXT.md` before anything.
2. **Before any Edit or Write** — you must have proposed a plan and received user approval. If no plan exists, propose one. Never implement without explicit user go-ahead.
3. **Every commit** — `feat:` / `fix:` / `docs:` / `chore:` + description in English.
4. **Milestone done** — update `PROJECT-STATUS.md`.
5. **Session end** (user signals stop) — update `PROJECT-STATUS.md` + rewrite `SESSION-CONTEXT.md`, commit+push before confirming.
6. **Always** — apply rules from `.meta/GUIDELINES.md`. Read it at session start.
7. **Never** — make autonomous decisions on topics listed in "Open questions" in `SESSION-CONTEXT.md`.

---

## 6. Development workflow

```
BRAINSTORM → SPEC → PLAN → IMPLEMENT → TEST → AUDIT → SHIP
```

Full spec: `.meta/specs/2026-03-31-development-workflow.md`

| Task | Skill |
|------|-------|
| Brainstorming | `superpowers:brainstorming` |
| Write plan | `superpowers:writing-plans` |
| Execute plan | `superpowers:executing-plans` |
| Code review | `superpowers:requesting-code-review` |
| Debug | `superpowers:systematic-debugging` |

**Superpowers plugin required:** `/install-plugin obra/superpowers`

---

## 7. Superpowers output paths

Specs and plans go in `.meta/`, not `docs/superpowers/`:
- Brainstorm drafts → `.meta/scratch/spec-<topic>.md`
- Plan drafts → `.meta/scratch/plan-<topic>.md`
- Once validated → move to `.meta/specs/` or `.meta/plans/`
- Audits → `.meta/audits/audit-results-<date>.md`

---

## 8. Key documents

| Document | Role |
|----------|------|
| `.meta/GUIDELINES.md` | Rules G1-G13, conventions, architecture boundaries |
| `docs/architecture/ARCHITECTURE.md` | Technical architecture, glossary |
| `docs/architecture/DATABASES.md` | DB schema (must match `infrastructure/db.py`) |
| `PROJECT-STATUS.md` | Live project state — next action, debt, roadmap |
| `SESSION-CONTEXT.md` | Living context — decisions, traps, open questions |

**Authority:** CLAUDE.md > ARCHITECTURE.md > code comments. Permanent docs > provisional docs.
