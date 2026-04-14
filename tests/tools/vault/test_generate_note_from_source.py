import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock
from datetime import date

from tests.conftest import make_embedding

from core.schemas import Source, NoteContentInput, NoteResult
from core.context import VaultContext


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


def _ctx_with_generate(ctx):
    """Return a ctx copy that has a mock LLM generate function."""
    mock_generate = MagicMock(return_value=_make_content())
    return VaultContext(
        settings=ctx.settings,
        db=ctx.db,
        system_db_path=ctx.system_db_path,
        embed=ctx.embed,
        generate=mock_generate,
        write_note=ctx.write_note,
        vault_path=ctx.vault_path,
        media_path=ctx.media_path,
    )


def test_generate_note_creates_draft(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source

    ctx.db.insert_source(_make_source())
    test_ctx = _ctx_with_generate(ctx)

    result = generate_note_from_source("src-1", test_ctx)

    assert isinstance(result, NoteResult)
    assert result.note.status == "draft"
    assert result.note.source_uid == "src-1"
    assert result.note.generation_template == "standard"


def test_generate_note_note_is_searchable(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source

    ctx.db.insert_source(_make_source(uid="src-2", slug="src-2"))
    test_ctx = _ctx_with_generate(ctx)

    result = generate_note_from_source("src-2", test_ctx)

    hits = ctx.db.search_notes(make_embedding(0.0), None, 5)
    note_uids = [h.note_uid for h in hits]
    assert result.note.uid in note_uids


def test_generate_note_not_found(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from core.errors import NotFoundError

    test_ctx = _ctx_with_generate(ctx)
    with pytest.raises(NotFoundError):
        generate_note_from_source("nonexistent", test_ctx)


def test_generate_note_source_not_rag_ready(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source

    ctx.db.insert_source(_make_source(uid="src-3", slug="src-3", status="raw"))
    test_ctx = _ctx_with_generate(ctx)
    with pytest.raises(ValueError, match="rag_ready"):
        generate_note_from_source("src-3", test_ctx)


def test_generate_note_conflict_if_note_exists(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source
    from core.schemas import Note
    from core.errors import ConflictError

    ctx.db.insert_source(_make_source(uid="src-4", slug="src-4"))
    existing = Note(
        uid="existing-note", source_uid="src-4", slug="existing-note",
        note_type=None, source_type=None, generation_template=None, rating=None,
        sync_status="synced", title="Existing Note", docstring="Already exists.",
        body="Body content here already.", url=None,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    ctx.db.insert_note(existing)
    test_ctx = _ctx_with_generate(ctx)
    with pytest.raises(ConflictError):
        generate_note_from_source("src-4", test_ctx)


def test_generate_note_custom_template(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source

    ctx.db.insert_source(_make_source(uid="src-5", slug="src-5"))
    mock_generate = MagicMock(return_value=_make_content())
    test_ctx = VaultContext(
        settings=ctx.settings,
        db=ctx.db,
        system_db_path=ctx.system_db_path,
        embed=ctx.embed,
        generate=mock_generate,
        write_note=ctx.write_note,
        vault_path=ctx.vault_path,
        media_path=ctx.media_path,
    )

    result = generate_note_from_source("src-5", test_ctx, template="standard")

    assert result.note.generation_template == "standard"
    # Verify generate was called with the template argument
    call_args = mock_generate.call_args
    assert call_args[0][2] == "standard"  # third positional arg is template


def test_generate_note_uses_synthesize_for_large_source(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source

    # Build a source whose transcript exceeds the threshold
    big_transcript = " ".join(["word"] * 200_000)  # ~266k tokens estimated
    ctx.db.insert_source(_make_source(transcript=big_transcript))

    fake_content = _make_content()
    test_ctx = _ctx_with_generate(ctx)

    with patch("tools.vault.generate_note_from_source.synthesize_large_source") as mock_synth, \
         patch("tools.vault.generate_note_from_source.get_context_window", return_value=10_000):
        mock_synth.return_value = fake_content
        result = generate_note_from_source("src-1", test_ctx)

    mock_synth.assert_called_once()
    assert result.note.title == fake_content.title


def test_generate_note_uses_direct_path_for_small_source(ctx):
    from tools.vault.generate_note_from_source import generate_note_from_source

    ctx.db.insert_source(_make_source(uid="src-small", slug="src-small", transcript="short transcript content"))
    test_ctx = _ctx_with_generate(ctx)

    with patch("tools.vault.generate_note_from_source.synthesize_large_source") as mock_synth, \
         patch("tools.vault.generate_note_from_source.get_context_window", return_value=200_000):
        result = generate_note_from_source("src-small", test_ctx)

    mock_synth.assert_not_called()
    assert result.note.status == "draft"
