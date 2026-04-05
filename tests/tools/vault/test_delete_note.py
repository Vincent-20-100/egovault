import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.errors import NotFoundError, ConflictError
from core.schemas import DeleteNoteResult


def _make_note(uid="nuid-1", sync_status="synced"):
    from core.schemas import Note
    return Note(
        uid=uid, slug="test-note", title="Test", docstring="Doc",
        body="Body content here.", tags=["test"], note_type=None,
        source_type=None, date_created="2026-03-30", date_modified="2026-03-30",
        sync_status=sync_status, source_uid=None,
    )


def test_delete_note_soft_delete(ctx):
    """Soft-delete sets sync_status to pending_deletion."""
    note = _make_note()
    with patch("infrastructure.db.get_note", return_value=note), \
         patch("infrastructure.db.soft_delete_note") as mock_soft:
        from tools.vault.delete_note import delete_note
        result = delete_note("nuid-1", ctx)
    assert result.action == "soft_deleted"
    assert result.uid == "nuid-1"
    mock_soft.assert_called_once()


def test_delete_note_hard_delete(ctx, tmp_path):
    """Hard-delete removes embedding, note, and markdown file."""
    note = _make_note()
    md_file = ctx.vault_path / "test-note.md"
    md_file.write_text("content")

    with patch("infrastructure.db.get_note", return_value=note), \
         patch("infrastructure.db.delete_note_embedding") as mock_emb, \
         patch("infrastructure.db.hard_delete_note") as mock_hard:
        from tools.vault.delete_note import delete_note
        result = delete_note("nuid-1", ctx, force=True)
    assert result.action == "hard_deleted"
    mock_emb.assert_called_once()
    mock_hard.assert_called_once()
    assert not md_file.exists()


def test_delete_note_not_found(ctx):
    """Raises NotFoundError when note does not exist."""
    with patch("infrastructure.db.get_note", return_value=None):
        from tools.vault.delete_note import delete_note
        with pytest.raises(NotFoundError):
            delete_note("nonexistent", ctx)


def test_delete_note_already_pending(ctx):
    """Raises ConflictError on soft-delete if already pending_deletion."""
    note = _make_note(sync_status="pending_deletion")
    with patch("infrastructure.db.get_note", return_value=note):
        from tools.vault.delete_note import delete_note
        with pytest.raises(ConflictError):
            delete_note("nuid-1", ctx, force=False)
