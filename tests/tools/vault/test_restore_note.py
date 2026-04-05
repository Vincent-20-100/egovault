import pytest
from unittest.mock import patch
from core.errors import NotFoundError, ConflictError
from core.schemas import RestoreNoteResult


def _make_note(sync_status="pending_deletion"):
    from core.schemas import Note
    return Note(
        uid="nuid-1", slug="test", title="Test", docstring="Doc",
        body="Body content here.", tags=["test"], note_type=None, source_type=None,
        date_created="2026-03-30", date_modified="2026-03-30",
        sync_status=sync_status, source_uid=None,
    )


def test_restore_note_success(ctx):
    note = _make_note(sync_status="pending_deletion")
    with patch("infrastructure.db.get_note", return_value=note), \
         patch("infrastructure.db.restore_note", return_value="synced") as mock_restore:
        from tools.vault.restore_note import restore_note
        result = restore_note("nuid-1", ctx)
    assert result.uid == "nuid-1"
    assert result.restored_sync_status == "synced"
    mock_restore.assert_called_once()


def test_restore_note_not_found(ctx):
    with patch("infrastructure.db.get_note", return_value=None):
        from tools.vault.restore_note import restore_note
        with pytest.raises(NotFoundError):
            restore_note("nonexistent", ctx)


def test_restore_note_not_pending(ctx):
    note = _make_note(sync_status="synced")
    with patch("infrastructure.db.get_note", return_value=note):
        from tools.vault.restore_note import restore_note
        with pytest.raises(ConflictError):
            restore_note("nuid-1", ctx)
