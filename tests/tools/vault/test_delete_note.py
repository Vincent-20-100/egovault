import pytest
from pathlib import Path
from unittest.mock import patch
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


def test_delete_note_soft_delete(tmp_settings):
    """Soft-delete sets sync_status to pending_deletion."""
    note = _make_note()
    with patch("infrastructure.db.get_note", return_value=note), \
         patch("infrastructure.db.soft_delete_note") as mock_soft:
        from tools.vault.delete_note import delete_note
        result = delete_note("nuid-1", tmp_settings)
    assert result.action == "soft_deleted"
    assert result.uid == "nuid-1"
    mock_soft.assert_called_once()


def test_delete_note_hard_delete(tmp_settings, tmp_path):
    """Hard-delete removes embedding, note, and markdown file."""
    note = _make_note()
    md_file = tmp_path / "test-note.md"
    md_file.write_text("content")

    with patch("infrastructure.db.get_note", return_value=note), \
         patch("infrastructure.db.delete_note_embedding") as mock_emb, \
         patch("infrastructure.db.hard_delete_note") as mock_hard, \
         patch.object(type(tmp_settings), "vault_path",
                      new_callable=lambda: property(lambda self: tmp_path)):
        from tools.vault.delete_note import delete_note
        result = delete_note("nuid-1", tmp_settings, force=True)
    assert result.action == "hard_deleted"
    mock_emb.assert_called_once_with(tmp_settings.vault_db_path, "nuid-1")
    mock_hard.assert_called_once_with(tmp_settings.vault_db_path, "nuid-1")
    assert not md_file.exists()


def test_delete_note_not_found(tmp_settings):
    """Raises NotFoundError when note does not exist."""
    with patch("infrastructure.db.get_note", return_value=None):
        from tools.vault.delete_note import delete_note
        with pytest.raises(NotFoundError):
            delete_note("nonexistent", tmp_settings)


def test_delete_note_already_pending(tmp_settings):
    """Raises ConflictError on soft-delete if already pending_deletion."""
    note = _make_note(sync_status="pending_deletion")
    with patch("infrastructure.db.get_note", return_value=note):
        from tools.vault.delete_note import delete_note
        with pytest.raises(ConflictError):
            delete_note("nuid-1", tmp_settings, force=False)
