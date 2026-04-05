import pytest
from datetime import date

from tests.conftest import make_embedding, EMBEDDING_DIMS
from core.schemas import Note, EmbedNoteResult


def _insert_test_note(ctx):
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
    ctx.db.insert_note(note)
    return note


def test_embed_note_returns_result(ctx):
    from tools.text.embed_note import embed_note

    _insert_test_note(ctx)
    result = embed_note("n1", ctx)

    assert isinstance(result, EmbedNoteResult)
    assert result.note_uid == "n1"
    assert result.embedding_dim == EMBEDDING_DIMS


def test_embed_note_populates_notes_vec(ctx):
    from tools.text.embed_note import embed_note

    _insert_test_note(ctx)
    embed_note("n1", ctx)

    results = ctx.db.search_notes(make_embedding(), None, 5)
    assert len(results) == 1
    assert results[0].note_uid == "n1"


def test_embed_note_replaces_existing_embedding(ctx):
    """Calling embed_note twice must not create duplicate rows in notes_vec."""
    from tools.text.embed_note import embed_note

    _insert_test_note(ctx)
    embed_note("n1", ctx)
    embed_note("n1", ctx)  # second call — must not duplicate

    results = ctx.db.search_notes(make_embedding(), None, 10)
    assert len(results) == 1


def test_embed_note_sets_sync_status_synced(ctx):
    from tools.text.embed_note import embed_note

    _insert_test_note(ctx)
    embed_note("n1", ctx)

    note = ctx.db.get_note("n1")
    assert note.sync_status == "synced"


def test_embed_note_not_found_raises(ctx):
    from tools.text.embed_note import embed_note

    with pytest.raises(ValueError, match="not found"):
        embed_note("nonexistent", ctx)
