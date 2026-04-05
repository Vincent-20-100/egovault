import pytest
from datetime import date

from tests.conftest import make_embedding

from core.schemas import NoteContentInput, NoteSystemFields, NoteResult
from core.uid import generate_uid


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


def test_create_note_returns_note_result(ctx):
    from tools.vault.create_note import create_note

    result = create_note(_content(), _system_fields(), ctx)

    assert isinstance(result, NoteResult)
    assert result.note.title == "Test Note Title"
    assert result.markdown_path.endswith(".md")


def test_create_note_writes_to_db(ctx):
    from tools.vault.create_note import create_note

    system = _system_fields()
    create_note(_content(), system, ctx)
    note = ctx.db.get_note(system.uid)

    assert note is not None
    assert note.title == "Test Note Title"


def test_create_note_writes_markdown_file(ctx):
    from tools.vault.create_note import create_note
    from pathlib import Path

    system = _system_fields()
    result = create_note(_content(), system, ctx)

    assert Path(result.markdown_path).exists()
    content = Path(result.markdown_path).read_text()
    assert "# Test Note Title" in content


def test_create_note_embeds_into_notes_vec(ctx):
    from tools.vault.create_note import create_note
    from infrastructure.db import search_notes

    system = _system_fields()
    create_note(_content(), system, ctx)

    results = search_notes(ctx.db._db_path, make_embedding(0.0), None, 5)
    assert len(results) == 1
    assert results[0].note_uid == system.uid


def test_create_note_source_type_mismatch_raises(ctx):
    from tools.vault.create_note import create_note
    from infrastructure.db import insert_source
    from core.schemas import Source

    source = Source(
        uid="src-1", slug="src", source_type="youtube", status="rag_ready",
        date_added=date.today().isoformat(),
    )
    insert_source(ctx.db._db_path, source)

    with pytest.raises(ValueError, match="source_type"):
        create_note(
            _content(source_type="audio"),
            _system_fields(source_uid="src-1"),
            ctx,
        )
