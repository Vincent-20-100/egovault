# EgoVault CLI — Design Spec

**Date:** 2026-03-30
**Status:** Approved
**Roadmap item:** A2 — CLI

---

## 1. Purpose

The CLI is the primary human-facing surface for EgoVault before the frontend is complete. It exposes all features accessible via command line without requiring a running server. It is a convenience layer — not a permanent product surface — and must stay simple.

---

## 2. Architecture

```
cli/
├── __init__.py
├── main.py              ← entry point, assembles command groups
├── output.py            ← rich helpers (table, panel, progress bar, json flag)
└── commands/
    ├── __init__.py
    ├── ingest.py        ← egovault ingest <url/file>
    ├── search.py        ← egovault search <query>
    ├── notes.py         ← egovault note list/get/create/update/approve
    ├── sources.py       ← egovault source list/get/generate-note
    └── status.py        ← egovault status
```

**Position in the hexagonal architecture:** `cli/` sits at the same level as `api/` — a routing layer only. Zero business logic. It calls `workflows/` for ingestion and `tools/` for search/notes/sources, exactly as `api/routers/` does.

**Architecture doc updates required:** Add `cli/` to `ARCHITECTURE.md` §2.2 directory tree and to `CLAUDE.md` structure tree.

**Entry point** added to `pyproject.toml`:
```toml
[project.scripts]
egovault = "cli.main:app"
```

After `uv sync`, `egovault` is available as a terminal command.

**New dependencies** added to `pyproject.toml`:
- `typer>=0.12`
- `rich>=13`

---

## 3. Command interface

### Global flags (available on all commands)

| Flag | Description |
|---|---|
| `--json` | Output raw JSON to stdout (for piping/scripting) |
| `--verbose` | Show internal details: timings, IDs, distances, step-by-step status |

`--json` and `--verbose` are combinable: produces enriched JSON output.

### 3.1 Ingest

```bash
egovault ingest <url_or_file> [--generate-note] [--no-generate-note] [--json] [--verbose]
```

- Auto-detects input type: YouTube URL, audio file (`.mp3`, `.mp4`, `.wav`, `.m4a`, `.ogg`, `.webm`), or PDF.
- Calls the corresponding workflow directly: `ingest_youtube`, `ingest_audio`, or `ingest_pdf`.
- **Synchronous and blocking** — no job_id, no polling. Simpler than the API's async model.
- Default output: `rich` progress bar showing each pipeline step (fetch → chunk → embed → done), then a summary panel with `slug`, `uid`, and final status.
- `--verbose`: adds per-step timing (e.g. `fetch: 1.2s`, `chunk: 0.1s`, `embed: 3.4s`).
- `--generate-note`: forces `auto_generate_note=True` for this ingest (overrides config).
- `--no-generate-note`: forces `auto_generate_note=False` (overrides config).
- Neither flag: reads `user.yaml` default (`llm.auto_generate_note`).

### 3.2 Search

```bash
egovault search <query> [--limit 10] [--mode chunks|notes] [--json] [--verbose]
```

- Calls `tools/vault/search.py` directly.
- Default output: `rich` table with columns `title | score | excerpt`.
- Scores are shown by default — they are useful information, not a debug detail.
- `--verbose`: adds `distance` (raw float), `chunk_uid`, `note_uid`, execution time.

### 3.3 Notes

```bash
egovault note list    [--limit 20] [--offset 0] [--type synthese] [--tags biais-cognitifs,economie] [--status draft|active] [--json] [--verbose]
egovault note get     <uid>        [--json] [--verbose]
egovault note create  --from-file <path.yaml> [--json] [--verbose]
egovault note update  <uid> [--title "..."] [--body "..."] [--rating 4] [--status draft|active] [--json] [--verbose]
egovault note approve <uid> [--json] [--verbose]
```

- `list`: calls `infrastructure/db.py:list_notes` — table with `uid | title | type | status | date_created`.
  - `--type`: filter by `note_type` (synthese, concept, reflexion).
  - `--tags`: comma-separated list of tags to filter by.
  - `--status`: filter by `status` (draft, active).
- `get`: calls `infrastructure/db.py:get_note` — rich panel with all fields.
- `create`: calls `tools/vault/create_note.py`. Uses `--from-file` exclusively (see §3.3.1).
- `update`: calls `tools/vault/update_note.py`. Editable fields: `title`, `docstring`, `body`, `note_type`, `source_type`, `rating` (1-5), `url`, `status` (draft, active). System fields (`uid`, `date_created`, `source_uid`, `generation_template`) are immutable.
- `approve`: shortcut for `update_note(status='active')` + conditional `finalize_source` if source is `rag_ready`. This cascade lives in the CLI routing layer, not in the tool (G4).
- `--verbose` on `list`/`get`: shows all database fields including `source_uid`, `generation_template`.

#### 3.3.1 `note create --from-file`

Note creation via CLI uses a YAML file containing all `NoteContentInput` fields. This avoids the impractical problem of passing multi-line Markdown body via CLI flags.

```bash
egovault note create --from-file my-note.yaml [--json] [--verbose]
```

Expected YAML structure:

```yaml
source_uid: "abc123-..."       # required (null for source-less notes)
title: "Elasticite des prix"   # required, 3-200 chars
docstring: |                   # required, max 300 chars
  Synthese sur l'elasticite des prix.
  Pourquoi c'est central en microeconomie.
  These: l'elasticite depend du cadre temporel.
body: |                        # required, Markdown
  ## Contexte
  L'elasticite mesure la sensibilite...
note_type: synthese            # optional: synthese | concept | reflexion
source_type: youtube           # optional: youtube | audio | pdf
tags:                          # required, 1-10 items
  - elasticite
  - microeconomie
  - prix
```

The CLI validates the YAML against `NoteContentInput` (Pydantic) before calling the tool. Validation errors are shown as user-friendly messages (G1/G6).

### 3.4 Sources

```bash
egovault source list          [--limit 20] [--offset 0] [--status rag_ready] [--json] [--verbose]
egovault source get           <uid>        [--json] [--verbose]
egovault source generate-note <uid> [--template standard] [--json] [--verbose]
```

- `list`: calls `infrastructure/db.py:list_sources` — table with `uid | slug | source_type | status | date_created`.
  - `--status`: filter by status (`raw`, `rag_ready`, `vaulted`). **Primary use case:** `egovault source list --status rag_ready` to find sources ready for note creation.
- `get`: calls `infrastructure/db.py:get_source` — rich panel with all fields including `url`, `transcript` (truncated by default, full with `--verbose`).
- `generate-note`: calls `tools/vault/generate_note_from_source.py`. Creates a `draft` note from the source using the configured LLM. Requires A4 (internal LLM path).

### 3.5 Status

```bash
egovault status [--limit 10] [--json] [--verbose]
```

- Reads recent jobs from `.system.db` — these are jobs created by the API (async path).
- CLI ingestion runs are synchronous and not recorded as jobs. `status` reflects API activity only.
- Default output: `rich` table with `job_id (short) | type | status | created_at | result`.
- `--verbose`: full `job_id`, `started_at`, `completed_at`, full result payload.

---

## 4. Output layer (`cli/output.py`)

Centralises all `rich` usage. Commands do not import `rich` directly.

Key helpers:
- `print_table(columns, rows, json_mode, verbose)` — renders a `rich.Table` or JSON array
- `print_panel(title, fields, json_mode, verbose)` — renders a `rich.Panel` or JSON object
- `print_progress(steps)` — context manager wrapping `rich.Progress` for ingestion
- `print_error(message, code, verbose)` — red error message or `{"error": ..., "code": ...}` JSON

---

## 5. Error handling

- User-facing messages describe capabilities, not implementation details (G1/G6).
- Exit code `1` on error (Unix convention — enables shell scripting).
- Default: short red message via `rich` (e.g. `Error: PDF parsing failed`).
- `--verbose`: adds error type and context, no stack trace, no library names.
- `--json`: `{"error": "PDF parsing failed", "code": "parse_error"}`.
- The CLI catches Python exceptions (FileNotFoundError, ValueError, `NotFoundError`, `ConflictError`, `LargeFormatError`, etc.) and maps them to user-friendly messages. `NotFoundError` and `ConflictError` must be added to `core/errors.py` if not already present (see §7.1).

---

## 6. Tests

- `tests/cli/` mirrors `cli/commands/`.
- Test behavior via Typer's `CliRunner` (built-in test client).
- Mock `workflows/` and `tools/` — do not mock internals.
- One test file per command group: `tests/cli/test_ingest.py`, `test_search.py`, `test_notes.py`, `test_sources.py`, `test_status.py`.

---

## 7. Prerequisites and dependencies

### 7.1 New error types needed in `core/errors.py`

`core/errors.py` currently only contains `LargeFormatError`. The following error types are used by A2, A3, and A4 specs and must be created:

```python
class NotFoundError(Exception):
    """Raised when a requested resource (note, source) does not exist."""

class ConflictError(Exception):
    """Raised when an operation conflicts with current state
    (e.g., note already exists for source, item already pending_deletion)."""
```

These are shared prerequisites across A2, A3, and A4. They should be created as part of whichever spec is implemented first.

### 7.2 A4 commands

The following commands depend on A4 (internal LLM path) being implemented:
- `egovault source generate-note`
- `egovault note approve`
- `egovault ingest --generate-note / --no-generate-note`
- `egovault note list --status draft|active`
- `egovault note update --status draft|active`

If A2 is implemented before A4, these commands should be stubbed with a clear error: "Requires A4 (internal LLM path). Not yet implemented."

---

## 8. Out of scope

- Configuration wizard (item 13 in product audit) — separate future spec.
- `delete` commands — covered by A3 (delete operations spec).
- Async job polling — not needed for direct workflow calls.
- Shell autocompletion — not needed at this stage.
