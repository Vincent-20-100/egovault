import pytest
import unittest.mock as mock
from unittest.mock import patch
from datetime import date

from tests.conftest import make_embedding, EMBEDDING_DIMS

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
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
        result = embed_note("n1", tmp_settings)

    assert isinstance(result, EmbedNoteResult)
    assert result.note_uid == "n1"
    assert result.embedding_dim == EMBEDDING_DIMS


def test_embed_note_populates_notes_vec(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note
    from infrastructure.db import search_notes

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
        embed_note("n1", tmp_settings)

    results = search_notes(tmp_db, make_embedding(), None, 5)
    assert len(results) == 1
    assert results[0].note_uid == "n1"


def test_embed_note_replaces_existing_embedding(tmp_settings, tmp_db):
    """Calling embed_note twice must not create duplicate rows in notes_vec."""
    from tools.text.embed_note import embed_note
    from infrastructure.db import search_notes

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
        embed_note("n1", tmp_settings)
        embed_note("n1", tmp_settings)  # second call — must not duplicate

    results = search_notes(tmp_db, make_embedding(), None, 10)
    assert len(results) == 1


def test_embed_note_sets_sync_status_synced(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note
    from infrastructure.db import get_note

    _insert_test_note(tmp_db)

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
        embed_note("n1", tmp_settings)

    note = get_note(tmp_db, "n1")
    assert note.sync_status == "synced"


def test_embed_note_not_found_raises(tmp_settings, tmp_db):
    from tools.text.embed_note import embed_note

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)):
        with pytest.raises(ValueError, match="not found"):
            embed_note("nonexistent", tmp_settings)
