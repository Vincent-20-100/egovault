import pytest
from datetime import date
from unittest.mock import patch
from core.schemas import NoteContentInput, NoteSystemFields
from core.uid import generate_uid
from core.errors import NotFoundError
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
        with pytest.raises(NotFoundError):
            update_note("nonexistent-uid", {"rating": 3}, tmp_settings)
