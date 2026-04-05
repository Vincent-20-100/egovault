import pytest
import unittest.mock as mock
from unittest.mock import patch
from datetime import date

from tests.conftest import make_embedding

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

    with patch("infrastructure.embedding_provider.embed", return_value=make_embedding()), \
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

    with patch("infrastructure.embedding_provider.embed", return_value=make_embedding()), \
         patch("infrastructure.llm_provider.generate_note_content", return_value=_make_content()):
        result = generate_note_from_source("src-2", settings)

    hits = search_notes(tmp_db, make_embedding(), None, 5)
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

    with patch("infrastructure.embedding_provider.embed", return_value=make_embedding()), \
         patch("infrastructure.llm_provider.generate_note_content", return_value=_make_content()) as mock_gen:
        result = generate_note_from_source("src-5", settings, template="standard")

    assert result.note.generation_template == "standard"
    call_args = mock_gen.call_args
    assert call_args[0][2] == "standard"  # template arg
