import pytest
from datetime import date
from unittest.mock import patch

from tests.conftest import make_embedding

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
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
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
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
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
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
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
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
        system = _system_fields()
        create_note(_content(), system, tmp_settings)

    results = search_notes(tmp_db, make_embedding(), None, 5)
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
