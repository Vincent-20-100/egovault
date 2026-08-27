# A1 — MCP Flow Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the core value loop — embed notes on creation/update so `notes_vec` is populated, complete the MCP tool surface, and document MCP client setup.

**Architecture:** Three sequential improvements. (1) `embed_note` tool + auto-embed hooks in `create_note`/`update_note` so `notes_vec` is always current. (2) Four missing MCP tools (`update_note`, `get_source`, `list_notes`, `list_sources`) + a `get_workflow_guide` tool. (3) Enriched docstrings on all MCP tools + setup documentation. All embedding calls go through `infrastructure.embedding_provider.embed()` — never through the `embed_text` tool (tool isolation rule).

**Tech Stack:** Python 3.x, sqlite-vec, Pydantic v2, FastMCP, pytest

**Source:** `docs/PRODUCT-AUDIT.md` §2

---

## File map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `core/schemas.py` | Add `EmbedNoteResult` |
| Create | `tools/text/embed_note.py` | Embed note by UID into `notes_vec` |
| Create | `tests/tools/text/test_embed_note.py` | Tests for `embed_note` |
| Modify | `tools/vault/create_note.py` | Auto-embed after insert |
| Modify | `tests/tools/vault/test_create_note.py` | Add embedding mock to existing tests |
| Modify | `tools/vault/update_note.py` | Auto-re-embed after update |
| Modify | `tests/tools/vault/test_update_note.py` | Update sync_status assertion + embedding mocks |
| Modify | `mcp/server.py` | Add 5 new tools, enrich all docstrings |
| Modify | `tests/mcp/test_server.py` | Test new MCP tools |
| Create | `docs/mcp-setup.md` | MCP client setup guide |

---

## Task 1: `EmbedNoteResult` schema

**Files:**
- Modify: `core/schemas.py` (append after line 198, after `ExportResult`)

- [ ] **Step 1: Add `EmbedNoteResult` to `core/schemas.py`**

Append after the `ExportResult` class:

```python
class EmbedNoteResult(BaseModel):
    note_uid: str
    embedding_dim: int
```

- [ ] **Step 2: Run tests to verify no breakage**

```
.venv/Scripts/python -m pytest tests/ -q
```

Expected: all existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add core/schemas.py
git commit -m "feat: add EmbedNoteResult schema"
```

---

## Task 2: `embed_note` tool

**Files:**
- Create: `tools/text/embed_note.py`
- Create: `tests/tools/text/test_embed_note.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/text/test_embed_note.py`:

```python
import pytest
import unittest.mock as mock
from unittest.mock import patch
from datetime import date
from core.schemas import Note, EmbedNoteResult


def _insert_test_note(tmp_db):
    from infrastructure.db import insert_note
    note = Note(
        uid="n1",
        slug="test-note",
        title="Test Title",
        docstring="Short description.",
        body="Body content here.",
        tags=["test-tag"],
        date_created=date.today().isoformat(),
        date_modified=date.today().isoformat(),
    )
    insert_note(tmp_db, note)
    return note


def test_embed_note_returns_result(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        result = embed_note("n1", tmp_settings)

    assert isinstance(result, EmbedNoteResult)
    assert result.note_uid == "n1"
    assert result.embedding_dim == 768


def test_embed_note_populates_notes_vec(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note
    from infrastructure.db import search_notes

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        embed_note("n1", tmp_settings)

    results = search_notes(tmp_db, [0.1] * 768, None, 5)
    assert len(results) == 1
    assert results[0].note_uid == "n1"


def test_embed_note_replaces_existing_embedding(tmp_settings, tmp_db):
    """Calling embed_note twice must not create duplicate rows in notes_vec."""
    from tools.text.embed_note import embed_note
    from infrastructure.db import search_notes

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        embed_note("n1", tmp_settings)
        embed_note("n1", tmp_settings)  # second call — must not duplicate

    results = search_notes(tmp_db, [0.1] * 768, None, 10)
    assert len(results) == 1


def test_embed_note_sets_sync_status_synced(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note
    from infrastructure.db import get_note

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        embed_note("n1", tmp_settings)

    note = get_note(tmp_db, "n1")
    assert note.sync_status == "synced"


def test_embed_note_not_found_raises(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)):
        with pytest.raises(ValueError, match="not found"):
            embed_note("nonexistent", tmp_settings)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
.venv/Scripts/python -m pytest tests/tools/text/test_embed_note.py -v
```

Expected: all 5 FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement `embed_note`**

Create `tools/text/embed_note.py`:

```python
"""
Note embedding tool.

Input  : note_uid string + settings
Output : EmbedNoteResult
Populates notes_vec. Safe to call multiple times (delete + reinsert).
"""

from core.schemas import EmbedNoteResult
from core.config import Settings
from core.logging import loggable


@loggable("embed_note")
def embed_note(note_uid: str, settings: Settings) -> EmbedNoteResult:
    """
    Embed a note into notes_vec using the configured embedding provider.
    Combines title + docstring + body for embedding.
    Safe to call multiple times — deletes the existing embedding before reinserting.
    Sets sync_status to 'synced'.
    """
    from infrastructure.db import (
        get_note, delete_note_embedding, insert_note_embedding,
        update_note as db_update,
    )
    from infrastructure.embedding_provider import embed

    note = get_note(settings.vault_db_path, note_uid)
    if note is None:
        raise ValueError(f"Note not found: {note_uid}")

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = embed(text, settings)

    delete_note_embedding(settings.vault_db_path, note_uid)
    insert_note_embedding(settings.vault_db_path, note_uid, embedding)
    db_update(settings.vault_db_path, note_uid, {"sync_status": "synced"})

    return EmbedNoteResult(note_uid=note_uid, embedding_dim=len(embedding))
```

- [ ] **Step 4: Run tests to confirm they pass**

```
.venv/Scripts/python -m pytest tests/tools/text/test_embed_note.py -v
```

Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/text/embed_note.py tests/tools/text/test_embed_note.py
git commit -m "feat: add embed_note tool — populates notes_vec on demand"
```

---

## Task 3: Auto-embed in `create_note`

**Files:**
- Modify: `tools/vault/create_note.py`
- Modify: `tests/tools/vault/test_create_note.py`

- [ ] **Step 1: Update existing tests to mock embedding**

`create_note` will now call `infrastructure.embedding_provider.embed`. Update `tests/tools/vault/test_create_note.py` — add `patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768)` to the three tests that complete successfully:

```python
import pytest
from datetime import date
from unittest.mock import patch
from core.schemas import NoteContentInput, NoteSystemFields, NoteResult
from core.uid import generate_uid
import unittest.mock as mock


def _content(**overrides):
    data = {
        "title": "Test Note Title",
        "docstring": "What this note is about.",
        "body": "This is the body of the test note, long enough.",
        "tags": ["test-tag"],
        "note_type": None,
        "source_type": None,
    }
    data.update(overrides)
    return NoteContentInput(**data)


def _system_fields(**overrides):
    data = {
        "uid": generate_uid(),
        "date_created": date.today().isoformat(),
        "source_uid": None,
        "slug": "test-note-title",
        "generation_template": None,
    }
    data.update(overrides)
    return NoteSystemFields(**data)


def test_create_note_returns_note_result(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        result = create_note(_content(), _system_fields(), tmp_settings)

    assert isinstance(result, NoteResult)
    assert result.note.title == "Test Note Title"
    assert result.markdown_path.endswith(".md")


def test_create_note_writes_to_db(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    from infrastructure.db import get_note

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        system = _system_fields()
        create_note(_content(), system, tmp_settings)
        note = get_note(tmp_db, system.uid)

    assert note is not None
    assert note.title == "Test Note Title"


def test_create_note_writes_markdown_file(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    from pathlib import Path

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        system = _system_fields()
        result = create_note(_content(), system, tmp_settings)

    assert Path(result.markdown_path).exists()
    content = Path(result.markdown_path).read_text()
    assert "# Test Note Title" in content


def test_create_note_embeds_into_notes_vec(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    from infrastructure.db import search_notes

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        system = _system_fields()
        create_note(_content(), system, tmp_settings)

    results = search_notes(tmp_db, [0.1] * 768, None, 5)
    assert len(results) == 1
    assert results[0].note_uid == system.uid


def test_create_note_source_type_mismatch_raises(tmp_settings, tmp_db, tmp_path):
    from tools.vault.create_note import create_note
    from infrastructure.db import insert_source
    from core.schemas import Source

    source = Source(
        uid="src-1", slug="src", source_type="youtube", status="rag_ready",
        date_added=date.today().isoformat(),
    )
    insert_source(tmp_db, source)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        with pytest.raises(ValueError, match="source_type"):
            create_note(
                _content(source_type="audio"),
                _system_fields(source_uid="src-1"),
                tmp_settings,
            )
```

- [ ] **Step 2: Run updated tests to confirm they now fail on the new test**

```
.venv/Scripts/python -m pytest tests/tools/vault/test_create_note.py -v
```

Expected: `test_create_note_embeds_into_notes_vec` FAILS (notes_vec empty), others PASS.

- [ ] **Step 3: Update `create_note` to auto-embed**

Replace `tools/vault/create_note.py` with:

```python
"""
Note creation tool.

Input  : NoteContentInput (LLM or manual) + NoteSystemFields
Output : NoteResult (note record + markdown path)
Writes to DB, embeds into notes_vec, and generates Markdown file.
Requires prior human approval of NoteContentInput before calling.
"""

from datetime import date

from core.schemas import NoteContentInput, NoteSystemFields, NoteResult, Note
from core.config import Settings
from core.logging import loggable


@loggable("create_note")
def create_note(
    content: NoteContentInput,
    system_fields: NoteSystemFields,
    settings: Settings,
) -> NoteResult:
    """
    Validate and persist a note.
    - Validates content.source_type matches source.source_type when source_uid is set.
    - Writes note to DB (notes + note_tags tables).
    - Embeds note into notes_vec automatically (title + docstring + body).
    - Generates Markdown via vault_writer.write_note().
    Requires prior human approval of NoteContentInput before calling.
    """
    from infrastructure.db import insert_note, get_source, insert_note_embedding
    from infrastructure.embedding_provider import embed
    from infrastructure.vault_writer import write_note

    if system_fields.source_uid:
        source = get_source(settings.vault_db_path, system_fields.source_uid)
        if (source and content.source_type
                and content.source_type != source.source_type):
            raise ValueError(
                f"content.source_type '{content.source_type}' does not match "
                f"source.source_type '{source.source_type}'"
            )

    today = date.today().isoformat()
    note = Note(
        **system_fields.model_dump(),
        **content.model_dump(),
        date_modified=today,
        sync_status="synced",
    )

    insert_note(settings.vault_db_path, note)

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = embed(text, settings)
    insert_note_embedding(settings.vault_db_path, note.uid, embedding)

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(note, settings.vault_path)

    return NoteResult(note=note, markdown_path=str(markdown_path))
```

- [ ] **Step 4: Run all tests**

```
.venv/Scripts/python -m pytest tests/tools/vault/test_create_note.py -v
```

Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/vault/create_note.py tests/tools/vault/test_create_note.py
git commit -m "feat: auto-embed note into notes_vec on creation"
```

---

## Task 4: Auto-re-embed in `update_note`

**Files:**
- Modify: `tools/vault/update_note.py`
- Modify: `tests/tools/vault/test_update_note.py`

- [ ] **Step 1: Update existing tests**

`_insert_test_note` calls `create_note` which now embeds. `update_note` will also embed. Both need the embedding mock. Replace `tests/tools/vault/test_update_note.py` with:

```python
import pytest
from datetime import date
from unittest.mock import patch
from core.schemas import NoteContentInput, NoteSystemFields
from core.uid import generate_uid
import unittest.mock as mock


def _insert_test_note(tmp_db, tmp_path, tmp_settings):
    from tools.vault.create_note import create_note

    content = NoteContentInput(
        title="Original Title",
        docstring="Original docstring here.",
        body="Original body content of the note.",
        tags=["original-tag"],
    )
    system = NoteSystemFields(
        uid=generate_uid(),
        date_created=date.today().isoformat(),
        slug="original-title",
    )
    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        result = create_note(content, system, tmp_settings)
    return result.note.uid


def test_update_note_returns_note_result(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note
    from core.schemas import NoteResult

    uid = _insert_test_note(tmp_db, tmp_path, tmp_settings)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        result = update_note(uid, {"rating": 5}, tmp_settings)

    assert isinstance(result, NoteResult)
    assert result.note.rating == 5


def test_update_note_re_embeds_note(tmp_settings, tmp_db, tmp_path):
    """After update, note must be re-embedded and sync_status must be 'synced'."""
    from tools.vault.update_note import update_note
    from infrastructure.db import search_notes

    uid = _insert_test_note(tmp_db, tmp_path, tmp_settings)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.2] * 768):
        result = update_note(uid, {"body": "Updated body content here."}, tmp_settings)

    assert result.note.sync_status == "synced"
    results = search_notes(tmp_db, [0.2] * 768, None, 5)
    assert any(r.note_uid == uid for r in results)


def test_update_note_ignores_system_fields(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note
    from infrastructure.db import get_note

    uid = _insert_test_note(tmp_db, tmp_path, tmp_settings)
    original_uid = uid

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)), \
         patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768):
        update_note(uid, {"uid": "new-uid", "date_created": "2000-01-01"}, tmp_settings)
        note = get_note(tmp_db, original_uid)

    assert note is not None
    assert note.date_created != "2000-01-01"


def test_update_note_not_found_raises(tmp_settings, tmp_db, tmp_path):
    from tools.vault.update_note import update_note

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "vault_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        with pytest.raises(ValueError, match="not found"):
            update_note("nonexistent-uid", {"rating": 3}, tmp_settings)
```

- [ ] **Step 2: Run tests to confirm `test_update_note_re_embeds_note` fails**

```
.venv/Scripts/python -m pytest tests/tools/vault/test_update_note.py -v
```

Expected: `test_update_note_re_embeds_note` FAILS (sync_status is "needs_re_embedding", notes_vec not updated).

- [ ] **Step 3: Update `update_note` to auto-re-embed**

Replace `tools/vault/update_note.py` with:

```python
"""
Note update tool.

Input  : note uid + partial field update
Output : NoteResult
Writes to DB, re-embeds into notes_vec, regenerates Markdown.
"""

from datetime import date

from core.schemas import NoteResult
from core.config import Settings
from core.logging import loggable

_SYSTEM_FIELDS = {"uid", "date_created", "source_uid", "generation_template"}


@loggable("update_note")
def update_note(uid: str, fields: dict, settings: Settings) -> NoteResult:
    """
    Update editable fields of an existing note.
    SYSTEM fields (uid, date_created, source_uid, generation_template) are silently ignored.
    Re-embeds the note into notes_vec after any update.
    Updates date_modified. Regenerates Markdown file via vault_writer.
    """
    from infrastructure.db import (
        get_note, update_note as db_update,
        delete_note_embedding, insert_note_embedding,
    )
    from infrastructure.embedding_provider import embed
    from infrastructure.vault_writer import write_note

    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise ValueError(f"Note not found: {uid}")

    safe_fields = {k: v for k, v in fields.items() if k not in _SYSTEM_FIELDS}
    safe_fields["date_modified"] = date.today().isoformat()

    db_update(settings.vault_db_path, uid, safe_fields)
    updated_note = get_note(settings.vault_db_path, uid)

    text = "\n\n".join(filter(None, [updated_note.title, updated_note.docstring, updated_note.body]))
    embedding = embed(text, settings)
    delete_note_embedding(settings.vault_db_path, uid)
    insert_note_embedding(settings.vault_db_path, uid, embedding)
    db_update(settings.vault_db_path, uid, {"sync_status": "synced"})
    updated_note = get_note(settings.vault_db_path, uid)

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(updated_note, settings.vault_path)

    return NoteResult(note=updated_note, markdown_path=str(markdown_path))
```

- [ ] **Step 4: Run all tests**

```
.venv/Scripts/python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/vault/update_note.py tests/tools/vault/test_update_note.py
git commit -m "feat: auto-re-embed note into notes_vec on update"
```

---

## Task 5: MCP — expose `update_note`

**Files:**
- Modify: `mcp/server.py` (import + new tool)
- Modify: `tests/mcp/test_server.py`

- [ ] **Step 1: Write failing test**

Add to `tests/mcp/test_server.py`:

```python
# ---------------------------------------------------------------------------
# update_note
# ---------------------------------------------------------------------------

def test_mcp_update_note_calls_tool(tmp_settings):
    import mcp.server as srv
    from core.schemas import NoteResult, Note
    from datetime import date

    note = Note(
        uid="n1", slug="test-note", title="Updated Title", tags=["tag1"],
        body="Updated body.", docstring="Updated docstring.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        rating=4,
    )
    mock_result = NoteResult(note=note, markdown_path="/tmp/test.md")

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._update_note_tool", return_value=mock_result) as mock_tool:
        result = srv.update_note("n1", {"rating": 4})

    mock_tool.assert_called_once_with("n1", {"rating": 4}, tmp_settings)
    assert result["note"]["rating"] == 4
```

- [ ] **Step 2: Run test to confirm it fails**

```
.venv/Scripts/python -m pytest tests/mcp/test_server.py::test_mcp_update_note_calls_tool -v
```

Expected: FAIL with `AttributeError: module 'mcp.server' has no attribute 'update_note'`.

- [ ] **Step 3: Add `update_note` to `mcp/server.py`**

Add import at the top of `mcp/server.py` (with the other tool imports):

```python
from tools.vault.update_note import update_note as _update_note_tool
```

Add the tool function (after the existing `create_note` tool, before `if __name__ == "__main__"`):

```python
@mcp.tool()
def update_note(uid: str, fields: dict) -> dict:
    """
    Update editable fields on an existing note.

    When to use: After reviewing a note (via get_note) and wanting to improve the
    body, fix the title, add a rating, or update tags.

    Editable fields: title, docstring, body, note_type, source_type, rating (1-5), url.
    System fields (uid, date_created, source_uid, generation_template) are ignored.

    What to call next: finalize_source(source_uid) if the associated source is ready
    to be archived as vaulted.
    """
    result = _update_note_tool(uid, fields, settings)
    return result.model_dump(mode="json")
```

- [ ] **Step 4: Run test to confirm it passes**

```
.venv/Scripts/python -m pytest tests/mcp/test_server.py::test_mcp_update_note_calls_tool -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```
.venv/Scripts/python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add mcp/server.py tests/mcp/test_server.py
git commit -m "feat: expose update_note in MCP server"
```

---

## Task 6: MCP — expose `get_source`, `list_notes`, `list_sources`

**Files:**
- Modify: `mcp/server.py`
- Modify: `tests/mcp/test_server.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/mcp/test_server.py`:

```python
# ---------------------------------------------------------------------------
# get_source
# ---------------------------------------------------------------------------

def test_mcp_get_source_returns_source(tmp_settings):
    import mcp.server as srv
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-1", slug="src-1", source_type="youtube",
        status="rag_ready", date_added=date.today().isoformat(),
        title="My Video",
    )

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._get_source_db", return_value=source):
        result = srv.get_source("src-1")

    assert result["uid"] == "src-1"
    assert result["title"] == "My Video"


def test_mcp_get_source_not_found_raises(tmp_settings):
    import mcp.server as srv

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._get_source_db", return_value=None):
        with pytest.raises(ValueError, match="not found"):
            srv.get_source("nonexistent")


# ---------------------------------------------------------------------------
# list_notes
# ---------------------------------------------------------------------------

def test_mcp_list_notes_returns_notes(tmp_settings):
    import mcp.server as srv
    from core.schemas import Note
    from datetime import date

    note = Note(
        uid="n1", slug="note-1", title="Note 1", tags=["tag1"],
        body="Body.", docstring="Desc.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._list_notes_db", return_value=[note]) as mock_fn:
        result = srv.list_notes(limit=10, offset=0)

    mock_fn.assert_called_once_with(tmp_settings.vault_db_path, None, None, 10, 0)
    assert len(result) == 1
    assert result[0]["uid"] == "n1"


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------

def test_mcp_list_sources_returns_sources(tmp_settings):
    import mcp.server as srv
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-1", slug="src-1", source_type="youtube",
        status="rag_ready", date_added=date.today().isoformat(),
    )

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._list_sources_db", return_value=[source]) as mock_fn:
        result = srv.list_sources(limit=10, offset=0, status="rag_ready")

    mock_fn.assert_called_once_with(tmp_settings.vault_db_path, "rag_ready", 10, 0)
    assert len(result) == 1
    assert result[0]["uid"] == "src-1"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
.venv/Scripts/python -m pytest tests/mcp/test_server.py -k "get_source or list_notes or list_sources" -v
```

Expected: all FAIL.

- [ ] **Step 3: Add the three tools to `mcp/server.py`**

Add imports (with the other infrastructure imports, after line 25):

```python
from infrastructure.db import get_source as _get_source_db
from infrastructure.db import list_notes as _list_notes_db
from infrastructure.db import list_sources as _list_sources_db
```

Add the three tools (after `update_note`, before `if __name__ == "__main__"`):

```python
@mcp.tool()
def get_source(uid: str) -> dict:
    """
    Retrieve a full source record by UID, including its transcript.

    When to use: After search() returns a chunk, call get_source(chunk.source_uid)
    to read the full source context (title, URL, full transcript) before drafting a note.
    This is the main tool for gathering content to write a note.

    What to call next: create_note() after reading and synthesizing the source content.
    """
    source = _get_source_db(settings.vault_db_path, uid)
    if source is None:
        raise ValueError(f"Source '{uid}' not found")
    return source.model_dump(mode="json")


@mcp.tool()
def list_notes(
    limit: int = 20,
    offset: int = 0,
    note_type: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """
    Browse notes in the vault.

    When to use: To check for existing notes on a topic before creating a new one
    (avoid duplicates). Also useful to list notes for review, export, or bulk update.
    Filter by note_type (synthese, concept, reflexion) or tags.

    What to call next: get_note(uid) to read the full content of a specific note.
    """
    results = _list_notes_db(settings.vault_db_path, note_type, tags, limit, offset)
    return [n.model_dump(mode="json") for n in results]


@mcp.tool()
def list_sources(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[dict]:
    """
    Browse sources in the vault.

    When to use: To find sources awaiting note creation (use status='rag_ready'),
    or to review all ingested sources. Status values: raw, rag_ready, vaulted.

    What to call next: search(query, mode='chunks') to explore a source's content
    semantically, or get_source(uid) to read its full transcript directly.
    """
    results = _list_sources_db(settings.vault_db_path, status, limit, offset)
    return [s.model_dump(mode="json") for s in results]
```

- [ ] **Step 4: Run all MCP tests**

```
.venv/Scripts/python -m pytest tests/mcp/test_server.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full test suite**

```
.venv/Scripts/python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add mcp/server.py tests/mcp/test_server.py
git commit -m "feat: expose get_source, list_notes, list_sources in MCP server"
```

---

## Task 7: MCP — `get_workflow_guide` + enrich all docstrings

**Files:**
- Modify: `mcp/server.py`
- Modify: `tests/mcp/test_server.py`

- [ ] **Step 1: Write failing test**

Add to `tests/mcp/test_server.py`:

```python
# ---------------------------------------------------------------------------
# get_workflow_guide
# ---------------------------------------------------------------------------

def test_mcp_get_workflow_guide_returns_string(tmp_settings):
    import mcp.server as srv

    with patch("mcp.server.settings", tmp_settings):
        result = srv.get_workflow_guide()

    assert isinstance(result, str)
    assert "create_note" in result
    assert "finalize_source" in result
```

- [ ] **Step 2: Run test to confirm it fails**

```
.venv/Scripts/python -m pytest tests/mcp/test_server.py::test_mcp_get_workflow_guide_returns_string -v
```

Expected: FAIL.

- [ ] **Step 3: Add `get_workflow_guide` and enrich all docstrings in `mcp/server.py`**

Replace the full content of `mcp/server.py` with the version below. The imports and MCP boilerplate at the top remain identical — only docstrings are updated and `get_workflow_guide` is added.

Updated docstrings for existing tools:

**`chunk_text`:**
```
Split text into overlapping chunks per system.yaml:chunking config.

When to use: Rarely called directly via MCP. This is used internally by ingest
workflows. Call it if you have raw text you want to split before embedding.

What to call next: embed_text() on each chunk content to get vectors.
```

**`embed_text`:**
```
Embed a text string using the configured provider (Ollama or OpenAI).
Returns a flat list of floats. No DB write.

When to use: Rarely called directly — embedding is handled automatically
by create_note and update_note. Use this for custom embedding workflows.

What to call next: Nothing — this is a utility tool.
```

**`search`:**
```
Semantic search over the vault.
mode='chunks': chunk-level RAG — searches source content (transcripts, PDFs).
mode='notes' : note-level semantic search — searches your written notes.

When to use: The starting point for any knowledge retrieval task.
Use mode='chunks' to find raw source material for a new note.
Use mode='notes' to find existing notes on a topic.

What to call next:
- After mode='chunks': get_source(source_uid) to read the full source.
- After mode='notes': get_note(uid) to read the full note.
```

**`transcribe`:**
```
Transcribe a local audio or video file to text using faster-whisper.

When to use: When the user has a local audio/video file to process.
The file must be under the configured media directory.

What to call next: chunk_text() on the transcript, then embed each chunk.
Or use the ingest_audio API endpoint for the full automated pipeline.
```

**`compress_audio`:**
```
Compress an audio file to Opus mono at low bitrate.

When to use: Before transcription to reduce file size and speed up processing.
The file must be under the configured media directory.

What to call next: transcribe() on the compressed file.
```

**`fetch_subtitles`:**
```
Fetch subtitles for a YouTube video (auto-generated or manual).

When to use: When the video has existing subtitles and you want to skip transcription.
Falls back to transcription automatically if no subtitles are found.

What to call next: chunk_text() on the subtitle text, then embed each chunk.
Or use the ingest_youtube API endpoint for the full automated pipeline.
```

**`export_typst`:**
```
Export a note to Typst format for PDF generation.

When to use: When the user wants a formatted PDF version of a note.
Requires Typst to be installed on the system.

What to call next: Nothing — this is a terminal export action.
```

**`export_mermaid`:**
```
Export note relationships to a Mermaid diagram (note_uid or tag filter).

When to use: To visualize connections between notes or explore a topic cluster.

What to call next: Nothing — this is a terminal export action.
```

**`get_note`:**
```
Retrieve the full content of a note by UID.

When to use: After list_notes() or search(mode='notes') returns a note UID,
call this to read its full title, docstring, body, and tags.

What to call next: update_note() to edit it, or export_typst() to export it.
```

**`finalize_source`:**
```
Mark a source as 'vaulted' after its note has been created and reviewed.

When to use: After create_note() and the user has reviewed and approved the note.
This is the final step of the note creation workflow.

What to call next: Nothing — the source is now archived.
```

**`create_note`:**
```
Create a new note from source content.

When to use: After reading a source (via get_source) and synthesizing its key ideas.
Always call list_notes() first to check no similar note already exists.
The note content (NoteContentInput) must be approved by the user before calling.

Expected workflow:
1. search(query, mode='chunks') → find relevant source chunks
2. get_source(source_uid) → read full source content
3. list_notes() → check for existing notes on this topic
4. Draft NoteContentInput → show to user for approval
5. create_note(source_uid, content) → create the note
6. finalize_source(source_uid) → archive the source

content dict fields:
- title (str, 3-200 chars): note title
- docstring (str, max 300 chars): 3-line summary: what, why, thesis
- body (str): main note content in Markdown
- note_type (str|None): synthese | concept | reflexion
- source_type (str|None): youtube | audio | pdf
- tags (list[str]): 1-10 kebab-case tags in French, no accents
- url (str|None): only for source-less notes
```

New `get_workflow_guide` tool:

```python
@mcp.tool()
def get_workflow_guide() -> str:
    """
    Return the recommended MCP workflow for EgoVault.

    When to use: At the start of a session to understand the intended tool sequence,
    or when unsure how to proceed with a user's request.
    """
    return """
EgoVault MCP Workflow Guide
===========================

EgoVault is a personal knowledge vault. You (the LLM) orchestrate note creation
by calling tools in sequence. EgoVault provides the building blocks; you provide
the intelligence.

## Core workflow: Source → Note

1. DISCOVER: search(query, mode='chunks')
   → Find relevant source chunks by semantic similarity.

2. READ: get_source(source_uid)
   → Read the full source record including transcript/content.
   → Also available: list_sources(status='rag_ready') to find all unprocessed sources.

3. CHECK: list_notes(tags=[...]) or search(query, mode='notes')
   → Verify no similar note already exists before creating one.

4. DRAFT: Compose NoteContentInput
   → title, docstring (3 lines: what/why/thesis), body (Markdown), tags (French kebab-case)
   → Show the draft to the user for approval before creating.

5. CREATE: create_note(source_uid, content)
   → Persists the note and embeds it into notes_vec automatically.

6. FINALIZE: finalize_source(source_uid)
   → Archives the source as 'vaulted'. Final step of the workflow.

## Editing an existing note

1. get_note(uid) → read current content
2. Propose changes to user
3. update_note(uid, fields) → apply changes and re-embed automatically

## Browsing

- list_sources(status='rag_ready') → sources ready for note creation
- list_notes(note_type='synthese') → browse by type
- search(query, mode='notes') → semantic note search

## Key rules

- Tags must be French, lowercase, kebab-case, no accents (e.g. 'biais-cognitifs')
- Always show note draft to user before calling create_note
- finalize_source only after the note is reviewed and approved
- Never expose or log API keys
"""
```

- [ ] **Step 4: Run all MCP tests**

```
.venv/Scripts/python -m pytest tests/mcp/test_server.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full test suite**

```
.venv/Scripts/python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add mcp/server.py tests/mcp/test_server.py
git commit -m "feat: add get_workflow_guide, enrich all MCP tool docstrings"
```

---

## Task 8: MCP setup documentation

**Files:**
- Create: `docs/mcp-setup.md`

- [ ] **Step 1: Create `docs/mcp-setup.md`**

```markdown
# EgoVault MCP Setup Guide

EgoVault exposes its tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).
Connect your LLM client to `mcp/server.py` to let it orchestrate note creation autonomously.

## Prerequisites

1. EgoVault installed and configured (`uv sync`, `init_user_dir.py` run, `config/install.yaml` filled)
2. Ollama running with `nomic-embed-text` model pulled: `ollama pull nomic-embed-text`
3. At least one source ingested via the API: `POST /api/v1/ingest/youtube`

## Claude Desktop

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add to the `mcpServers` section:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "C:/path/to/egovault/.venv/Scripts/python",
      "args": ["C:/path/to/egovault/mcp/server.py"]
    }
  }
}
```

Replace `C:/path/to/egovault` with the absolute path to your egovault repository.

On macOS/Linux:
```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop after saving. You should see "egovault" appear in the MCP tools panel.

## Cursor

Create or edit `.cursor/mcp.json` at the project root or `~/.cursor/mcp.json` globally:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

## Windsurf / Codeium

Windsurf uses the same format as Cursor. Create `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

## Generic stdio (any MCP client)

EgoVault's MCP server communicates over stdio. Launch it with:

```bash
/path/to/egovault/.venv/bin/python /path/to/egovault/mcp/server.py
```

Any MCP client that supports stdio transport can connect to this process.

## Testing the connection

Once connected, ask your LLM:

> "Call get_workflow_guide() to explain how EgoVault works."

The LLM should return the EgoVault workflow guide. Then try:

> "List my sources with status rag_ready."

## Troubleshooting

**"No module named 'core'"** → Run from the egovault repo root, or ensure the venv python is used.

**"FileNotFoundError: config/install.yaml"** → Run `scripts/setup/init_user_dir.py` first and fill in `config/install.yaml`.

**"Connection refused" (Ollama)** → Start Ollama: `ollama serve`

**Tool calls silently fail** → Check that `egovault-user/data/vault.db` exists and is initialized.
```

- [ ] **Step 2: Verify file was created**

```bash
ls docs/mcp-setup.md
```

Expected: file exists.

- [ ] **Step 3: Commit**

```bash
git add docs/mcp-setup.md
git commit -m "docs: add MCP client setup guide (Claude Desktop, Cursor, Windsurf, generic stdio)"
```

---

## Self-review

### Spec coverage (audit §2)

| Requirement | Task |
|-------------|------|
| `embed_note` does not exist → `notes_vec` empty | Task 2 + 3 + 4 |
| `create_note` MCP tool doesn't trigger embed | Task 3 |
| MCP tool descriptions too terse | Task 7 |
| No MCP setup documentation | Task 8 |
| `get_source` not exposed via MCP | Task 6 |
| `list_notes` / `list_sources` not exposed via MCP | Task 6 |
| No `update_note` via MCP | Task 5 |
| `get_workflow_guide` tool | Task 7 |

All 8 requirements covered. ✓

### Placeholder scan

No TBD, TODO, or "implement later" present. ✓

### Type consistency

- `EmbedNoteResult` defined in Task 1, used in Task 2. ✓
- `_update_note_tool` import added in Task 5. ✓
- `_get_source_db`, `_list_notes_db`, `_list_sources_db` imports added in Task 6. ✓
- All mock return types match their corresponding Pydantic schemas. ✓
