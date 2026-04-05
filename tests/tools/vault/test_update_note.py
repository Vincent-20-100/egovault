import pytest
from datetime import date

from tests.conftest import make_embedding

from core.schemas import NoteContentInput, NoteSystemFields
from core.uid import generate_uid
from core.errors import NotFoundError


def _insert_test_note(ctx):
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
    result = create_note(content, system, ctx)
    return result.note.uid


def test_update_note_returns_note_result(ctx):
    from tools.vault.update_note import update_note
    from core.schemas import NoteResult

    uid = _insert_test_note(ctx)
    result = update_note(uid, {"rating": 5}, ctx)

    assert isinstance(result, NoteResult)
    assert result.note.rating == 5


def test_update_note_re_embeds_note(ctx):
    """After update, note must be re-embedded and sync_status must be 'synced'."""
    from tools.vault.update_note import update_note
    from infrastructure.db import search_notes

    uid = _insert_test_note(ctx)
    result = update_note(uid, {"body": "Updated body content here."}, ctx)

    assert result.note.sync_status == "synced"
    results = search_notes(ctx.db._db_path, make_embedding(0.0), None, 5)
    assert any(r.note_uid == uid for r in results)


def test_update_note_ignores_system_fields(ctx):
    from tools.vault.update_note import update_note

    uid = _insert_test_note(ctx)
    original_uid = uid

    update_note(uid, {"uid": "new-uid", "date_created": "2000-01-01"}, ctx)
    note = ctx.db.get_note(original_uid)

    assert note is not None
    assert note.date_created != "2000-01-01"


def test_update_note_not_found_raises(ctx):
    from tools.vault.update_note import update_note

    with pytest.raises(NotFoundError):
        update_note("nonexistent-uid", {"rating": 3}, ctx)
