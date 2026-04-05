# A4 — Internal LLM Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional internal LLM path that automatically generates a `draft` note from an ingested source after it reaches `rag_ready`, without requiring an external MCP call.

**Architecture:** A new `generate_note_from_source` tool calls `infrastructure/llm_provider.generate_note_content`, then writes the note to DB + vault + notes_vec using infrastructure functions directly (G4: tools cannot import other tools). Notes created via this path are marked `status = 'draft'`; the `status` column is added to the `notes` table by migration `_003`. All three ingest workflows accept `auto_generate_note: bool | None = None` and invoke the tool if the flag resolves to `True`. Approval cascade (draft → active + finalize_source) is handled in the routing layers (CLI, API) per G4.

**Tech Stack:** `core/errors.py` (NotFoundError/ConflictError from A2), `infrastructure/db.py`, `infrastructure/llm_provider.py`, `infrastructure/embedding_provider.py`, `infrastructure/vault_writer.py`, `tools/vault/generate_note_from_source.py` (new), three ingest workflows, `api/routers/notes.py`, `api/routers/sources.py`, `api/routers/ingest.py`, `api/models.py`, `cli/commands/sources.py`, `cli/commands/ingest.py`, `mcp/server.py`.

**Prerequisite:** A2 plan must be applied first — `Note.status` field and `"status"` in `db.update_note` allowed set are added there (Task 2.5).

---

## File Map

**Create:**
- `scripts/temp/_003_add_note_status.py` — migration: add `status TEXT NOT NULL DEFAULT 'active'` to notes
- `tools/vault/generate_note_from_source.py` — new tool
- `tests/scripts/__init__.py` — make test directory importable
- `tests/scripts/test__003_add_note_status.py` — migration tests
- `tests/tools/vault/test_generate_note_from_source.py` — tool tests
- `tests/api/test_notes_approve.py` — API approve endpoint tests
- `tests/api/test_sources_generate_note.py` — API generate-note endpoint tests

**Modify:**
- `core/config.py` — add `auto_generate_note: bool = False` to `LLMUserConfig`
- `infrastructure/db.py` — update note queries to handle `status` column
- `workflows/ingest_youtube.py` — add `auto_generate_note` param + post-rag_ready generation
- `workflows/ingest_audio.py` — same
- `workflows/ingest_pdf.py` — same
- `tests/workflows/test_ingest_youtube.py` — add auto_generate_note tests
- `tests/workflows/test_ingest_audio.py` — add auto_generate_note tests
- `tests/workflows/test_ingest_pdf.py` — add auto_generate_note tests
- `api/models.py` — add `status` to `NoteDetail`, `status` to `NotePatch`, `auto_generate_note` to `IngestYoutubeRequest`
- `api/routers/notes.py` — add `POST /notes/{uid}/approve`, update PATCH to handle `status`
- `api/routers/sources.py` — add `POST /sources/{uid}/generate-note`
- `api/routers/ingest.py` — pass `auto_generate_note` to workflows
- `cli/commands/sources.py` — add `source generate-note` command
- `cli/commands/ingest.py` — add `--generate-note` / `--no-generate-note` flags
- `mcp/server.py` — add `generate_note_from_source` tool + update workflow guide

---

## Task 1: DB Migration — add `status` column to notes

**Files:**
- Create: `scripts/temp/_003_add_note_status.py`
- Create: `tests/scripts/__init__.py`
- Create: `tests/scripts/test__003_add_note_status.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/__init__.py` (empty).

Create `tests/scripts/test__003_add_note_status.py`:

```python
import sqlite3
import pytest
from pathlib import Path


def test_migration_adds_status_column(tmp_db):
    from scripts.temp._003_add_note_status import run
    run(tmp_db)
    conn = sqlite3.connect(tmp_db)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]
    conn.close()
    assert "status" in cols


def test_migration_existing_notes_default_active(tmp_db):
    from scripts.temp._003_add_note_status import run
    from infrastructure.db import insert_note
    from core.schemas import Note
    from datetime import date

    note = Note(
        uid="n1", source_uid=None, slug="test-note", note_type=None,
        source_type=None, generation_template=None, rating=None,
        sync_status="synced", title="Test Note", docstring="Short description.",
        body="Body content here for testing.", url=None,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    insert_note(tmp_db, note)
    run(tmp_db)
    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT status FROM notes WHERE uid = 'n1'").fetchone()
    conn.close()
    assert row[0] == "active"


def test_migration_idempotent(tmp_db):
    from scripts.temp._003_add_note_status import run
    run(tmp_db)
    run(tmp_db)  # must not raise
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd /c/Users/Vincent/GitHub/Vincent-20-100/egovault
.venv/Scripts/python -m pytest tests/scripts/test__003_add_note_status.py -v
```
Expected: FAIL — `scripts/temp/_003_add_note_status` does not exist.

- [ ] **Step 3: Write the migration script**

Create `scripts/temp/_003_add_note_status.py`:

```python
"""
One-shot migration: add status column to notes table.

status TEXT NOT NULL DEFAULT 'active'
All existing notes keep status = 'active' (no data loss).
Safe to re-run (idempotent).
"""
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent.parent / "egovault-user" / "data" / "vault.db"


def run(db_path: Path = DEFAULT_DB) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        conn.commit()
        print(f"Migration applied: status column added to notes ({db_path})")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column already exists — skipping ({db_path})")
        else:
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    run(path)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
.venv/Scripts/python -m pytest tests/scripts/test__003_add_note_status.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/temp/_003_add_note_status.py tests/scripts/__init__.py \
        tests/scripts/test__003_add_note_status.py
git commit -m "feat: add migration _003 — status column on notes table"
```

---

## Task 2: Config — `auto_generate_note` in `LLMUserConfig` + tighten `Note.status` type

**Files:**
- Modify: `core/config.py:62-65` (LLMUserConfig)
- Modify: `core/schemas.py` (Note.status — tighten from `str` to `Literal`)

Note: A2 Task 2.5 adds `status: str = "active"` to `Note`. This task tightens it to `Literal["draft", "active"] = "active"` per spec §5. If A2 has not been applied yet, combine both changes here.

- [ ] **Step 1: Add `auto_generate_note` field to `LLMUserConfig`**

In `core/config.py`, update `LLMUserConfig`:

```python
class LLMUserConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3"
    auto_generate_note: bool = False
```

- [ ] **Step 2: Tighten `Note.status` to `Literal["draft", "active"]`**

In `core/schemas.py`, update the `Note` class. Find the `status` field (added in A2 Task 2.5) and change:
```python
status: str = "active"       # approval state: draft (auto-generated) | active (human-approved)
```
To:
```python
status: Literal["draft", "active"] = "active"
```

Make sure `Literal` is imported at the top of the file (it already is — used by `SubtitleResult`).

- [ ] **Step 3: Verify no existing tests break**

```bash
.venv/Scripts/python -m pytest tests/ -q --tb=short
```
Expected: all PASS — both fields have defaults, no existing config files need updating.

- [ ] **Step 4: Commit**

```bash
git add core/config.py core/schemas.py
git commit -m "feat: add auto_generate_note to LLMUserConfig, tighten Note.status to Literal"
```

---

## Task 3: `generate_note_from_source` tool (TDD)

**Files:**
- Create: `tools/vault/generate_note_from_source.py`
- Create: `tests/tools/vault/test_generate_note_from_source.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/vault/test_generate_note_from_source.py`:

```python
import pytest
import unittest.mock as mock
from unittest.mock import patch
from datetime import date
from core.schemas import Source, NoteContentInput, NoteResult


def _make_source(**overrides):
    data = {
        "uid": "src-1",
        "slug": "test-source",
        "source_type": "youtube",
        "status": "rag_ready",
        "title": "Test Source Title",
        "url": "https://youtube.com/watch?v=abc123",
        "author": None,
        "date_added": date.today().isoformat(),
        "date_source": None,
        "media_path": None,
        "transcript": "This is the test transcript content.",
        "raw_metadata": None,
    }
    data.update(overrides)
    return Source(**data)


def _make_content():
    return NoteContentInput(
        title="Generated Note Title",
        docstring="What this note is about. Short summary.",
        body="# Generated Note\n\nBody content here, enough text.",
        tags=["test-tag"],
        note_type=None,
        source_type=None,
    )


def _with_db(tmp_settings, tmp_db, tmp_path):
    settings = mock.MagicMock(wraps=tmp_settings)
    type(settings).vault_db_path = property(lambda self: tmp_db)
    type(settings).vault_path = property(lambda self: tmp_path)
    return settings


def test_generate_note_creates_draft(tmp_settings, tmp_db, tmp_path):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from infrastructure.db import insert_source, get_note

    insert_source(tmp_db, _make_source())
    settings = _with_db(tmp_settings, tmp_db, tmp_path)

    with patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768), \
         patch("infrastructure.llm_provider.generate_note_content", return_value=_make_content()):
        result = generate_note_from_source("src-1", settings)

    assert isinstance(result, NoteResult)
    assert result.note.status == "draft"
    assert result.note.source_uid == "src-1"
    assert result.note.generation_template == "standard"


def test_generate_note_note_is_searchable(tmp_settings, tmp_db, tmp_path):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from infrastructure.db import insert_source, search_notes

    insert_source(tmp_db, _make_source(uid="src-2", slug="src-2"))
    settings = _with_db(tmp_settings, tmp_db, tmp_path)

    with patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768), \
         patch("infrastructure.llm_provider.generate_note_content", return_value=_make_content()):
        result = generate_note_from_source("src-2", settings)

    hits = search_notes(tmp_db, [0.1] * 768, None, 5)
    note_uids = [h.note_uid for h in hits]
    assert result.note.uid in note_uids


def test_generate_note_not_found(tmp_settings, tmp_db, tmp_path):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from core.errors import NotFoundError

    settings = _with_db(tmp_settings, tmp_db, tmp_path)
    with pytest.raises(NotFoundError):
        generate_note_from_source("nonexistent", settings)


def test_generate_note_source_not_rag_ready(tmp_settings, tmp_db, tmp_path):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from infrastructure.db import insert_source

    insert_source(tmp_db, _make_source(uid="src-3", slug="src-3", status="raw"))
    settings = _with_db(tmp_settings, tmp_db, tmp_path)
    with pytest.raises(ValueError, match="rag_ready"):
        generate_note_from_source("src-3", settings)


def test_generate_note_conflict_if_note_exists(tmp_settings, tmp_db, tmp_path):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from infrastructure.db import insert_source, insert_note
    from core.schemas import Note
    from core.errors import ConflictError

    insert_source(tmp_db, _make_source(uid="src-4", slug="src-4"))
    existing = Note(
        uid="existing-note", source_uid="src-4", slug="existing-note",
        note_type=None, source_type=None, generation_template=None, rating=None,
        sync_status="synced", title="Existing Note", docstring="Already exists.",
        body="Body content here already.", url=None,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    insert_note(tmp_db, existing)
    settings = _with_db(tmp_settings, tmp_db, tmp_path)
    with pytest.raises(ConflictError):
        generate_note_from_source("src-4", settings)


def test_generate_note_custom_template(tmp_settings, tmp_db, tmp_path):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from infrastructure.db import insert_source

    insert_source(tmp_db, _make_source(uid="src-5", slug="src-5"))
    settings = _with_db(tmp_settings, tmp_db, tmp_path)

    with patch("infrastructure.embedding_provider.embed", return_value=[0.1] * 768), \
         patch("infrastructure.llm_provider.generate_note_content", return_value=_make_content()) as mock_gen:
        result = generate_note_from_source("src-5", settings, template="standard")

    assert result.note.generation_template == "standard"
    call_args = mock_gen.call_args
    assert call_args[0][2] == "standard"  # template arg
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_generate_note_from_source.py -v
```
Expected: FAIL — `tools/vault/generate_note_from_source` does not exist.

- [ ] **Step 3: Write the tool**

Create `tools/vault/generate_note_from_source.py`:

```python
"""
Generate a draft note from an ingested source via the configured LLM.

Input  : source_uid (str) + Settings + optional template name
Output : NoteResult with note.status == 'draft'

The note is immediately embedded and searchable. It must be approved
(status set to 'active') before the source is finalized as vaulted.
"""

import logging
from datetime import date

from core.config import Settings
from core.schemas import Note, NoteContentInput, NoteResult, NoteSystemFields
from core.uid import generate_uid, make_unique_slug

logger = logging.getLogger(__name__)


def generate_note_from_source(
    source_uid: str,
    settings: Settings,
    template: str = "standard",
) -> NoteResult:
    """
    Generate a draft note from an ingested source at rag_ready status.

    Calls the configured LLM to produce note content, creates the note as draft,
    and embeds it immediately so it is searchable. The note must be approved
    (status → active) before the source is finalized as vaulted.

    Raises NotFoundError if source_uid does not exist.
    Raises ValueError if source is not at rag_ready status.
    Raises ConflictError if a note already exists for this source.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import (
        get_source,
        get_note_by_source,
        get_note,
        get_vault_connection,
        insert_note,
        insert_note_embedding,
        update_note,
    )
    from infrastructure.embedding_provider import embed
    from infrastructure.llm_provider import generate_note_content
    from infrastructure.vault_writer import write_note

    db = settings.vault_db_path

    source = get_source(db, source_uid)
    if source is None:
        raise NotFoundError("Source", source_uid)

    if source.status != "rag_ready":
        raise ValueError(
            f"Source '{source_uid}' is not at rag_ready status (current: {source.status})"
        )

    if get_note_by_source(db, source_uid) is not None:
        raise ConflictError("Source", source_uid, "a note already exists for this source")

    metadata = {
        "title": source.title,
        "url": source.url,
        "author": source.author,
        "date_source": source.date_source,
        "source_type": source.source_type,
    }
    content_input = generate_note_content(
        source.transcript or "", metadata, template, settings
    )

    conn = get_vault_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM notes").fetchall()}
    conn.close()

    today = date.today().isoformat()
    system_fields = NoteSystemFields(
        uid=generate_uid(),
        date_created=today,
        source_uid=source_uid,
        slug=make_unique_slug(content_input.title, existing_slugs),
        generation_template=template,
    )

    note = Note(
        **system_fields.model_dump(),
        **content_input.model_dump(),
        date_modified=today,
        sync_status="synced",
    )
    insert_note(db, note)

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = embed(text, settings)
    insert_note_embedding(db, note.uid, embedding)

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(note, settings.vault_path)

    update_note(db, note.uid, {"status": "draft"})

    updated_note = get_note(db, note.uid)
    return NoteResult(note=updated_note, markdown_path=str(markdown_path))
```

- [ ] **Step 4: Run tests**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_generate_note_from_source.py -v
```
Expected: all PASS.

- [ ] **Step 5: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -q --tb=short
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/vault/generate_note_from_source.py \
        tests/tools/vault/test_generate_note_from_source.py
git commit -m "feat: add generate_note_from_source tool — creates draft note via LLM"
```

---

## Task 4: Workflow changes — `auto_generate_note` param (TDD)

**Files:**
- Modify: `workflows/ingest_youtube.py`
- Modify: `workflows/ingest_audio.py`
- Modify: `workflows/ingest_pdf.py`
- Modify: `tests/workflows/test_ingest_youtube.py`
- Modify: `tests/workflows/test_ingest_audio.py`
- Modify: `tests/workflows/test_ingest_pdf.py`

- [ ] **Step 1: Write failing tests for ingest_youtube**

Add to `tests/workflows/test_ingest_youtube.py`:

```python
from core.schemas import NoteResult, Note


def _make_note_result(source_uid="src-gen"):
    from datetime import date
    note = Note(
        uid="note-gen", source_uid=source_uid, slug="generated-note",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Generated", docstring="desc",
        body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    return NoteResult(note=note, markdown_path="/vault/generated-note.md")


def _make_settings_with_db(tmp_settings, tmp_db):
    return tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )


def test_ingest_youtube_auto_generate_true_creates_draft(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_youtube._llm_is_configured", return_value=True), \
         patch("workflows.ingest_youtube.generate_note_from_source",
               return_value=_make_note_result()) as mock_gen:

        result = ingest_youtube("https://youtube.com/watch?v=abc", settings,
                                auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_youtube_auto_generate_false_skips_note(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen:

        result = ingest_youtube("https://youtube.com/watch?v=skip", settings,
                                auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()


def test_ingest_youtube_auto_generate_none_reads_config_true(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)
    settings_with_flag = settings.model_copy(
        update={"user": settings.user.model_copy(
            update={"llm": settings.user.llm.model_copy(
                update={"auto_generate_note": True}
            )}
        )}
    )

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_youtube._llm_is_configured", return_value=True), \
         patch("workflows.ingest_youtube.generate_note_from_source",
               return_value=_make_note_result()) as mock_gen:

        result = ingest_youtube("https://youtube.com/watch?v=cfg", settings_with_flag,
                                auto_generate_note=None)

    mock_gen.assert_called_once()


def test_ingest_youtube_auto_generate_none_reads_config_false(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)
    # default is auto_generate_note=False

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen:

        ingest_youtube("https://youtube.com/watch?v=cfg2", settings,
                       auto_generate_note=None)

    mock_gen.assert_not_called()


def test_ingest_youtube_llm_not_configured_skips_note(tmp_settings, tmp_db, caplog):
    import logging
    from workflows.ingest_youtube import ingest_youtube

    settings = _make_settings_with_db(tmp_settings, tmp_db)

    with patch("workflows.ingest_youtube.fetch_subtitles", return_value=_make_subtitle_result()), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_youtube._llm_is_configured", return_value=False), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen, \
         caplog.at_level(logging.INFO, logger="workflows.ingest_youtube"):

        result = ingest_youtube("https://youtube.com/watch?v=nollm", settings,
                                auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
    assert any("LLM not configured" in r.message for r in caplog.records)


def test_ingest_youtube_large_format_skips_note_and_raises(tmp_settings, tmp_db):
    from workflows.ingest_youtube import ingest_youtube
    from core.errors import LargeFormatError

    settings = _make_settings_with_db(tmp_settings, tmp_db)
    big_text = " ".join(["word"] * 50001)

    with patch("workflows.ingest_youtube.fetch_subtitles",
               return_value=_make_subtitle_result(big_text)), \
         patch("workflows.ingest_youtube.chunk_text", return_value=[_make_chunk()]), \
         patch("workflows.ingest_youtube.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_youtube.generate_note_from_source") as mock_gen:

        with pytest.raises(LargeFormatError):
            ingest_youtube("https://youtube.com/watch?v=big3", settings,
                           auto_generate_note=True)

    mock_gen.assert_not_called()
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_youtube.py -v \
  -k "auto_generate or llm_not or large_format_skips"
```
Expected: FAIL — signature mismatch / missing import.

- [ ] **Step 3: Update `workflows/ingest_youtube.py`**

Replace the current file with the updated version. The diff:

1. Add imports at the top:
```python
import logging
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)
```

2. Add the `_llm_is_configured` helper after the imports:
```python
def _llm_is_configured(settings) -> bool:
    """Return True only if a supported LLM is configured with credentials."""
    if settings.user.llm.provider == "claude":
        return bool(settings.install.providers.anthropic_api_key)
    return False
```

3. Update the function signature:
```python
def ingest_youtube(url: str, settings: Settings, auto_generate_note: bool | None = None) -> Source:
```

4. After `update_source_status(db, source_uid, "rag_ready")` and before the large-format check, add the resolution logic:
```python
    should_generate = (
        auto_generate_note if auto_generate_note is not None
        else settings.user.llm.auto_generate_note
    )
```

5. Replace the end of the function:
```python
    if token_count > threshold:
        if should_generate:
            logger.info("Source exceeds token threshold, skipping note generation")
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    if should_generate:
        if not _llm_is_configured(settings):
            logger.info("LLM not configured, skipping note generation")
        else:
            generate_note_from_source(source_uid, settings)

    return get_source(db, source_uid)
```

The full updated file:

```python
"""
YouTube ingestion workflow.

Pipeline:
  fetch_subtitles → chunk_text → embed_chunks → [LLM → create_note → embed_note]

The LLM + note steps are skipped if:
  - No LLM configured (LLM-free mode) → source stays rag_ready
  - Source exceeds large_format_threshold_tokens → LargeFormatError raised

Status transitions managed here:
  raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
"""

import logging
import re
from datetime import date

from core.config import Settings
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from infrastructure.db import (
    get_vault_connection,
    get_source,
    insert_chunk_embeddings,
    insert_chunks,
    insert_source,
    update_source_status,
    update_source_transcript,
)
from tools.media.fetch_subtitles import fetch_subtitles
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL for slug generation."""
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else "unknown"


def _llm_is_configured(settings) -> bool:
    """Return True only if a supported LLM is configured with credentials."""
    if settings.user.llm.provider == "claude":
        return bool(settings.install.providers.anthropic_api_key)
    return False


def ingest_youtube(
    url: str,
    settings: Settings,
    auto_generate_note: bool | None = None,
) -> Source:
    """
    Run the full YouTube ingestion pipeline.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if source exceeds token threshold.
    If auto_generate_note resolves to True and LLM is configured, creates a draft note.
    """
    db = settings.vault_db_path
    today = date.today().isoformat()
    source_uid = generate_uid()
    video_id = _extract_video_id(url)

    conn = get_vault_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM sources").fetchall()}
    conn.close()

    slug = make_unique_slug(f"youtube-{video_id}", existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type="youtube",
        status="raw",
        url=url,
        date_added=today,
    )
    insert_source(db, source)

    # Step 1: Fetch subtitles
    update_source_status(db, source_uid, "transcribing")
    subtitle_result = fetch_subtitles(url, settings)
    update_source_transcript(db, source_uid, subtitle_result.text)
    update_source_status(db, source_uid, "text_ready")

    # Step 2: Check size — rough word-count estimate
    token_count = len(subtitle_result.text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    # Step 3: Chunk + embed regardless of size (source must reach rag_ready)
    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(subtitle_result.text, settings.system)
    insert_chunks(db, source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, settings)
        insert_chunk_embeddings(db, chunk.uid, embedding)

    update_source_status(db, source_uid, "rag_ready")

    should_generate = (
        auto_generate_note if auto_generate_note is not None
        else settings.user.llm.auto_generate_note
    )

    if token_count > threshold:
        if should_generate:
            logger.info("Source exceeds token threshold, skipping note generation")
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    if should_generate:
        if not _llm_is_configured(settings):
            logger.info("LLM not configured, skipping note generation")
        else:
            generate_note_from_source(source_uid, settings)

    return get_source(db, source_uid)
```

- [ ] **Step 4: Run youtube workflow tests**

```bash
.venv/Scripts/python -m pytest tests/workflows/test_ingest_youtube.py -v
```
Expected: all PASS.

- [ ] **Step 5: Apply identical changes to `ingest_audio.py`**

In `workflows/ingest_audio.py`:
1. Add `import logging` and `from tools.vault.generate_note_from_source import generate_note_from_source`
2. Add `logger = logging.getLogger(__name__)`
3. Add `_llm_is_configured` helper (identical to the one in ingest_youtube.py)
4. Update function signature: `def ingest_audio(path: str, settings: Settings, auto_generate_note: bool | None = None) -> Source:`
5. After `update_source_status(db, source_uid, "rag_ready")`, add `should_generate` resolution:
```python
    should_generate = (
        auto_generate_note if auto_generate_note is not None
        else settings.user.llm.auto_generate_note
    )
```
6. Replace the large-format check and final return with the same pattern as ingest_youtube.

- [ ] **Step 6: Add auto_generate_note tests to `test_ingest_audio.py`**

Add to `tests/workflows/test_ingest_audio.py` (read the existing test file first to match helper patterns):

```python
def test_ingest_audio_auto_generate_true_creates_draft(tmp_settings, tmp_db):
    from workflows.ingest_audio import ingest_audio
    from core.schemas import NoteResult, Note
    from datetime import date

    def _make_audio_note_result():
        note = Note(
            uid="note-audio", source_uid="audio-src", slug="audio-note",
            note_type=None, source_type=None, generation_template="standard",
            rating=None, sync_status="synced", title="Audio Note",
            docstring="Audio note desc.", body="Audio note body content.",
            url=None, status="draft",
            date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
            tags=["test-tag"],
        )
        return NoteResult(note=note, markdown_path="/vault/audio-note.md")

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )

    with patch("workflows.ingest_audio.compress_audio",
               return_value=MagicMock(output_path="/tmp/compressed.opus")), \
         patch("workflows.ingest_audio.transcribe",
               return_value=MagicMock(text="audio transcript here")), \
         patch("workflows.ingest_audio.chunk_text", return_value=[MagicMock(
             uid="c1", position=0, content="chunk", token_count=3)]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_audio._llm_is_configured", return_value=True), \
         patch("workflows.ingest_audio.generate_note_from_source",
               return_value=_make_audio_note_result()) as mock_gen:

        result = ingest_audio("/tmp/test.mp3", settings, auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_audio_auto_generate_false_skips_note(tmp_settings, tmp_db):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )

    with patch("workflows.ingest_audio.compress_audio",
               return_value=MagicMock(output_path="/tmp/compressed.opus")), \
         patch("workflows.ingest_audio.transcribe",
               return_value=MagicMock(text="audio transcript here")), \
         patch("workflows.ingest_audio.chunk_text", return_value=[MagicMock(
             uid="c1", position=0, content="chunk", token_count=3)]), \
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768), \
         patch("workflows.ingest_audio.generate_note_from_source") as mock_gen:

        result = ingest_audio("/tmp/test.mp3", settings, auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
```

- [ ] **Step 7: Apply identical changes to `ingest_pdf.py`**

Same pattern as ingest_audio. Read `workflows/ingest_pdf.py` first to match existing helper names and patch paths.

- [ ] **Step 8: Add matching tests to `test_ingest_pdf.py`**

Same pattern as test_ingest_audio — two tests: `auto_generate_true_creates_draft` and `auto_generate_false_skips_note`. Read existing test file for helper/patch patterns.

- [ ] **Step 9: Run all workflow tests**

```bash
.venv/Scripts/python -m pytest tests/workflows/ -v
```
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add workflows/ingest_youtube.py workflows/ingest_audio.py workflows/ingest_pdf.py \
        tests/workflows/test_ingest_youtube.py tests/workflows/test_ingest_audio.py \
        tests/workflows/test_ingest_pdf.py
git commit -m "feat: add auto_generate_note param to all ingest workflows"
```

---

## Task 5: API changes

**Files:**
- Modify: `api/models.py`
- Modify: `api/routers/notes.py`
- Modify: `api/routers/sources.py`
- Modify: `api/routers/ingest.py`
- Create: `tests/api/test_notes_approve.py`
- Create: `tests/api/test_sources_generate_note.py`

- [ ] **Step 1: Update `api/models.py`**

Three changes:

1. Add `status: str = "active"` to `NoteDetail`:
```python
class NoteDetail(BaseModel):
    uid: str
    slug: str
    title: str
    body: str
    note_type: str | None
    source_type: str | None
    rating: int | None
    tags: list[str]
    date_created: str
    date_modified: str
    status: str = "active"
```

2. Add `status` to `NotePatch`:
```python
class NotePatch(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    tags: list[str] | None = None
    status: str | None = None
```

3. Add `auto_generate_note` to `IngestYoutubeRequest`:
```python
class IngestYoutubeRequest(BaseModel):
    url: str
    auto_generate_note: bool | None = None
```

- [ ] **Step 2: Write failing tests for `POST /notes/{uid}/approve`**

Create `tests/api/test_notes_approve.py`:

```python
import pytest
from core.schemas import Note, Source
from infrastructure.db import insert_note, insert_source
from datetime import date


def _make_note(uid: str, slug: str, status: str = "draft", source_uid: str | None = None):
    return Note(
        uid=uid, source_uid=source_uid, slug=slug, note_type=None,
        source_type=None, generation_template="standard", rating=None,
        sync_status="synced", title=f"Note {uid}", docstring="A short description.",
        body="# Title\n\nBody content here.", url=None, status=status,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )


def _make_source(uid: str, status: str = "rag_ready"):
    return Source(
        uid=uid, slug=uid, source_type="youtube", status=status,
        url="https://example.com", title=f"Source {uid}",
        date_added=date.today().isoformat(),
    )


@pytest.fixture(scope="module", autouse=True)
def seed(tmp_settings):
    # draft note with linked rag_ready source
    insert_source(tmp_settings.vault_db_path, _make_source("approve-src-1"))
    insert_note(tmp_settings.vault_db_path,
                _make_note("approve-note-1", "approve-note-1", "draft", "approve-src-1"))
    # draft note without source
    insert_note(tmp_settings.vault_db_path,
                _make_note("approve-note-2", "approve-note-2", "draft"))
    # active note (not draft)
    insert_note(tmp_settings.vault_db_path,
                _make_note("approve-note-3", "approve-note-3", "active"))


def test_approve_draft_note_with_source(client, tmp_settings):
    from infrastructure.db import get_note, get_source
    response = client.post("/notes/approve-note-1/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    # source should be finalized
    source = get_source(tmp_settings.vault_db_path, "approve-src-1")
    assert source.status == "vaulted"


def test_approve_draft_note_without_source(client):
    response = client.post("/notes/approve-note-2/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_approve_not_found(client):
    response = client.post("/notes/nonexistent-uid/approve")
    assert response.status_code == 404


def test_approve_already_active_returns_409(client):
    response = client.post("/notes/approve-note-3/approve")
    assert response.status_code == 409
```

- [ ] **Step 3: Write failing tests for `POST /sources/{uid}/generate-note`**

Create `tests/api/test_sources_generate_note.py`:

Note: the router uses a local import `from tools.vault.generate_note_from_source import generate_note_from_source`, so patch at `tools.vault.generate_note_from_source.generate_note_from_source` or mock the infrastructure calls. These tests mock at the LLM/embedding infrastructure level for success cases and use natural DB state for error cases.

```python
import pytest
from unittest.mock import patch
from core.schemas import NoteContentInput, Source
from infrastructure.db import insert_source, insert_note, get_note
from core.schemas import Note
from datetime import date


def _make_content():
    return NoteContentInput(
        title="Generated Note Title",
        docstring="What this note is about.",
        body="# Generated Note\n\nBody content here, enough text.",
        tags=["test-tag"],
        note_type=None,
        source_type=None,
    )


@pytest.fixture(scope="module", autouse=True)
def seed(tmp_settings):
    db = tmp_settings.vault_db_path
    # rag_ready source — happy path
    if not _src_exists(db, "gen-src-1"):
        insert_source(db, Source(
            uid="gen-src-1", slug="gen-src-1", source_type="youtube",
            status="rag_ready", url="https://example.com",
            title="Source For Generation",
            transcript="This is a test transcript long enough.",
            date_added=date.today().isoformat(),
        ))
    # raw source — not rag_ready
    if not _src_exists(db, "gen-src-raw"):
        insert_source(db, Source(
            uid="gen-src-raw", slug="gen-src-raw", source_type="youtube",
            status="raw", date_added=date.today().isoformat(),
        ))
    # source with existing note — conflict
    if not _src_exists(db, "gen-src-conflict"):
        insert_source(db, Source(
            uid="gen-src-conflict", slug="gen-src-conflict",
            source_type="youtube", status="rag_ready",
            transcript="Transcript.", date_added=date.today().isoformat(),
        ))
        insert_note(db, Note(
            uid="note-for-conflict", source_uid="gen-src-conflict",
            slug="note-for-conflict", note_type=None, source_type=None,
            generation_template=None, rating=None, sync_status="synced",
            title="Existing Note", docstring="Already exists.",
            body="Body content here.", url=None,
            date_created=date.today().isoformat(),
            date_modified=date.today().isoformat(),
            tags=["test-tag"],
        ))


def _src_exists(db, uid):
    from infrastructure.db import get_source
    return get_source(db, uid) is not None


def test_generate_note_from_source_success(client, tmp_settings):
    vault_path = tmp_settings.vault_path
    vault_path.mkdir(parents=True, exist_ok=True)

    with patch("infrastructure.llm_provider.generate_note_content",
               return_value=_make_content()), \
         patch("infrastructure.embedding_provider.embed",
               return_value=[0.1] * 768):
        response = client.post("/sources/gen-src-1/generate-note")

    assert response.status_code == 200
    data = response.json()
    assert data["note"]["status"] == "draft"
    assert data["note"]["source_uid"] == "gen-src-1"


def test_generate_note_source_not_found(client):
    response = client.post("/sources/nonexistent-gen/generate-note")
    assert response.status_code == 404


def test_generate_note_source_not_rag_ready_422(client):
    # gen-src-raw exists but status is "raw"
    response = client.post("/sources/gen-src-raw/generate-note")
    assert response.status_code == 422


def test_generate_note_conflict_409(client, tmp_settings):
    # gen-src-conflict already has a note — ConflictError from tool → 409
    response = client.post("/sources/gen-src-conflict/generate-note")
    assert response.status_code == 409


def test_generate_note_template_param(client, tmp_settings):
    # Use a second rag_ready source to avoid conflict with gen-src-1
    db = tmp_settings.vault_db_path
    if not _src_exists(db, "gen-src-tpl"):
        insert_source(db, Source(
            uid="gen-src-tpl", slug="gen-src-tpl", source_type="youtube",
            status="rag_ready", transcript="Transcript.",
            date_added=date.today().isoformat(),
        ))
    vault_path = tmp_settings.vault_path
    vault_path.mkdir(parents=True, exist_ok=True)

    with patch("infrastructure.llm_provider.generate_note_content",
               return_value=_make_content()) as mock_gen, \
         patch("infrastructure.embedding_provider.embed",
               return_value=[0.1] * 768):
        response = client.post("/sources/gen-src-tpl/generate-note?template=standard")

    assert response.status_code == 200
    # Verify template was forwarded to the LLM call
    call_args = mock_gen.call_args
    assert call_args[0][2] == "standard"  # positional: (transcript, metadata, template, settings)
```

- [ ] **Step 4: Run failing tests**

```bash
.venv/Scripts/python -m pytest tests/api/test_notes_approve.py tests/api/test_sources_generate_note.py -v
```
Expected: FAIL — endpoints do not exist yet.

- [ ] **Step 5: Update `api/routers/notes.py`**

1. Update `_to_detail` to include `status`:
```python
def _to_detail(note) -> NoteDetail:
    return NoteDetail(
        uid=note.uid, slug=note.slug, title=note.title,
        body=note.body, note_type=note.note_type,
        source_type=note.source_type, rating=note.rating,
        tags=note.tags, date_created=note.date_created,
        date_modified=note.date_modified,
        status=note.status,
    )
```

2. Update `patch_note` to handle `status`:
```python
@router.patch("/{uid}", response_model=NoteDetail)
def patch_note(uid: str, patch: NotePatch, request: Request):
    db = request.app.state.settings.vault_db_path
    if get_note(db, uid) is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")

    from datetime import date
    fields: dict = {}
    if patch.rating is not None:
        fields["rating"] = patch.rating
    if patch.tags is not None:
        set_note_tags(db, uid, patch.tags)
    if patch.status is not None:
        fields["status"] = patch.status
    if fields:
        fields["date_modified"] = date.today().isoformat()
        update_note(db, uid, fields)

    updated = get_note(db, uid)
    return _to_detail(updated)
```

3. Add the `approve` endpoint (add after `patch_note`):
```python
@router.post("/{uid}/approve", response_model=NoteDetail)
def approve_note(uid: str, request: Request):
    """Approve a draft note and finalize its linked source if applicable."""
    db = request.app.state.settings.vault_db_path
    settings = request.app.state.settings

    note = get_note(db, uid)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    if note.status != "draft":
        raise HTTPException(status_code=409,
                            detail=f"Note '{uid}' is not in draft status")

    from tools.vault.update_note import update_note as _update_note_tool
    _update_note_tool(uid, {"status": "active"}, settings)

    if note.source_uid:
        from infrastructure.db import get_source
        source = get_source(db, note.source_uid)
        if source and source.status == "rag_ready":
            from tools.vault.finalize_source import finalize_source
            finalize_source(note.source_uid, settings)

    updated = get_note(db, uid)
    return _to_detail(updated)
```

- [ ] **Step 6: Update `api/routers/sources.py`**

Add the generate-note endpoint (add after `get_source_by_uid`):

```python
@router.post("/{uid}/generate-note")
def generate_note_from_source_endpoint(
    uid: str,
    request: Request,
    template: str = "standard",
):
    """Generate a draft note from an ingested source at rag_ready status."""
    from tools.vault.generate_note_from_source import generate_note_from_source
    from core.errors import NotFoundError, ConflictError

    settings = request.app.state.settings
    try:
        result = generate_note_from_source(uid, settings, template=template)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Source '{uid}' not found")
    except ValueError:
        raise HTTPException(status_code=422,
                            detail=f"Source '{uid}' is not at rag_ready status")
    except ConflictError:
        raise HTTPException(status_code=409,
                            detail=f"A note already exists for source '{uid}'")
    return result.model_dump(mode="json")
```

- [ ] **Step 7: Update `api/routers/ingest.py`**

1. Update `_run_youtube` to accept and pass `auto_generate_note`:
```python
def _run_youtube(job_id: str, url: str, settings, auto_generate_note=None) -> None:
    from workflows.ingest_youtube import ingest_youtube
    system_db = settings.system_db_path
    try:
        update_job_status(system_db, job_id, "running")
        result = ingest_youtube(url, settings, auto_generate_note=auto_generate_note)
        update_job_done(system_db, job_id, {"note_uid": None, "slug": result.slug})
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))
```

2. Same for `_run_audio` and `_run_pdf`.

3. Update `ingest_youtube_endpoint`:
```python
@router.post("/youtube", status_code=202, response_model=IngestResponse)
def ingest_youtube_endpoint(body: IngestYoutubeRequest, request: Request):
    video_id = validate_youtube_url(body.url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="invalid youtube url")
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    settings = request.app.state.settings
    executor = request.app.state.executor
    job_id = generate_uid()
    insert_job(settings.system_db_path, job_id, "youtube", {"url": canonical_url})
    _submit_job(executor, _run_youtube, job_id, canonical_url, settings,
                body.auto_generate_note)
    return IngestResponse(job_id=job_id)
```

4. Update `ingest_audio_endpoint` and `ingest_pdf_endpoint` to add `auto_generate_note: bool | None = None` as a `Query` parameter and pass it through:
```python
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query

@router.post("/audio", status_code=202, response_model=IngestResponse)
async def ingest_audio_endpoint(
    request: Request,
    file: UploadFile = File(...),
    auto_generate_note: bool | None = Query(None),
):
    # ... existing file handling unchanged ...
    _submit_job(executor, _run_audio, job_id, dest, settings, auto_generate_note)
    return IngestResponse(job_id=job_id)
```

- [ ] **Step 8: Run API tests**

```bash
.venv/Scripts/python -m pytest tests/api/test_notes_approve.py \
        tests/api/test_sources_generate_note.py -v
```
Expected: all PASS.

- [ ] **Step 9: Run full API test suite**

```bash
.venv/Scripts/python -m pytest tests/api/ -v
```
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add api/models.py api/routers/notes.py api/routers/sources.py api/routers/ingest.py \
        tests/api/test_notes_approve.py tests/api/test_sources_generate_note.py
git commit -m "feat: add approve endpoint, generate-note endpoint, auto_generate_note to ingest API"
```

---

## Task 6: CLI changes

**Files:**
- Modify: `cli/commands/sources.py`
- Modify: `cli/commands/ingest.py`

Tests for CLI commands in this task use the pattern from existing `tests/cli/` tests. Read `tests/cli/test_sources.py` and `tests/cli/test_ingest.py` before writing to match helper and fixture patterns exactly.

- [ ] **Step 1: Read existing CLI test files**

```bash
.venv/Scripts/python -m pytest tests/cli/ --collect-only -q
```
Run this to see what tests already exist, then read `tests/cli/test_sources.py` and `tests/cli/test_ingest.py` to understand the helper patterns.

- [ ] **Step 2: Write failing tests for `source generate-note`**

Add to `tests/cli/test_sources.py` (or a new `tests/cli/test_sources_generate_note.py` if the existing file is large — check first):

```python
def test_source_generate_note_success():
    from core.schemas import Note, NoteResult
    from datetime import date

    note = Note(
        uid="note-gen", source_uid="src-gen", slug="gen-note",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Generated Note",
        docstring="desc", body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    note_result = NoteResult(note=note, markdown_path="/vault/gen-note.md")

    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._generate_note_from_source",
               return_value=note_result) as mock_gen:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["generate-note", "src-gen"])

    assert result.exit_code == 0
    mock_gen.assert_called_once()


def test_source_generate_note_not_found():
    from core.errors import NotFoundError
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._generate_note_from_source",
               side_effect=NotFoundError("Source", "bad-uid")):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["generate-note", "bad-uid"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_source_generate_note_json_mode():
    from core.schemas import Note, NoteResult
    from datetime import date

    note = Note(
        uid="note-gen2", source_uid="src-gen2", slug="gen-note2",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Generated Note 2",
        docstring="desc", body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    note_result = NoteResult(note=note, markdown_path="/vault/gen-note2.md")

    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._generate_note_from_source",
               return_value=note_result):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["generate-note", "src-gen2", "--json"])

    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "note" in data
```

- [ ] **Step 3: Run failing tests**

```bash
.venv/Scripts/python -m pytest tests/cli/ -v -k "generate_note"
```
Expected: FAIL.

- [ ] **Step 4: Add `source generate-note` to `cli/commands/sources.py`**

Add helper after `_get_source`:
```python
def _generate_note_from_source(source_uid, settings, template="standard"):
    from tools.vault.generate_note_from_source import generate_note_from_source
    return generate_note_from_source(source_uid, settings, template=template)
```

Add command after `source_get`:
```python
@app.command("generate-note")
def source_generate_note(
    uid: Annotated[str, typer.Argument(help="Source UID")],
    template: Annotated[str, typer.Option("--template",
                        help="Generation template name")] = "standard",
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Generate a draft note from an ingested source via the configured LLM."""
    from core.errors import NotFoundError, ConflictError

    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _generate_note_from_source(uid, settings, template=template)
    except NotFoundError:
        print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)
    except ConflictError:
        print_error(f"A note already exists for source: {uid}", "conflict",
                    json_mode, verbose)
        raise typer.Exit(1)
    except Exception as e:
        print_error("Note generation failed.", "generation_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    fields: dict = {
        "note_uid": result.note.uid,
        "slug": result.note.slug,
        "status": result.note.status,
        "template": result.note.generation_template,
    }
    if verbose:
        fields["markdown_path"] = result.markdown_path

    if json_mode:
        import json
        print(json.dumps(result.model_dump(mode="json")))
    else:
        print_panel("Draft note generated", fields, json_mode)
```

- [ ] **Step 5: Run source CLI tests**

```bash
.venv/Scripts/python -m pytest tests/cli/ -v -k "generate_note"
```
Expected: all PASS.

- [ ] **Step 6: Write failing tests for ingest `--generate-note` flag**

Add to `tests/cli/test_ingest.py`:

```python
def test_ingest_generate_note_flag_passed_to_workflow():
    """--generate-note passes auto_generate_note=True to the workflow."""
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-ingest-gen", slug="youtube-abc", source_type="youtube",
        status="rag_ready", url="https://youtube.com/watch?v=abc",
        date_added=date.today().isoformat(),
    )
    with patch("cli.commands.ingest._load_settings") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(
            app, ["https://youtube.com/watch?v=abc", "--generate-note"]
        )

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args
    assert call_kwargs[1].get("auto_generate_note") is True or \
           (len(call_kwargs[0]) > 3 and call_kwargs[0][3] is True)


def test_ingest_no_generate_note_flag_passed():
    """--no-generate-note passes auto_generate_note=False to the workflow."""
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-ingest-nogen", slug="youtube-nogen", source_type="youtube",
        status="rag_ready", url="https://youtube.com/watch?v=nogen",
        date_added=date.today().isoformat(),
    )
    with patch("cli.commands.ingest._load_settings") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(
            app, ["https://youtube.com/watch?v=nogen", "--no-generate-note"]
        )

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args
    assert call_kwargs[1].get("auto_generate_note") is False or \
           (len(call_kwargs[0]) > 3 and call_kwargs[0][3] is False)


def test_ingest_no_flag_passes_none():
    """No flag passes auto_generate_note=None (read from config)."""
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-ingest-cfg", slug="youtube-cfg", source_type="youtube",
        status="rag_ready", url="https://youtube.com/watch?v=cfg",
        date_added=date.today().isoformat(),
    )
    with patch("cli.commands.ingest._load_settings") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["https://youtube.com/watch?v=cfg"])

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args
    auto = call_kwargs[1].get("auto_generate_note", call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None)
    assert auto is None
```

- [ ] **Step 7: Run failing ingest tests**

```bash
.venv/Scripts/python -m pytest tests/cli/test_ingest.py -v -k "generate_note"
```
Expected: FAIL.

- [ ] **Step 8: Update `cli/commands/ingest.py`**

1. Update `_run_ingest` to accept and pass `auto_generate_note`:
```python
def _run_ingest(input_type: str, target: str, settings, auto_generate_note=None):
    if input_type == "youtube":
        from workflows.ingest_youtube import ingest_youtube
        return ingest_youtube(target, settings, auto_generate_note=auto_generate_note)
    elif input_type == "audio":
        from workflows.ingest_audio import ingest_audio
        return ingest_audio(target, settings, auto_generate_note=auto_generate_note)
    else:
        from workflows.ingest_pdf import ingest_pdf
        return ingest_pdf(target, settings, auto_generate_note=auto_generate_note)
```

2. Update the `ingest` command signature to add the flag:
```python
@app.command()
def ingest(
    target: Annotated[str, typer.Argument(help="YouTube URL or path to audio/PDF file")],
    generate_note: Annotated[
        bool | None,
        typer.Option("--generate-note/--no-generate-note",
                     help="Generate a draft note after ingestion. Default: reads user.yaml.")
    ] = None,
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose",
                       help="Show step timings and details")] = False,
) -> None:
```

3. Update the `_run_ingest` call inside the `ingest` function:
```python
        with spinner(f"Ingesting {input_type}..."):
            source = _run_ingest(input_type, target, settings,
                                 auto_generate_note=generate_note)
```

- [ ] **Step 9: Run CLI tests**

```bash
.venv/Scripts/python -m pytest tests/cli/ -v
```
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add cli/commands/sources.py cli/commands/ingest.py \
        tests/cli/test_sources.py tests/cli/test_ingest.py
git commit -m "feat: add source generate-note command and --generate-note flag to ingest"
```

---

## Task 7: MCP — `generate_note_from_source` tool + workflow guide update

**Files:**
- Modify: `mcp/server.py`

- [ ] **Step 1: Add import and tool to `mcp/server.py`**

Add import near the other tool imports at the top of `mcp/server.py`:
```python
from tools.vault.generate_note_from_source import generate_note_from_source as _generate_note_from_source_tool
```

Add the tool after `update_note`:
```python
@mcp.tool()
def generate_note_from_source(source_uid: str, template: str = "standard") -> dict:
    """
    Generate a draft note from an ingested source.

    The source must be at rag_ready status. The configured LLM generates
    note content automatically. The note is created as draft — it must be
    reviewed and approved before the source is finalized.

    When to use: After a source has been ingested and indexed (rag_ready status),
    to automatically generate a note draft without composing content manually.
    Use list_sources(status='rag_ready') to find candidates.

    What to call next: get_note(uid) to review the draft, then
    update_note(uid, {'status': 'active'}) to approve it, then
    finalize_source(source_uid) to archive the source.
    """
    result = _generate_note_from_source_tool(source_uid, settings, template)
    return result.model_dump(mode="json")
```

- [ ] **Step 2: Update `get_workflow_guide` in `mcp/server.py`**

In the `get_workflow_guide` function, update the return string to add the internal path section. Append after the existing workflow text (before the closing `"""`):

```python
## Internal path: automatic note generation

If auto_generate_note is configured in user.yaml, draft notes are created
automatically after ingestion. To generate a note on demand:

1. generate_note_from_source(source_uid) → draft note created automatically
2. get_note(uid) → review the draft content
3. update_note(uid, {'status': 'active'}) → approve the note
4. finalize_source(source_uid) → archive the source as vaulted

## Draft note approval (manual MCP workflow)

After reviewing a draft note:
1. update_note(uid, {'status': 'active'}) → mark as approved
2. finalize_source(source_uid) → archive the linked source
```

- [ ] **Step 3: Write MCP tool test**

Add to `tests/mcp/test_server.py`:

```python
def test_mcp_generate_note_from_source_calls_tool(tmp_settings):
    import mcp.server as srv
    from core.schemas import NoteResult, Note
    from datetime import date

    note = Note(
        uid="note-mcp", source_uid="src-mcp", slug="note-mcp",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="MCP Note",
        docstring="desc", body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    mock_result = NoteResult(note=note, markdown_path="/vault/note-mcp.md")

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._generate_note_from_source_tool",
               return_value=mock_result) as mock_tool:
        result = srv.generate_note_from_source("src-mcp")

    mock_tool.assert_called_once_with("src-mcp", tmp_settings, "standard")
    assert result["note"]["status"] == "draft"
```

- [ ] **Step 4: Run MCP tests**

```bash
.venv/Scripts/python -m pytest tests/mcp/ -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp/server.py tests/mcp/test_server.py
git commit -m "feat: add generate_note_from_source MCP tool and update workflow guide"
```

---

## Task 8: Final smoke test and full suite

- [ ] **Step 1: Run the migration against a real DB (if available)**

If you have a local `vault.db`, run:
```bash
.venv/Scripts/python scripts/temp/_003_add_note_status.py
```
Expected: `Migration applied: status column added to notes`.

If re-run:
Expected: `Column already exists — skipping`.

- [ ] **Step 2: Run the full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short
```
Expected: all PASS (259+ tests + new A4 tests).

- [ ] **Step 3: Manual CLI smoke test**

```bash
.venv/Scripts/python -m cli.main source --help
.venv/Scripts/python -m cli.main source generate-note --help
.venv/Scripts/python -m cli.main ingest --help
```
Expected: `generate-note` appears in source subcommands. `--generate-note/--no-generate-note` appears in ingest help.

- [ ] **Step 4: Final commit if any fixups needed**

```bash
git add -p
git commit -m "chore: A4 internal LLM path — fixups"
```

---

## Deferred / covered elsewhere

- `egovault note approve <uid>` — **implemented in A2 plan Task 5**, not re-implemented here
- `egovault note list --status draft` / `note update --status active` **fully** operational after migration _003 runs (wired in A2)
- MCP approval flow — no new tool needed; workflow guide update in Task 7 covers it (use `update_note(uid, {status: active})` + `finalize_source`)
- `tools/text/summarize.py` — remains an unimplemented stub, not part of A4
- Large-format handling beyond the `logger.info` skip
- Batch note generation workflow
