# A3 — Delete Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full delete/restore/purge lifecycle for notes and sources — soft-delete via `pending_deletion`, hard-delete with full cascade, and a `purge` command to clean all pending items.

**Architecture:** Five new atomic tools in `tools/vault/` (`delete_note`, `delete_source`, `restore_note`, `restore_source`, `purge`). All cascade logic (note + source together, `--delete-source` flag) lives in the routing layer (CLI/API), never in the tools. DB migration adds `previous_status` / `previous_sync_status` columns. MCP tools gated by `allow_destructive_ops: false` config flag registered at startup.

**Tech Stack:** `tools/vault/`, `infrastructure/db.py`, `core/schemas.py`, `core/errors.py`, `core/config.py`, `api/routers/`, `cli/commands/`, `mcp/server.py`, SQLite, `pytest`, `typer`, `fastapi`.

**Prerequisite:** `NotFoundError` and `ConflictError` must exist in `core/errors.py`. These are added in the A2 CLI completion plan (Task 1). If A2 has not run yet, add them before starting this plan.

---

## File Map

**Create:**
- `scripts/temp/002_add_previous_status.py`
- `tools/vault/delete_note.py`
- `tools/vault/delete_source.py`
- `tools/vault/restore_note.py`
- `tools/vault/restore_source.py`
- `tools/vault/purge.py`
- `api/routers/vault.py`
- `cli/commands/purge.py`
- `tests/tools/vault/test_delete_note.py`
- `tests/tools/vault/test_delete_source.py`
- `tests/tools/vault/test_restore_note.py`
- `tests/tools/vault/test_restore_source.py`
- `tests/tools/vault/test_purge.py`
- `tests/api/test_notes_delete.py`
- `tests/api/test_sources_delete.py`
- `tests/scripts/test_002_migration.py`

**Modify:**
- `core/schemas.py` — 5 new result models
- `core/config.py` — `allow_destructive_ops` in `UserConfig`
- `infrastructure/db.py` — 10 new functions
- `api/routers/notes.py` — DELETE + restore endpoints
- `api/routers/sources.py` — DELETE + restore endpoints
- `api/main.py` — register vault router
- `cli/commands/notes.py` — delete + restore commands
- `cli/commands/sources.py` — delete + restore commands
- `cli/main.py` — register purge command
- `mcp/server.py` — conditional delete/purge tools
- `config/user.yaml` — add `allow_destructive_ops: false`
- `tests/conftest.py` — add `allow_destructive_ops` to fixture

---

## Task 1: DB Migration

**Files:**
- Create: `scripts/temp/002_add_previous_status.py`
- Create: `tests/scripts/test_002_migration.py`

- [ ] **Step 1: Write the migration script**

Create `scripts/temp/002_add_previous_status.py`:

```python
"""
Migration 002 — add previous_status columns for soft-delete tracking.

Adds:
  sources.previous_status      TEXT  (NULL default)
  notes.previous_sync_status   TEXT  (NULL default)

Idempotent: silently skips if column already exists.
"""

import sqlite3
from pathlib import Path
from core.config import load_settings


def run(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    for sql in [
        "ALTER TABLE sources ADD COLUMN previous_status TEXT",
        "ALTER TABLE notes ADD COLUMN previous_sync_status TEXT",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                raise
    conn.commit()
    conn.close()
    print(f"Migration 002 applied to {db_path}")


if __name__ == "__main__":
    settings = load_settings()
    run(settings.vault_db_path)
    print("Done.")
```

- [ ] **Step 2: Write migration tests**

Create `tests/scripts/test_002_migration.py`:

```python
import sqlite3
import pytest
from pathlib import Path
from infrastructure.db import init_db


def _get_columns(db_path: Path, table: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    conn.close()
    return [row[1] for row in rows]


def test_migration_adds_previous_status(tmp_path):
    db = tmp_path / "vault.db"
    init_db(db)
    from scripts.temp._002_add_previous_status import run
    run(db)
    assert "previous_status" in _get_columns(db, "sources")
    assert "previous_sync_status" in _get_columns(db, "notes")


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "vault.db"
    init_db(db)
    from scripts.temp._002_add_previous_status import run
    run(db)
    run(db)  # second call must not raise
    assert "previous_status" in _get_columns(db, "sources")
```

Note: rename `002_add_previous_status.py` to `_002_add_previous_status.py` (underscore prefix) so Python can import it in tests without the leading digit. Update the `__main__` block filename comment accordingly.

- [ ] **Step 3: Run migration tests**

```bash
.venv/Scripts/python -m pytest tests/scripts/test_002_migration.py -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/temp/_002_add_previous_status.py tests/scripts/test_002_migration.py
git commit -m "feat: migration 002 — add previous_status columns for soft-delete"
```

---

## Task 2: Schemas and Config

**Files:**
- Modify: `core/schemas.py`
- Modify: `core/config.py`
- Modify: `config/user.yaml`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add 5 new result models to `core/schemas.py`**

Add after `EmbedNoteResult`:

```python
class DeleteNoteResult(BaseModel):
    uid: str
    action: Literal["soft_deleted", "hard_deleted"]
    deleted_source_uid: str | None = None  # set by routing layer when --delete-source is used


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

- [ ] **Step 2: Add `allow_destructive_ops` to `UserConfig` in `core/config.py`**

In `UserConfig`:

```python
class UserConfig(BaseModel):
    embedding: EmbeddingUserConfig
    llm: LLMUserConfig
    vault: VaultUserConfig
    allow_destructive_ops: bool = False  # expose delete/purge tools to the LLM via MCP
```

- [ ] **Step 3: Add `allow_destructive_ops` to `config/user.yaml`**

Add at the end of `config/user.yaml`:

```yaml
# MCP safety gate — set to true to expose delete/purge tools to the LLM
allow_destructive_ops: false
```

- [ ] **Step 4: Update `tests/conftest.py` fixture**

In the `tmp_settings` fixture, in the `user.yaml` content dict, add:

```python
"allow_destructive_ops": False,
```

- [ ] **Step 5: Verify imports**

```bash
.venv/Scripts/python -c "from core.schemas import DeleteNoteResult, DeleteSourceResult, RestoreNoteResult, RestoreSourceResult, PurgeResult; print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add core/schemas.py core/config.py config/user.yaml tests/conftest.py
git commit -m "feat: add delete/restore/purge schemas and allow_destructive_ops config"
```

---

## Task 3: DB Functions

**Files:**
- Modify: `infrastructure/db.py`

- [ ] **Step 1: Add source soft-delete, restore, hard-delete functions**

Add to `infrastructure/db.py` after the existing `list_sources` function:

```python
def soft_delete_source(db_path: Path, uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        "UPDATE sources SET previous_status = status, status = 'pending_deletion' WHERE uid = ?",
        (uid,),
    )
    conn.commit()
    conn.close()


def restore_source(db_path: Path, uid: str) -> str:
    conn = get_vault_connection(db_path)
    row = conn.execute(
        "SELECT previous_status FROM sources WHERE uid = ?", (uid,)
    ).fetchone()
    previous = row[0] if row else None
    conn.execute(
        "UPDATE sources SET status = previous_status, previous_status = NULL WHERE uid = ?",
        (uid,),
    )
    conn.commit()
    conn.close()
    return previous or "rag_ready"


def hard_delete_source(db_path: Path, uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute("DELETE FROM sources WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()


def orphan_notes_for_source(db_path: Path, uid: str) -> list[str]:
    conn = get_vault_connection(db_path)
    rows = conn.execute(
        "SELECT uid FROM notes WHERE source_uid = ?", (uid,)
    ).fetchall()
    note_uids = [row[0] for row in rows]
    conn.execute("UPDATE notes SET source_uid = NULL WHERE source_uid = ?", (uid,))
    conn.commit()
    conn.close()
    return note_uids


def delete_chunk_embeddings_for_source(db_path: Path, uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        "DELETE FROM chunks_vec WHERE chunk_uid IN "
        "(SELECT uid FROM chunks WHERE source_uid = ?)",
        (uid,),
    )
    conn.commit()
    conn.close()


def list_sources_pending_deletion(db_path: Path) -> list[Source]:
    conn = get_vault_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM sources WHERE status = 'pending_deletion'"
    ).fetchall()
    conn.close()
    return [Source(**dict(row)) for row in rows]
```

- [ ] **Step 2: Add note soft-delete, restore, hard-delete functions**

Add after the functions from Step 1:

```python
def soft_delete_note(db_path: Path, uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        "UPDATE notes SET previous_sync_status = sync_status, sync_status = 'pending_deletion' WHERE uid = ?",
        (uid,),
    )
    conn.commit()
    conn.close()


def restore_note(db_path: Path, uid: str) -> str:
    conn = get_vault_connection(db_path)
    row = conn.execute(
        "SELECT previous_sync_status FROM notes WHERE uid = ?", (uid,)
    ).fetchone()
    previous = row[0] if row else None
    conn.execute(
        "UPDATE notes SET sync_status = previous_sync_status, previous_sync_status = NULL WHERE uid = ?",
        (uid,),
    )
    conn.commit()
    conn.close()
    return previous or "synced"


def hard_delete_note(db_path: Path, uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute("DELETE FROM notes WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()


def list_notes_pending_deletion(db_path: Path) -> list[Note]:
    conn = get_vault_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM notes WHERE sync_status = 'pending_deletion'"
    ).fetchall()
    results = []
    for row in rows:
        data = dict(row)
        tags = _fetch_note_tags(conn, data["uid"])
        data["tags"] = tags if tags else ["untagged"]
        results.append(Note(**data))
    conn.close()
    return results
```

- [ ] **Step 3: Quick import check**

```bash
.venv/Scripts/python -c "
from infrastructure.db import (
    soft_delete_source, restore_source, hard_delete_source,
    orphan_notes_for_source, delete_chunk_embeddings_for_source,
    list_sources_pending_deletion, soft_delete_note, restore_note,
    hard_delete_note, list_notes_pending_deletion
)
print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add infrastructure/db.py
git commit -m "feat: add soft-delete, restore, hard-delete DB functions for notes and sources"
```

---

## Task 4: `delete_note` and `delete_source` Tools

**Files:**
- Create: `tools/vault/delete_note.py`
- Create: `tools/vault/delete_source.py`
- Create: `tests/tools/vault/test_delete_note.py`
- Create: `tests/tools/vault/test_delete_source.py`

- [ ] **Step 1: Write failing tests for `delete_note`**

Create `tests/tools/vault/test_delete_note.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.errors import NotFoundError, ConflictError
from core.schemas import DeleteNoteResult


def _make_note(uid="nuid-1", sync_status="synced"):
    from core.schemas import Note
    return Note(
        uid=uid, slug="test-note", title="Test", docstring="Doc",
        body="Body content here.", tags=["test"], note_type=None,
        source_type=None, date_created="2026-03-30", date_modified="2026-03-30",
        sync_status=sync_status, source_uid=None,
    )


def test_delete_note_soft_delete(tmp_settings):
    """Soft-delete sets sync_status to pending_deletion."""
    note = _make_note()
    with patch("tools.vault.delete_note.get_note", return_value=note), \
         patch("tools.vault.delete_note.soft_delete_note") as mock_soft:
        from tools.vault.delete_note import delete_note
        result = delete_note("nuid-1", tmp_settings)
    assert result.action == "soft_deleted"
    assert result.uid == "nuid-1"
    mock_soft.assert_called_once()


def test_delete_note_hard_delete(tmp_settings, tmp_path):
    """Hard-delete removes embedding, note, and markdown file."""
    note = _make_note()
    md_file = tmp_path / "test-note.md"
    md_file.write_text("content")

    with patch("tools.vault.delete_note.get_note", return_value=note), \
         patch("tools.vault.delete_note.delete_note_embedding") as mock_emb, \
         patch("tools.vault.delete_note.hard_delete_note") as mock_hard, \
         patch.object(type(tmp_settings), "vault_path",
                      new_callable=lambda: property(lambda self: tmp_path)):
        from tools.vault.delete_note import delete_note
        result = delete_note("nuid-1", tmp_settings, force=True)
    assert result.action == "hard_deleted"
    mock_emb.assert_called_once_with(tmp_settings.vault_db_path, "nuid-1")
    mock_hard.assert_called_once_with(tmp_settings.vault_db_path, "nuid-1")
    assert not md_file.exists()


def test_delete_note_not_found(tmp_settings):
    """Raises NotFoundError when note does not exist."""
    with patch("tools.vault.delete_note.get_note", return_value=None):
        from tools.vault.delete_note import delete_note
        with pytest.raises(NotFoundError):
            delete_note("nonexistent", tmp_settings)


def test_delete_note_already_pending(tmp_settings):
    """Raises ConflictError on soft-delete if already pending_deletion."""
    note = _make_note(sync_status="pending_deletion")
    with patch("tools.vault.delete_note.get_note", return_value=note):
        from tools.vault.delete_note import delete_note
        with pytest.raises(ConflictError):
            delete_note("nuid-1", tmp_settings, force=False)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_delete_note.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `tools/vault/delete_note.py`**

Create `tools/vault/delete_note.py`:

```python
"""
Note deletion tool.

Input  : note uid + force flag
Output : DeleteNoteResult
Soft-delete: marks note as pending_deletion (reversible via restore_note).
Hard-delete: permanently removes note, embedding, and Markdown file.
The --delete-source cascade is handled by the routing layer, not this tool.
"""

from core.schemas import DeleteNoteResult
from core.config import Settings
from core.logging import loggable


@loggable("delete_note")
def delete_note(
    uid: str,
    settings: Settings,
    force: bool = False,
) -> DeleteNoteResult:
    """
    Remove a note from the vault.
    Soft-delete (default): marks as pending_deletion, reversible via restore.
    Hard-delete (force=True): permanently removes note, embedding, and Markdown file.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import (
        get_note, soft_delete_note, hard_delete_note, delete_note_embedding,
    )

    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise NotFoundError("Note", uid)

    if not force:
        if note.sync_status == "pending_deletion":
            raise ConflictError("Note", uid, "already marked for deletion")
        soft_delete_note(settings.vault_db_path, uid)
        return DeleteNoteResult(uid=uid, action="soft_deleted")

    delete_note_embedding(settings.vault_db_path, uid)
    hard_delete_note(settings.vault_db_path, uid)

    md_file = settings.vault_path / f"{note.slug}.md"
    if md_file.exists():
        md_file.unlink()

    return DeleteNoteResult(uid=uid, action="hard_deleted")
```

- [ ] **Step 4: Run `delete_note` tests**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_delete_note.py -v
```
Expected: all PASS

- [ ] **Step 5: Write failing tests for `delete_source`**

Create `tests/tools/vault/test_delete_source.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.errors import NotFoundError, ConflictError
from core.schemas import DeleteSourceResult


def _make_source(uid="suid-1", status="rag_ready", media_path=None):
    from core.schemas import Source
    return Source(
        uid=uid, slug="test-source", source_type="youtube",
        status=status, date_added="2026-03-30", media_path=media_path,
    )


def test_delete_source_soft_delete(tmp_settings):
    source = _make_source()
    with patch("tools.vault.delete_source.get_source", return_value=source), \
         patch("tools.vault.delete_source.soft_delete_source") as mock_soft:
        from tools.vault.delete_source import delete_source
        result = delete_source("suid-1", tmp_settings)
    assert result.action == "soft_deleted"
    assert result.media_deleted is False
    assert result.orphaned_note_uids == []
    mock_soft.assert_called_once()


def test_delete_source_hard_delete_no_media(tmp_settings):
    source = _make_source()
    with patch("tools.vault.delete_source.get_source", return_value=source), \
         patch("tools.vault.delete_source.orphan_notes_for_source", return_value=["nuid-1"]) as mock_orphan, \
         patch("tools.vault.delete_source.delete_chunk_embeddings_for_source") as mock_emb, \
         patch("tools.vault.delete_source.delete_chunks_for_source") as mock_chunks, \
         patch("tools.vault.delete_source.hard_delete_source") as mock_hard:
        from tools.vault.delete_source import delete_source
        result = delete_source("suid-1", tmp_settings, force=True)
    assert result.action == "hard_deleted"
    assert result.media_deleted is False
    assert result.orphaned_note_uids == ["nuid-1"]
    mock_orphan.assert_called_once()
    mock_emb.assert_called_once()
    mock_chunks.assert_called_once()
    mock_hard.assert_called_once()


def test_delete_source_hard_delete_with_media(tmp_settings, tmp_path):
    media_file = tmp_path / "video.mp4"
    media_file.write_bytes(b"fake")
    source = _make_source(media_path=str(media_file))
    with patch("tools.vault.delete_source.get_source", return_value=source), \
         patch("tools.vault.delete_source.orphan_notes_for_source", return_value=[]), \
         patch("tools.vault.delete_source.delete_chunk_embeddings_for_source"), \
         patch("tools.vault.delete_source.delete_chunks_for_source"), \
         patch("tools.vault.delete_source.hard_delete_source"):
        from tools.vault.delete_source import delete_source
        result = delete_source("suid-1", tmp_settings, force=True)
    assert result.media_deleted is True
    assert not media_file.exists()


def test_delete_source_not_found(tmp_settings):
    with patch("tools.vault.delete_source.get_source", return_value=None):
        from tools.vault.delete_source import delete_source
        with pytest.raises(NotFoundError):
            delete_source("nonexistent", tmp_settings)


def test_delete_source_already_pending(tmp_settings):
    source = _make_source(status="pending_deletion")
    with patch("tools.vault.delete_source.get_source", return_value=source):
        from tools.vault.delete_source import delete_source
        with pytest.raises(ConflictError):
            delete_source("suid-1", tmp_settings, force=False)
```

- [ ] **Step 6: Implement `tools/vault/delete_source.py`**

Create `tools/vault/delete_source.py`:

```python
"""
Source deletion tool.

Input  : source uid + force flag
Output : DeleteSourceResult
Soft-delete: marks source as pending_deletion (reversible via restore_source).
Hard-delete: permanently removes source, chunks, embeddings, and media file.
Linked notes become orphaned (source_uid set to NULL) — they are NOT deleted.
"""

from pathlib import Path

from core.schemas import DeleteSourceResult
from core.config import Settings
from core.logging import loggable


@loggable("delete_source")
def delete_source(
    uid: str,
    settings: Settings,
    force: bool = False,
) -> DeleteSourceResult:
    """
    Remove a source from the vault.
    Soft-delete (default): marks as pending_deletion, reversible via restore.
    Hard-delete (force=True): permanently removes source, all chunks, embeddings, and media file.
    Linked notes become orphaned — their source_uid is set to NULL.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import (
        get_source, soft_delete_source, hard_delete_source,
        orphan_notes_for_source, delete_chunk_embeddings_for_source,
        delete_chunks_for_source,
    )

    source = get_source(settings.vault_db_path, uid)
    if source is None:
        raise NotFoundError("Source", uid)

    if not force:
        if source.status == "pending_deletion":
            raise ConflictError("Source", uid, "already marked for deletion")
        soft_delete_source(settings.vault_db_path, uid)
        return DeleteSourceResult(
            uid=uid, action="soft_deleted", media_deleted=False, orphaned_note_uids=[]
        )

    orphaned = orphan_notes_for_source(settings.vault_db_path, uid)
    delete_chunk_embeddings_for_source(settings.vault_db_path, uid)
    delete_chunks_for_source(settings.vault_db_path, uid)

    media_deleted = False
    if source.media_path:
        media_file = Path(source.media_path)
        if media_file.exists():
            media_file.unlink()
            media_deleted = True

    hard_delete_source(settings.vault_db_path, uid)

    return DeleteSourceResult(
        uid=uid, action="hard_deleted",
        media_deleted=media_deleted,
        orphaned_note_uids=orphaned,
    )
```

- [ ] **Step 7: Run all delete tool tests**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_delete_note.py tests/tools/vault/test_delete_source.py -v
```
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add tools/vault/delete_note.py tools/vault/delete_source.py \
        tests/tools/vault/test_delete_note.py tests/tools/vault/test_delete_source.py
git commit -m "feat: add delete_note and delete_source tools"
```

---

## Task 5: `restore_note`, `restore_source`, and `purge` Tools

**Files:**
- Create: `tools/vault/restore_note.py`
- Create: `tools/vault/restore_source.py`
- Create: `tools/vault/purge.py`
- Create: `tests/tools/vault/test_restore_note.py`
- Create: `tests/tools/vault/test_restore_source.py`
- Create: `tests/tools/vault/test_purge.py`

- [ ] **Step 1: Write tests for restore tools**

Create `tests/tools/vault/test_restore_note.py`:

```python
import pytest
from unittest.mock import patch
from core.errors import NotFoundError, ConflictError
from core.schemas import RestoreNoteResult


def _make_note(sync_status="pending_deletion"):
    from core.schemas import Note
    return Note(
        uid="nuid-1", slug="test", title="Test", docstring="Doc",
        body="Body.", tags=["test"], note_type=None, source_type=None,
        date_created="2026-03-30", date_modified="2026-03-30",
        sync_status=sync_status, source_uid=None,
    )


def test_restore_note_success(tmp_settings):
    note = _make_note(sync_status="pending_deletion")
    with patch("tools.vault.restore_note.get_note", return_value=note), \
         patch("tools.vault.restore_note.restore_note_db", return_value="synced") as mock_restore:
        from tools.vault.restore_note import restore_note
        result = restore_note("nuid-1", tmp_settings)
    assert result.uid == "nuid-1"
    assert result.restored_sync_status == "synced"
    mock_restore.assert_called_once()


def test_restore_note_not_found(tmp_settings):
    with patch("tools.vault.restore_note.get_note", return_value=None):
        from tools.vault.restore_note import restore_note
        with pytest.raises(NotFoundError):
            restore_note("nonexistent", tmp_settings)


def test_restore_note_not_pending(tmp_settings):
    note = _make_note(sync_status="synced")
    with patch("tools.vault.restore_note.get_note", return_value=note):
        from tools.vault.restore_note import restore_note
        with pytest.raises(ConflictError):
            restore_note("nuid-1", tmp_settings)
```

Create `tests/tools/vault/test_restore_source.py`:

```python
import pytest
from unittest.mock import patch
from core.errors import NotFoundError, ConflictError
from core.schemas import RestoreSourceResult


def _make_source(status="pending_deletion"):
    from core.schemas import Source
    return Source(
        uid="suid-1", slug="test-source", source_type="youtube",
        status=status, date_added="2026-03-30",
    )


def test_restore_source_success(tmp_settings):
    source = _make_source()
    with patch("tools.vault.restore_source.get_source", return_value=source), \
         patch("tools.vault.restore_source.restore_source_db", return_value="rag_ready") as mock_restore:
        from tools.vault.restore_source import restore_source
        result = restore_source("suid-1", tmp_settings)
    assert result.uid == "suid-1"
    assert result.restored_status == "rag_ready"


def test_restore_source_not_found(tmp_settings):
    with patch("tools.vault.restore_source.get_source", return_value=None):
        from tools.vault.restore_source import restore_source
        with pytest.raises(NotFoundError):
            restore_source("nonexistent", tmp_settings)


def test_restore_source_not_pending(tmp_settings):
    source = _make_source(status="rag_ready")
    with patch("tools.vault.restore_source.get_source", return_value=source):
        from tools.vault.restore_source import restore_source
        with pytest.raises(ConflictError):
            restore_source("suid-1", tmp_settings)
```

Create `tests/tools/vault/test_purge.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from core.schemas import PurgeResult


def test_purge_empty_vault(tmp_settings):
    with patch("tools.vault.purge.list_notes_pending_deletion", return_value=[]), \
         patch("tools.vault.purge.list_sources_pending_deletion", return_value=[]):
        from tools.vault.purge import purge
        result = purge(tmp_settings)
    assert result.notes_purged == 0
    assert result.sources_purged == 0
    assert result.media_files_deleted == 0


def test_purge_deletes_pending_notes(tmp_settings):
    from core.schemas import Note
    note = Note(
        uid="nuid-1", slug="test", title="Test", docstring="Doc",
        body="Body.", tags=["t"], note_type=None, source_type=None,
        date_created="2026-03-30", date_modified="2026-03-30",
        sync_status="pending_deletion", source_uid=None,
    )
    with patch("tools.vault.purge.list_notes_pending_deletion", return_value=[note]), \
         patch("tools.vault.purge.list_sources_pending_deletion", return_value=[]), \
         patch("tools.vault.purge.delete_note_embedding"), \
         patch("tools.vault.purge.hard_delete_note"), \
         patch.object(type(tmp_settings), "vault_path",
                      new_callable=lambda: property(lambda self: MagicMock())):
        from tools.vault.purge import purge
        result = purge(tmp_settings)
    assert result.notes_purged == 1


def test_purge_deletes_pending_sources(tmp_settings):
    from core.schemas import Source
    source = Source(
        uid="suid-1", slug="test-source", source_type="youtube",
        status="pending_deletion", date_added="2026-03-30",
    )
    with patch("tools.vault.purge.list_notes_pending_deletion", return_value=[]), \
         patch("tools.vault.purge.list_sources_pending_deletion", return_value=[source]), \
         patch("tools.vault.purge.orphan_notes_for_source", return_value=[]), \
         patch("tools.vault.purge.delete_chunk_embeddings_for_source"), \
         patch("tools.vault.purge.delete_chunks_for_source"), \
         patch("tools.vault.purge.hard_delete_source"):
        from tools.vault.purge import purge
        result = purge(tmp_settings)
    assert result.sources_purged == 1
    assert result.media_files_deleted == 0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_restore_note.py tests/tools/vault/test_restore_source.py tests/tools/vault/test_purge.py -v
```
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement `tools/vault/restore_note.py`**

```python
"""
Note restore tool.

Input  : note uid
Output : RestoreNoteResult
Restores a note from pending_deletion to its previous sync_status.
"""

from core.schemas import RestoreNoteResult
from core.config import Settings
from core.logging import loggable


@loggable("restore_note")
def restore_note(uid: str, settings: Settings) -> RestoreNoteResult:
    """
    Restore a note previously marked for deletion.
    Reverts the note to its sync status prior to the soft-delete.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import get_note, restore_note as restore_note_db

    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise NotFoundError("Note", uid)
    if note.sync_status != "pending_deletion":
        raise ConflictError("Note", uid, "not marked for deletion")

    restored_status = restore_note_db(settings.vault_db_path, uid)
    return RestoreNoteResult(uid=uid, restored_sync_status=restored_status)
```

- [ ] **Step 4: Implement `tools/vault/restore_source.py`**

```python
"""
Source restore tool.

Input  : source uid
Output : RestoreSourceResult
Restores a source from pending_deletion to its previous status.
"""

from core.schemas import RestoreSourceResult
from core.config import Settings
from core.logging import loggable


@loggable("restore_source")
def restore_source(uid: str, settings: Settings) -> RestoreSourceResult:
    """
    Restore a source previously marked for deletion.
    Reverts the source to its status prior to the soft-delete.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import get_source, restore_source as restore_source_db

    source = get_source(settings.vault_db_path, uid)
    if source is None:
        raise NotFoundError("Source", uid)
    if source.status != "pending_deletion":
        raise ConflictError("Source", uid, "not marked for deletion")

    restored_status = restore_source_db(settings.vault_db_path, uid)
    return RestoreSourceResult(uid=uid, restored_status=restored_status)
```

- [ ] **Step 5: Implement `tools/vault/purge.py`**

```python
"""
Vault purge tool.

Input  : settings
Output : PurgeResult
Hard-deletes all notes and sources currently in pending_deletion.
"""

from pathlib import Path

from core.schemas import PurgeResult
from core.config import Settings
from core.logging import loggable


@loggable("purge")
def purge(settings: Settings) -> PurgeResult:
    """
    Permanently remove all items marked for deletion from the vault.
    Purges all pending notes (embeddings, files) and sources (chunks, embeddings, media).
    """
    from infrastructure.db import (
        list_notes_pending_deletion, list_sources_pending_deletion,
        delete_note_embedding, hard_delete_note,
        orphan_notes_for_source, delete_chunk_embeddings_for_source,
        delete_chunks_for_source, hard_delete_source,
    )

    notes_purged = 0
    for note in list_notes_pending_deletion(settings.vault_db_path):
        delete_note_embedding(settings.vault_db_path, note.uid)
        hard_delete_note(settings.vault_db_path, note.uid)
        md_file = settings.vault_path / f"{note.slug}.md"
        if md_file.exists():
            md_file.unlink()
        notes_purged += 1

    sources_purged = 0
    media_files_deleted = 0
    for source in list_sources_pending_deletion(settings.vault_db_path):
        orphan_notes_for_source(settings.vault_db_path, source.uid)
        delete_chunk_embeddings_for_source(settings.vault_db_path, source.uid)
        delete_chunks_for_source(settings.vault_db_path, source.uid)
        if source.media_path:
            media_file = Path(source.media_path)
            if media_file.exists():
                media_file.unlink()
                media_files_deleted += 1
        hard_delete_source(settings.vault_db_path, source.uid)
        sources_purged += 1

    return PurgeResult(
        notes_purged=notes_purged,
        sources_purged=sources_purged,
        media_files_deleted=media_files_deleted,
    )
```

- [ ] **Step 6: Run all restore and purge tests**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_restore_note.py tests/tools/vault/test_restore_source.py tests/tools/vault/test_purge.py -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add tools/vault/restore_note.py tools/vault/restore_source.py tools/vault/purge.py \
        tests/tools/vault/test_restore_note.py tests/tools/vault/test_restore_source.py \
        tests/tools/vault/test_purge.py
git commit -m "feat: add restore_note, restore_source, and purge tools"
```

---

## Task 6: API Endpoints

**Files:**
- Modify: `api/routers/notes.py`
- Modify: `api/routers/sources.py`
- Create: `api/routers/vault.py`
- Modify: `api/main.py`
- Create: `tests/api/test_notes_delete.py`
- Create: `tests/api/test_sources_delete.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/api/test_notes_delete.py`:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from core.schemas import DeleteNoteResult, RestoreNoteResult
from core.errors import NotFoundError, ConflictError


@pytest.fixture
def client(tmp_settings):
    from api.main import create_app
    app = create_app(tmp_settings)
    return TestClient(app)


def test_delete_note_soft(client):
    result = DeleteNoteResult(uid="nuid-1", action="soft_deleted")
    with patch("api.routers.notes.delete_note", return_value=result):
        resp = client.delete("/notes/nuid-1")
    assert resp.status_code == 200
    assert resp.json()["action"] == "soft_deleted"


def test_delete_note_hard(client):
    result = DeleteNoteResult(uid="nuid-1", action="hard_deleted")
    with patch("api.routers.notes.delete_note", return_value=result):
        resp = client.delete("/notes/nuid-1?force=true")
    assert resp.status_code == 200
    assert resp.json()["action"] == "hard_deleted"


def test_delete_note_not_found(client):
    with patch("api.routers.notes.delete_note", side_effect=NotFoundError("Note", "nuid-1")):
        resp = client.delete("/notes/nuid-1")
    assert resp.status_code == 404


def test_delete_note_conflict(client):
    with patch("api.routers.notes.delete_note", side_effect=ConflictError("Note", "nuid-1", "already pending")):
        resp = client.delete("/notes/nuid-1")
    assert resp.status_code == 409


def test_restore_note(client):
    result = RestoreNoteResult(uid="nuid-1", restored_sync_status="synced")
    with patch("api.routers.notes.restore_note", return_value=result):
        resp = client.post("/notes/nuid-1/restore")
    assert resp.status_code == 200
    assert resp.json()["restored_sync_status"] == "synced"
```

Create `tests/api/test_sources_delete.py`:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from core.schemas import DeleteSourceResult, RestoreSourceResult, PurgeResult
from core.errors import NotFoundError, ConflictError


@pytest.fixture
def client(tmp_settings):
    from api.main import create_app
    app = create_app(tmp_settings)
    return TestClient(app)


def test_delete_source_soft(client):
    result = DeleteSourceResult(uid="suid-1", action="soft_deleted", media_deleted=False, orphaned_note_uids=[])
    with patch("api.routers.sources.delete_source", return_value=result):
        resp = client.delete("/sources/suid-1")
    assert resp.status_code == 200
    assert resp.json()["action"] == "soft_deleted"


def test_delete_source_hard(client):
    result = DeleteSourceResult(uid="suid-1", action="hard_deleted", media_deleted=False, orphaned_note_uids=[])
    with patch("api.routers.sources.delete_source", return_value=result):
        resp = client.delete("/sources/suid-1?force=true")
    assert resp.status_code == 200


def test_delete_source_not_found(client):
    with patch("api.routers.sources.delete_source", side_effect=NotFoundError("Source", "suid-1")):
        resp = client.delete("/sources/suid-1")
    assert resp.status_code == 404


def test_restore_source(client):
    result = RestoreSourceResult(uid="suid-1", restored_status="rag_ready")
    with patch("api.routers.sources.restore_source", return_value=result):
        resp = client.post("/sources/suid-1/restore")
    assert resp.status_code == 200


def test_purge(client):
    result = PurgeResult(notes_purged=2, sources_purged=1, media_files_deleted=1)
    with patch("api.routers.vault.purge", return_value=result):
        resp = client.post("/vault/purge")
    assert resp.status_code == 200
    assert resp.json()["notes_purged"] == 2
```

- [ ] **Step 2: Add DELETE and restore to `api/routers/notes.py`**

Add at the end of `api/routers/notes.py`:

```python
@router.delete("/{uid}", response_model=DeleteNoteResult)
def delete_note_endpoint(
    uid: str,
    request: Request,
    force: bool = False,
    delete_source: bool = False,
):
    from core.errors import NotFoundError, ConflictError
    from tools.vault.delete_note import delete_note
    from tools.vault.delete_source import delete_source as _delete_source_tool
    settings = request.app.state.settings
    try:
        result = delete_note(uid, settings, force=force)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if delete_source and force:
        note = get_note(settings.vault_db_path, uid)  # note is already deleted if hard-delete succeeded
        # routing layer: if note had source_uid before deletion, delete the source too
        # source_uid was on the note before hard-delete — we need it from result or pre-fetched
    return result


@router.post("/{uid}/restore", response_model=RestoreNoteResult)
def restore_note_endpoint(uid: str, request: Request):
    from core.errors import NotFoundError, ConflictError
    from tools.vault.restore_note import restore_note
    settings = request.app.state.settings
    try:
        return restore_note(uid, settings)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

**Important:** the `delete_source=True` cascade in the API needs the `source_uid` before the note is deleted. Update `delete_note_endpoint` to fetch the note first:

```python
@router.delete("/{uid}", response_model=DeleteNoteResult)
def delete_note_endpoint(
    uid: str,
    request: Request,
    force: bool = False,
    delete_source: bool = False,
):
    from core.errors import NotFoundError, ConflictError
    from tools.vault.delete_note import delete_note
    settings = request.app.state.settings

    # Pre-fetch source_uid for cascade before note is deleted
    source_uid = None
    if delete_source and force:
        note = get_note(settings.vault_db_path, uid)
        if note:
            source_uid = note.source_uid

    try:
        result = delete_note(uid, settings, force=force)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if source_uid and delete_source and force:
        from tools.vault.delete_source import delete_source as _delete_source
        try:
            _delete_source(source_uid, settings, force=True)
            result = result.model_copy(update={"deleted_source_uid": source_uid})
        except Exception:
            pass  # source deletion is best-effort; note already deleted

    return result
```

Add to imports at top of `api/routers/notes.py`:
```python
from core.schemas import DeleteNoteResult, RestoreNoteResult
```

- [ ] **Step 3: Add DELETE and restore to `api/routers/sources.py`**

Add at the end of `api/routers/sources.py`:

```python
@router.delete("/{uid}", response_model=DeleteSourceResult)
def delete_source_endpoint(uid: str, request: Request, force: bool = False):
    from core.errors import NotFoundError, ConflictError
    from tools.vault.delete_source import delete_source
    settings = request.app.state.settings
    try:
        return delete_source(uid, settings, force=force)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Source '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{uid}/restore", response_model=RestoreSourceResult)
def restore_source_endpoint(uid: str, request: Request):
    from core.errors import NotFoundError, ConflictError
    from tools.vault.restore_source import restore_source
    settings = request.app.state.settings
    try:
        return restore_source(uid, settings)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Source '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

Add to imports at top of `api/routers/sources.py`:
```python
from core.schemas import DeleteSourceResult, RestoreSourceResult
from fastapi import HTTPException
```

- [ ] **Step 4: Create `api/routers/vault.py`**

```python
from fastapi import APIRouter, Request
from core.schemas import PurgeResult

router = APIRouter(prefix="/vault", tags=["vault"])


@router.post("/purge", response_model=PurgeResult)
def purge_endpoint(request: Request):
    from tools.vault.purge import purge
    return purge(request.app.state.settings)
```

- [ ] **Step 5: Register vault router in `api/main.py`**

In `api/main.py`, add:
```python
from api.routers.vault import router as vault_router
```
And in `create_app`:
```python
app.include_router(vault_router)
```

- [ ] **Step 6: Run API tests**

```bash
.venv/Scripts/python -m pytest tests/api/test_notes_delete.py tests/api/test_sources_delete.py -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add api/routers/notes.py api/routers/sources.py api/routers/vault.py api/main.py \
        tests/api/test_notes_delete.py tests/api/test_sources_delete.py
git commit -m "feat: add delete/restore/purge API endpoints"
```

---

## Task 7: CLI Commands

**Files:**
- Modify: `cli/commands/notes.py`
- Modify: `cli/commands/sources.py`
- Create: `cli/commands/purge.py`
- Modify: `cli/main.py`

- [ ] **Step 1: Add `note delete` and `note restore` to `cli/commands/notes.py`**

Add at the end of `cli/commands/notes.py`:

```python
def _delete_note(uid, settings, force):
    from tools.vault.delete_note import delete_note
    return delete_note(uid, settings, force=force)


def _restore_note(uid, settings):
    from tools.vault.restore_note import restore_note
    return restore_note(uid, settings)


def _delete_source_tool(source_uid, settings):
    from tools.vault.delete_source import delete_source
    return delete_source(source_uid, settings, force=True)


@app.command("delete")
def note_delete(
    uid: Annotated[str, typer.Argument(help="Note UID to delete")],
    force: Annotated[bool, typer.Option("--force", help="Hard-delete immediately (irreversible)")] = False,
    delete_source: Annotated[bool, typer.Option("--delete-source", help="Also delete linked source")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Delete a note. Soft-delete by default; use --force for immediate removal."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if force and not yes:
        note = _get_note(settings.vault_db_path, uid)
        summary = f"Note: {note.title if note else uid}"
        if delete_source and note and note.source_uid:
            summary += f"\nLinked source: {note.source_uid} (and all its chunks, media)"
        typer.echo(f"This will permanently delete:\n  {summary}")
        if not typer.confirm("Confirm permanent deletion?"):
            raise typer.Exit(0)

    try:
        result = _delete_note(uid, settings, force=force)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Delete failed.", "delete_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if delete_source and force and result.action == "hard_deleted":
        note_before = _get_note(settings.vault_db_path, uid)
        # note is already deleted at this point; source_uid was captured before deletion
        # routing layer: handled via pre-fetch — see API for pattern
        pass  # source deletion cascade is best handled by the API; CLI defers to explicit source delete

    fields = {"uid": result.uid, "action": result.action}
    print_panel("Note deleted", fields, json_mode)


@app.command("restore")
def note_restore(
    uid: Annotated[str, typer.Argument(help="Note UID to restore")],
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Restore a note previously marked for deletion."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _restore_note(uid, settings)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Restore failed.", "restore_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    print_panel("Note restored", {"uid": result.uid, "sync_status": result.restored_sync_status}, json_mode)
```

**Note on `--delete-source` cascade in CLI:** the CLI `note delete --delete-source --force` command should pre-fetch the `source_uid` before calling `_delete_note`, then call `_delete_source_tool` after. Update the `note_delete` function:

```python
# Before calling _delete_note, capture source_uid if needed
source_uid_to_delete = None
if delete_source and force:
    note_before = _get_note(settings.vault_db_path, uid)
    if note_before and note_before.source_uid:
        source_uid_to_delete = note_before.source_uid

try:
    result = _delete_note(uid, settings, force=force)
except ...

if source_uid_to_delete:
    try:
        _delete_source_tool(source_uid_to_delete, settings)
        result = result.model_copy(update={"deleted_source_uid": source_uid_to_delete})
    except Exception as e:
        print_error(f"Note deleted but source deletion failed: {e}", "source_error", json_mode, verbose)
```

- [ ] **Step 2: Add `source delete` and `source restore` to `cli/commands/sources.py`**

Add at the end of `cli/commands/sources.py`:

```python
def _delete_source(uid, settings, force):
    from tools.vault.delete_source import delete_source
    return delete_source(uid, settings, force=force)


def _restore_source(uid, settings):
    from tools.vault.restore_source import restore_source
    return restore_source(uid, settings)


@app.command("delete")
def source_delete(
    uid: Annotated[str, typer.Argument(help="Source UID to delete")],
    force: Annotated[bool, typer.Option("--force", help="Hard-delete immediately (irreversible)")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Delete a source. Soft-delete by default; use --force for immediate removal."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if force and not yes:
        source = _get_source(settings.vault_db_path, uid)
        summary = f"Source: {source.title or source.slug if source else uid}"
        if source and source.media_path:
            summary += f"\nMedia file: {source.media_path}"
        summary += "\nAll chunks and embeddings"
        typer.echo(f"This will permanently delete:\n  {summary}")
        if not typer.confirm("Confirm permanent deletion?"):
            raise typer.Exit(0)

    try:
        result = _delete_source(uid, settings, force=force)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Delete failed.", "delete_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    fields: dict = {"uid": result.uid, "action": result.action}
    if result.orphaned_note_uids:
        fields["orphaned_notes"] = ", ".join(result.orphaned_note_uids)
    print_panel("Source deleted", fields, json_mode)


@app.command("restore")
def source_restore(
    uid: Annotated[str, typer.Argument(help="Source UID to restore")],
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Restore a source previously marked for deletion."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _restore_source(uid, settings)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Restore failed.", "restore_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    print_panel("Source restored", {"uid": result.uid, "status": result.restored_status}, json_mode)
```

- [ ] **Step 3: Create `cli/commands/purge.py`**

```python
"""
Purge command — permanently removes all pending_deletion items.

Routing layer only. No business logic.
"""

from typing import Annotated
import typer
from cli.output import print_panel, print_error, print_table

app = typer.Typer(help="Purge all items marked for deletion.")


def _load_settings():
    from core.config import load_settings
    return load_settings()


def _run_purge(settings):
    from tools.vault.purge import purge
    return purge(settings)


def _list_pending(settings):
    from infrastructure.db import list_notes_pending_deletion, list_sources_pending_deletion
    return (
        list_notes_pending_deletion(settings.vault_db_path),
        list_sources_pending_deletion(settings.vault_db_path),
    )


@app.command()
def purge_cmd(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="List what would be purged without deleting")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Permanently delete all items currently marked for deletion."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    pending_notes, pending_sources = _list_pending(settings)

    if dry_run:
        typer.echo(f"Pending deletion: {len(pending_notes)} notes, {len(pending_sources)} sources")
        if verbose and pending_notes:
            print_table(["uid", "title"], [[n.uid, n.title] for n in pending_notes], json_mode)
        if verbose and pending_sources:
            print_table(["uid", "slug"], [[s.uid, s.slug] for s in pending_sources], json_mode)
        raise typer.Exit(0)

    if not pending_notes and not pending_sources:
        typer.echo("Nothing to purge.")
        raise typer.Exit(0)

    if not yes:
        typer.echo(f"About to permanently delete {len(pending_notes)} notes and {len(pending_sources)} sources.")
        if not typer.confirm("Confirm purge? This cannot be undone."):
            raise typer.Exit(0)

    try:
        result = _run_purge(settings)
    except Exception as e:
        print_error("Purge failed.", "purge_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    print_panel("Purge complete", {
        "notes_purged": result.notes_purged,
        "sources_purged": result.sources_purged,
        "media_files_deleted": result.media_files_deleted,
    }, json_mode)
```

- [ ] **Step 4: Register purge in `cli/main.py`**

Add to `cli/main.py`:
```python
from cli.commands.purge import app as purge_app
```
And:
```python
app.add_typer(purge_app, name="purge")
```

- [ ] **Step 5: Smoke test CLI commands exist**

```bash
.venv/Scripts/python -m cli.main note delete --help
.venv/Scripts/python -m cli.main note restore --help
.venv/Scripts/python -m cli.main source delete --help
.venv/Scripts/python -m cli.main source restore --help
.venv/Scripts/python -m cli.main purge --help
```
Expected: all show help without error.

- [ ] **Step 6: Commit**

```bash
git add cli/commands/notes.py cli/commands/sources.py cli/commands/purge.py cli/main.py
git commit -m "feat: add delete/restore/purge CLI commands"
```

---

## Task 8: MCP Tools (Conditional Registration)

**Files:**
- Modify: `mcp/server.py`

- [ ] **Step 1: Add conditional delete/purge tool registration to `mcp/server.py`**

In `mcp/server.py`, after the existing tool registrations, add a conditional block:

```python
# Destructive operations — only registered if allow_destructive_ops is True
if settings and settings.user.allow_destructive_ops:
    from tools.vault.delete_note import delete_note as _delete_note_tool
    from tools.vault.delete_source import delete_source as _delete_source_tool
    from tools.vault.restore_note import restore_note as _restore_note_tool
    from tools.vault.restore_source import restore_source as _restore_source_tool
    from tools.vault.purge import purge as _purge_tool

    @mcp.tool()
    def delete_note(uid: str, force: bool = False) -> dict:
        """
        Mark a note for deletion or permanently remove it.
        Without force: marks as pending deletion, reversible via restore_note.
        With force: permanently removes the note, its embedding, and its Markdown file.
        """
        return _delete_note_tool(uid, settings, force=force).model_dump(mode="json")

    @mcp.tool()
    def delete_source(uid: str, force: bool = False) -> dict:
        """
        Mark a source for deletion or permanently remove it.
        Without force: marks as pending deletion, reversible via restore_source.
        With force: permanently removes the source, all its chunks, embeddings, and media file.
        Linked notes become orphaned — they are not deleted.
        """
        return _delete_source_tool(uid, settings, force=force).model_dump(mode="json")

    @mcp.tool()
    def restore_note(uid: str) -> dict:
        """
        Restore a note previously marked for deletion.
        Reverts to the sync status it had before soft-deletion.
        """
        return _restore_note_tool(uid, settings).model_dump(mode="json")

    @mcp.tool()
    def restore_source(uid: str) -> dict:
        """
        Restore a source previously marked for deletion.
        Reverts to the status it had before soft-deletion.
        """
        return _restore_source_tool(uid, settings).model_dump(mode="json")

    @mcp.tool()
    def purge() -> dict:
        """
        Permanently remove all notes and sources currently marked for deletion.
        This operation cannot be undone.
        """
        return _purge_tool(settings).model_dump(mode="json")
```

- [ ] **Step 2: Verify MCP server still starts**

```bash
.venv/Scripts/python -c "import mcp.server; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mcp/server.py
git commit -m "feat: add delete/purge MCP tools (gated by allow_destructive_ops)"
```

---

## Task 9: Full Test Suite

- [ ] **Step 1: Run the complete test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short -q
```
Expected: all PASS

- [ ] **Step 2: Run the migration on the dev DB to verify it works end to end**

```bash
.venv/Scripts/python scripts/temp/_002_add_previous_status.py
```
Expected: `Migration 002 applied to ...` and `Done.`

- [ ] **Step 3: Final commit if any fixups needed**

```bash
git add -p
git commit -m "chore: A3 delete operations — fixups"
```
