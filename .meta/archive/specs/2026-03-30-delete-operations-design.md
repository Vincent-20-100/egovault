# A3 — Delete Operations Design

**Date:** 2026-03-30
**Status:** Approved
**Roadmap item:** A3 — Delete operations (basic CRUD completeness)

---

## 1. Problem

EgoVault has no way to delete anything. Notes, sources, chunks, and media files accumulate without any cleanup path. The audit (`docs/PRODUCT-AUDIT.md` §3, §6, §11) identifies this as a high-priority gap: "Cannot delete anything. Accumulation without cleanup is an anti-pattern."

`pending_deletion` is referenced in the audit as an intended status but is not implemented anywhere.

---

## 2. Scope

Three new tools in `tools/vault/`:
- `delete_note` — soft or hard delete a note
- `delete_source` — soft or hard delete a source
- `purge` — hard-delete all items in `pending_deletion`

Plus corresponding restore functions, DB migration, API endpoints, CLI commands, and MCP tools.

Out of scope: re-ingestion path, rechunk, provider management.

---

## 3. Core Design Decisions

### 3.1 Soft-delete vs hard-delete

Both notes and sources support a two-step deletion model:

1. **Soft-delete (default):** item is marked `pending_deletion`. No data is removed. Fully reversible via restore.
2. **Hard-delete (`force=True`):** immediate and permanent. All associated data is purged (see §3.3).
3. **Purge:** hard-deletes all items currently in `pending_deletion`.

The soft-delete window is a deliberate safety net. There is no automatic expiry — purge is always user-initiated.

### 3.2 Cascade behavior

**Deleting a source:** the linked note (if any) becomes orphaned — its `source_uid` is set to `NULL`. The note is not deleted.

**Deleting a note with `delete_source=True`:** after deleting the note, also hard-deletes the linked source (if any). The user is informed of what will be destroyed before confirmation.

**Deleting a note with `delete_source=False` (default):** source is untouched.

### 3.3 Hard-delete scope

When a source is hard-deleted, the following are permanently removed:
- The source record from `sources`
- All associated chunks from `chunks` (via `ON DELETE CASCADE`)
- All chunk embeddings from `chunks_vec`
- The media file from disk (`media_path`), if present
- The transcript (stored in the `sources` row, removed with it)

When a note is hard-deleted:
- The note record from `notes`
- All tag associations from `note_tags` (via `ON DELETE CASCADE`)
- The note embedding from `notes_vec`
- The Markdown file from the vault directory

### 3.4 Previous status tracking

To enable accurate restore, both tables store the status prior to soft-deletion:

- `sources`: new column `previous_status TEXT`
- `notes`: new column `previous_sync_status TEXT`

On soft-delete: current status is saved to `previous_*`, status set to `pending_deletion`.
On restore: `status = previous_status`, `previous_status = NULL`.

This avoids falsifying the state of a source that was deleted before reaching `finalized`.

### 3.5 MCP safety gate

Delete and purge MCP tools are registered **only if `user.yaml: allow_destructive_ops: true`**.
Default value: `false`. The check happens once at server startup. Changing the config requires restarting the MCP server. If disabled, the LLM does not see these tools at all.

---

## 4. DB Migration

New file: `scripts/temp/002_add_previous_status.py`

```sql
ALTER TABLE sources ADD COLUMN previous_status TEXT;
ALTER TABLE notes ADD COLUMN previous_sync_status TEXT;
```

Safe to run on existing DBs. Both columns default to NULL (no data loss).

**Idempotency:** SQLite raises an error if a column already exists. The migration script must catch `OperationalError` with message `"duplicate column name"` for each ALTER statement and skip silently — the column already being present is the desired end state.

---

## 5. Schemas (`core/schemas.py`)

```python
class DeleteNoteResult(BaseModel):
    uid: str
    action: Literal["soft_deleted", "hard_deleted"]
    deleted_source_uid: str | None = None  # populated if delete_source=True

class DeleteSourceResult(BaseModel):
    uid: str
    action: Literal["soft_deleted", "hard_deleted"]
    media_deleted: bool
    orphaned_note_uids: list[str]

class RestoreNoteResult(BaseModel):
    uid: str
    restored_sync_status: str

class RestoreSourceResult(BaseModel):
    uid: str
    restored_status: str

class PurgeResult(BaseModel):
    notes_purged: int
    sources_purged: int
    media_files_deleted: int
```

---

## 6. Infrastructure (`infrastructure/db.py`)

New functions:

```python
# Sources
soft_delete_source(db_path, uid) -> None
    # saves current status to previous_status, sets status = 'pending_deletion'

restore_source(db_path, uid) -> str
    # sets status = previous_status, clears previous_status, returns restored status

hard_delete_source(db_path, uid) -> None
    # DELETE FROM sources WHERE uid = ? (chunks cascade automatically)

orphan_notes_for_source(db_path, uid) -> list[str]
    # UPDATE notes SET source_uid = NULL WHERE source_uid = ?
    # returns list of affected note uids

delete_chunk_embeddings_for_source(db_path, uid) -> None
    # DELETE FROM chunks_vec WHERE chunk_uid IN
    #   (SELECT uid FROM chunks WHERE source_uid = ?)

list_sources_pending_deletion(db_path) -> list[Source]
    # SELECT * FROM sources WHERE status = 'pending_deletion'

# Notes
soft_delete_note(db_path, uid) -> None
    # saves current sync_status to previous_sync_status, sets sync_status = 'pending_deletion'

restore_note(db_path, uid) -> str
    # sets sync_status = previous_sync_status, clears previous_sync_status
    # returns restored sync_status

hard_delete_note(db_path, uid) -> None
    # DELETE FROM notes WHERE uid = ? (note_tags cascade automatically)

list_notes_pending_deletion(db_path) -> list[Note]
    # SELECT * FROM notes WHERE sync_status = 'pending_deletion'
```

Existing functions reused: `delete_note_embedding`, `delete_chunks_for_source`.

---

## 7. Tools (`tools/vault/`)

### `tools/vault/delete_note.py`

```python
def delete_note(
    uid: str,
    settings: Settings,
    delete_source: bool = False,
    force: bool = False,
) -> DeleteNoteResult
```

**Soft-delete (`force=False`):**
1. Verify note exists — raise `NotFoundError` if not
2. Verify note is not already in `pending_deletion` — raise `ConflictError` if so (maps to HTTP 409)
3. `soft_delete_note(uid)`
4. Return `DeleteNoteResult(action="soft_deleted")`

**Hard-delete (`force=True`):**
1. Verify note exists
2. `delete_note_embedding(uid)`
3. `hard_delete_note(uid)` (note_tags cascade)
4. Delete `.md` file from vault if it exists
5. Return `DeleteNoteResult(action="hard_deleted")`

**Note:** the `delete_source` cascade (when `delete_source=True`) is handled by the **routing layer** (CLI command, API router), not by the tool itself. This respects G4: a tool never imports another tool. The routing layer calls `delete_note(force=True)` first, then `delete_source(source_uid, force=True)` if requested.

### `tools/vault/delete_source.py`

```python
def delete_source(
    uid: str,
    settings: Settings,
    force: bool = False,
) -> DeleteSourceResult
```

**Soft-delete (`force=False`):**
1. Verify source exists — raise `NotFoundError` if not
2. Verify source is not already in `pending_deletion` — raise `ConflictError` if so (maps to HTTP 409)
3. `soft_delete_source(uid)`
4. Return `DeleteSourceResult(action="soft_deleted", media_deleted=False, orphaned_note_uids=[])`

**Hard-delete (`force=True`):**
1. Verify source exists
2. `orphan_notes_for_source(uid)` — collect orphaned note uids
3. `delete_chunk_embeddings_for_source(uid)`
4. `delete_chunks_for_source(uid)`
5. Delete media file from disk if `source.media_path` is set — collect `media_deleted`
6. `hard_delete_source(uid)`
7. Return `DeleteSourceResult(action="hard_deleted", media_deleted=..., orphaned_note_uids=[...])`

### `tools/vault/purge.py`

```python
def purge(settings: Settings) -> PurgeResult
```

1. `list_notes_pending_deletion()` → hard-delete each (embedding + note_tags + note + markdown file)
2. `list_sources_pending_deletion()` → hard-delete each (orphan notes + chunk embeddings + chunks + media file + source)
3. Return `PurgeResult(notes_purged=N, sources_purged=M, media_files_deleted=K)`

### Restore tools (`tools/vault/restore_note.py`, `tools/vault/restore_source.py`)

```python
def restore_note(uid: str, settings: Settings) -> RestoreNoteResult
    # Verify note exists and is in pending_deletion
    # restore_note(uid) → returns previous sync_status
    # Return RestoreNoteResult

def restore_source(uid: str, settings: Settings) -> RestoreSourceResult
    # Verify source exists and is in pending_deletion
    # restore_source(uid) → returns previous status
    # Return RestoreSourceResult
```

---

## 8. API (`api/routers/`)

### `api/routers/notes.py` — additions

```
DELETE /notes/{uid}?force=false&delete_source=false
    → 200 DeleteNoteResult
    → 404 if note not found
    → 409 if already pending_deletion and force=False

POST /notes/{uid}/restore
    → 200 RestoreNoteResult
    → 404 if not found
    → 409 if not in pending_deletion
```

### `api/routers/sources.py` — additions

```
DELETE /sources/{uid}?force=false
    → 200 DeleteSourceResult
    → 404 if source not found
    → 409 if already pending_deletion and force=False

POST /sources/{uid}/restore
    → 200 RestoreSourceResult
    → 404 if not found
    → 409 if not in pending_deletion

POST /vault/purge
    → 200 PurgeResult
```

`POST /vault/purge` goes in a new minimal `api/routers/vault.py` router (single endpoint, avoids polluting notes or sources routers with a cross-cutting operation).

All routers delegate entirely to tools — zero business logic in the routing layer (G4).

---

## 9. CLI (`cli/commands/`)

### `cli/commands/sources.py` — additions

```
egovault source delete <uid> [--force] [--yes]
egovault source restore <uid>
```

### `cli/commands/notes.py` — additions

```
egovault note delete <uid> [--force] [--delete-source] [--yes]
egovault note restore <uid>
```

### `cli/commands/purge.py` — new file

```
egovault purge [--dry-run] [--yes]
```

**`--dry-run`:** lists what would be purged (counts + uids) without deleting anything. Useful for inspection before committing.

**Confirmation behavior:** any hard-delete (force or purge) prints a summary of what will be permanently destroyed (note title, source title, media file path if applicable) and prompts `Confirm? [y/N]`. Pass `--yes` to skip for scripting.

---

## 10. MCP (`mcp/server.py`)

New config field in `user.yaml`:
```yaml
allow_destructive_ops: false  # set to true to expose delete/purge tools to the LLM
```

Corresponding field in `core/config.py` Settings model (default `False`).

At server startup, if `settings.allow_destructive_ops` is `True`, the following tools are registered with FastMCP:

```
delete_note(uid, force=False, delete_source=False)
delete_source(uid, force=False)
restore_note(uid)
restore_source(uid)
purge()
```

If `False`, these tools are not registered — the LLM does not see them. Changing the config requires restarting the MCP server.

Docstrings follow G1/G2: describe capabilities, not implementation details.

---

## 11. Tests

```
tests/tools/vault/test_delete_note.py
    - soft-delete sets sync_status=pending_deletion, saves previous_sync_status
    - hard-delete removes note, embedding, markdown file
    - hard-delete with delete_source=True also removes source
    - error on non-existent uid
    - error on already pending_deletion (soft-delete only)

tests/tools/vault/test_delete_source.py
    - soft-delete sets status=pending_deletion, saves previous_status
    - hard-delete removes source, chunks, embeddings, media file
    - hard-delete orphans linked notes (source_uid=NULL)
    - error on non-existent uid

tests/tools/vault/test_purge.py
    - purges all pending_deletion notes and sources
    - dry-run equivalent: list_*_pending_deletion returns correct items
    - empty vault returns PurgeResult(0, 0, 0)

tests/tools/vault/test_restore_note.py
    - restores previous_sync_status correctly
    - error if not in pending_deletion

tests/tools/vault/test_restore_source.py
    - restores previous_status correctly (including non-finalized states)
    - error if not in pending_deletion

tests/api/test_notes_delete.py
    - DELETE /notes/{uid} → 200 soft-delete
    - DELETE /notes/{uid}?force=true → 200 hard-delete
    - DELETE /notes/{uid} → 409 if already pending_deletion
    - POST /notes/{uid}/restore → 200

tests/api/test_sources_delete.py
    - DELETE /sources/{uid} → 200 soft-delete
    - DELETE /sources/{uid}?force=true → 200 hard-delete
    - POST /sources/{uid}/restore → 200
    - POST /vault/purge → 200 PurgeResult

tests/scripts/test_002_migration.py
    - migration adds columns without data loss
    - idempotent on re-run
```

---

## 12. Prerequisites

### 12.1 New error types needed in `core/errors.py`

`core/errors.py` currently only contains `LargeFormatError`. This spec requires:

```python
class NotFoundError(Exception):
    """Raised when a requested resource (note, source) does not exist."""

class ConflictError(Exception):
    """Raised when an operation conflicts with current state
    (e.g., item already pending_deletion, note already exists for source)."""
```

These are shared prerequisites across A2, A3, and A4. They should be created as part of whichever spec is implemented first.

---

## 13. Guardrails checklist

- [x] No library names in docstrings or error messages (G1)
- [x] Docstrings describe capabilities, not mechanisms (G2)
- [x] No hardcoded values — `allow_destructive_ops` in `user.yaml` (G3)
- [x] Architecture boundaries respected — tools call infra, API/MCP call tools (G4)
- [x] No unnecessary abstractions — 5 focused tool files (G5)
- [x] Errors use `NotFoundError` from `core/errors.py` (G6)
- [x] English in code, no vault content touched (G7)
- [x] Tests mirror source structure (G8)
- [x] All tool inputs/outputs are Pydantic models (G9)
- [x] No user content logged, parameterized queries only (G10)
- [x] MCP/API are thin routing layers (G11)
- [x] No duplicated documentation (G12)
