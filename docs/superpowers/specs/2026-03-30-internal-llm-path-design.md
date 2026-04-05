# A4 — Internal LLM Path Design

**Date:** 2026-03-30
**Status:** Approved
**Roadmap item:** A4 — Internal LLM path
**Depends on:** A1 complete (embed_note, MCP flow fix) ✓

---

## 1. Problem

All three ingest workflows stop at `rag_ready` (chunks embedded, source indexed). Moving from source to note requires an external LLM calling `create_note` via MCP. There is no automatic path.

This creates friction: ingesting 10 sources means 10 manual MCP note-creation sessions. A4 adds an optional internal generation path — after `rag_ready`, EgoVault can call the configured LLM provider itself and create a draft note automatically.

---

## 2. Scope

- New tool `tools/vault/generate_note_from_source.py`
- New `status` field on `notes` table (`draft | active`)
- `auto_generate_note` config flag in `user.yaml`, overridable per call
- DB migration `scripts/temp/003_add_note_status.py`
- `update_note` updated to allow `status` field
- Workflow changes: 3 ingest workflows accept `auto_generate_note` param
- API, CLI, MCP surfaces updated

Out of scope: `summarize.py` (text condensation stub), large-format handling, batch generation workflow.

---

## 3. Core Design Decisions

### 3.1 The LLM call

`infrastructure/llm_provider.generate_note_content(source_content, metadata, template)` is the only LLM call needed. It takes the source transcript + metadata, calls the configured provider, and returns a validated `NoteContentInput`.

`tools/text/summarize.py` is NOT part of this flow. The audit's use of "summarize" was shorthand for "generate note content via LLM." `summarize.py` remains an unimplemented stub, out of scope.

### 3.2 Draft status

Notes created via the internal path are marked `status = 'draft'` — no human was in the loop during generation. Notes created via MCP or manually are `status = 'active'` — the human approved them (MCP client shows the tool call and requests approval natively).

`status` is a new dedicated field on `notes`, separate from `sync_status`. The two fields serve different purposes:
- `sync_status`: technical embedding state (`synced`, `needs_re_embedding`, `embedding`)
- `status`: human approval state (`draft`, `active`)

### 3.3 Source lifecycle with drafts

A source stays `rag_ready` while its linked note is `draft`. The source is only finalized (`vaulted`) when the note is approved. This preserves the semantic of `vaulted` = "fully processed and validated" and keeps `rag_ready` as the actionable signal for pending work.

### 3.4 Approval cascade

Approving a draft note (`status → active`) automatically finalizes the linked source if it is still `rag_ready`. This cascade lives in the routing layer (CLI command, API router) — not in `update_note`, which stays atomic.

### 3.5 `auto_generate_note` flag

Default `false` in `user.yaml` (safe for users without a configured LLM). Overridable per call. `None` at call time means "read from config." Pattern matches existing `language` config behavior.

---

## 4. DB Migration

New file: `scripts/temp/003_add_note_status.py`

```sql
ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'active';
```

Safe on existing DBs. All existing notes default to `active` — no data loss.

**Idempotency:** catch `OperationalError: duplicate column name` and skip silently.

---

## 5. Schemas (`core/schemas.py`)

**`Note` model:** add field `status: Literal["draft", "active"] = "active"`

No new result model needed. `generate_note_from_source` returns `NoteResult` (already defined). `note.status` and `note.generation_template` carry all the additional information needed.

---

## 6. Config (`user.yaml` + `core/config.py`)

```yaml
# user.yaml
llm:
  provider: claude
  model: claude-sonnet-4-20250514
  auto_generate_note: false   # safe default — opt-in once, applies to all ingests
```

`Settings.user.llm.auto_generate_note: bool = False` added to the Pydantic config model.

---

## 7. New Tool (`tools/vault/generate_note_from_source.py`)

```python
def generate_note_from_source(
    source_uid: str,
    settings: Settings,
    template: str = "standard",
) -> NoteResult
```

**Flow:**
1. `get_source(source_uid)` — raise `NotFoundError` if absent
2. Verify `source.status == "rag_ready"` — raise `ValueError` if not
3. `get_note_by_source(source_uid)` — raise `ConflictError` if note already exists
4. Build `metadata` dict from source fields (title, url, author, date_source, source_type)
5. `generate_note_content(source.transcript, metadata, template)` → `NoteContentInput`
6. Build `NoteSystemFields(uid, slug, source_uid, date_created, generation_template=template)`
7. `create_note(content, system_fields, settings)` → writes DB + markdown + embedding
8. Set `status = 'draft'` on the note via `update_note`
9. Return `NoteResult`

The note is immediately searchable (embedding written in step 7) and marked draft.

---

## 8. Infrastructure (`infrastructure/db.py`)

**`update_note`:** add `"status"` to the `allowed` set. This makes `note update --status active` valid from CLI and `PATCH /notes/{uid}` from API.

No other DB function changes needed. `get_note_by_source` already exists (line 293).

---

## 9. Workflow Changes

All three ingest workflows receive a new optional parameter:

```python
def ingest_youtube(url: str, settings: Settings, auto_generate_note: bool | None = None) -> Source
def ingest_audio(path: str, settings: Settings, auto_generate_note: bool | None = None) -> Source
def ingest_pdf(path: str, settings: Settings, auto_generate_note: bool | None = None) -> Source
```

**Resolution logic** (same in all three):
```python
should_generate = auto_generate_note if auto_generate_note is not None \
                  else settings.user.llm.auto_generate_note
```

**After `rag_ready`**, if `should_generate` is `True`:
- If LLM not configured (provider not set or no API key) → `logger.info("LLM not configured, skipping note generation")` — return source
- If `LargeFormatError` already raised → `logger.info("Source exceeds token threshold, skipping note generation")` — re-raise `LargeFormatError` as before
- Otherwise → `generate_note_from_source(source_uid, settings)` → note created in `draft`

If `should_generate` is `False` → behavior unchanged, source stays `rag_ready`.

---

## 10. Approval Flow

Approving a draft note is not a new tool — it uses `update_note(status='active')` followed by `finalize_source`. The cascade is handled in the routing layer:

**CLI (`cli/commands/notes.py`):**
```bash
egovault note approve <uid>
```
Calls `update_note(uid, {"status": "active"})` then, if `note.source_uid` is set and source is `rag_ready`, calls `finalize_source(source_uid, settings)`.

**API (`api/routers/notes.py`):**
```
POST /notes/{uid}/approve
```
Same two-step cascade. Returns updated `NoteDetail`.

**MCP:** no new tool. Workflow guide updated: "After reviewing a draft note, call `update_note` with `status: active`, then call `finalize_source` on the linked source."

---

## 11. API Changes (`api/routers/`)

**`api/routers/notes.py`:**
```
POST  /notes/{uid}/approve
      → 200 NoteDetail
      → 404 if note not found
      → 409 if note not in draft status
```
`NotePatch` model updated to accept `status: Literal["draft", "active"] | None`.

**`api/routers/sources.py`:**
```
POST  /sources/{uid}/generate-note?template=standard
      → 200 NoteResult
      → 404 if source not found
      → 409 if note already exists for source
      → 422 if source not rag_ready
```

**`api/routers/ingest.py`:**
`auto_generate_note: bool | None` added to ingest request bodies.

---

## 12. CLI Changes

The following commands are added/updated. They require updates to the A2 CLI spec (`2026-03-30-cli-design.md`) during implementation:

**`cli/commands/notes.py`:**
```bash
egovault note approve <uid>                                    [--json]
egovault note list  [--limit 20] [--offset 0] [--status draft|active] [--json]
egovault note update <uid> [...] [--status draft|active]      [--json]
```
`note approve` = `update_note(status='active')` + conditional `finalize_source`.
`note update --status active` is now valid (field exists after migration).

**`cli/commands/sources.py`:**
```bash
egovault source generate-note <uid> [--template standard]     [--json]
```

**`cli/commands/ingest.py`:**
```bash
egovault ingest <url_or_file> [--generate-note] [--no-generate-note] [--json] [--verbose]
```
`--generate-note` forces `auto_generate_note=True`. `--no-generate-note` forces `False`. Neither flag = reads `user.yaml` default.

---

## 13. MCP Changes (`mcp/server.py`)

New tool exposed:
```
generate_note_from_source(source_uid, template='standard')
```
Docstring describes capability, not implementation (G1/G2): "Generate a draft note from an ingested source. The source must be at rag_ready status. Returns a note marked draft — call approve after reviewing."

Workflow guide (`get_workflow_guide`) updated with the internal path flow and draft approval step.

---

## 14. Tests

```
tests/tools/vault/test_generate_note_from_source.py
    - generates draft note from rag_ready source
    - NotFoundError if source does not exist
    - ValueError if source not rag_ready
    - ConflictError if note already exists for source
    - NoteResult.note.status == 'draft'
    - NoteResult.note.generation_template == template

tests/workflows/test_ingest_youtube.py (+ audio, pdf)
    - auto_generate_note=True → draft note created after rag_ready
    - auto_generate_note=False → stops at rag_ready, no note
    - auto_generate_note=None, config=True → draft note created
    - auto_generate_note=None, config=False → stops at rag_ready
    - LLM not configured → logger.info logged, stops at rag_ready
    - source exceeds threshold → logger.info logged, LargeFormatError raised

tests/api/test_notes_approve.py
    - POST /notes/{uid}/approve → status='active', source finalized
    - 409 if note not in draft

tests/api/test_sources_generate_note.py
    - POST /sources/{uid}/generate-note → 200 NoteResult
    - 409 if note already exists
    - 422 if source not rag_ready

tests/scripts/test_003_migration.py
    - status column added with default 'active'
    - existing notes unaffected
    - idempotent on re-run
```

---

## 15. A2 CLI Spec — Required Updates

The following items must be added to `docs/superpowers/specs/2026-03-30-cli-design.md` during A4 implementation:

1. `egovault note approve <uid>` command
2. `egovault source generate-note <uid> [--template standard]` command
3. `--generate-note` / `--no-generate-note` flags on `egovault ingest`
4. `--status draft|active` filter on `egovault note list`
5. Note that `note update --status active` is valid once A4 migration runs

---

## 16. Prerequisites

### New error types needed in `core/errors.py`

`core/errors.py` currently only contains `LargeFormatError`. This spec requires `NotFoundError` and `ConflictError`. See A2 CLI spec §7.1 or A3 Delete spec §12.1 for definitions — shared prerequisite across A2, A3, and A4.

---

## 17. Guardrails Checklist

- [x] No library/provider names in docstrings or error messages (G1)
- [x] Docstrings describe capabilities, not implementation (G2)
- [x] `auto_generate_note` in `user.yaml`, template defaults to config-driven value (G3)
- [x] `update_note` stays atomic — cascade in routing layer only (G4)
- [x] No new result model — `NoteResult` reused (G5)
- [x] `logger.info` on skip cases, `NotFoundError`/`ConflictError` from `core/errors.py` (G6)
- [x] English in code, no vault content hardcoded (G7)
- [x] Tests mirror source structure (G8)
- [x] All tool inputs/outputs are Pydantic models (G9)
- [x] No user content logged, parameterized queries (G10)
- [x] MCP/API are thin routing layers (G11)
- [x] No duplicated documentation (G12)
