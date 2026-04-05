import pytest
from pathlib import Path
from unittest.mock import patch
from core.errors import NotFoundError, ConflictError
from core.schemas import DeleteSourceResult


def _make_source(uid="suid-1", status="rag_ready", media_path=None):
    from core.schemas import Source
    return Source(
        uid=uid, slug="test-source", source_type="youtube",
        status=status, date_added="2026-03-30", media_path=media_path,
    )


def test_delete_source_soft_delete(ctx):
    source = _make_source()
    with patch("infrastructure.db.get_source", return_value=source), \
         patch("infrastructure.db.soft_delete_source") as mock_soft:
        from tools.vault.delete_source import delete_source
        result = delete_source("suid-1", ctx)
    assert result.action == "soft_deleted"
    assert result.media_deleted is False
    assert result.orphaned_note_uids == []
    mock_soft.assert_called_once()


def test_delete_source_hard_delete_no_media(ctx):
    source = _make_source()
    with patch("infrastructure.db.get_source", return_value=source), \
         patch("infrastructure.db.orphan_notes_for_source", return_value=["nuid-1"]) as mock_orphan, \
         patch("infrastructure.db.delete_chunk_embeddings_for_source") as mock_emb, \
         patch("infrastructure.db.delete_chunks_for_source") as mock_chunks, \
         patch("infrastructure.db.hard_delete_source") as mock_hard:
        from tools.vault.delete_source import delete_source
        result = delete_source("suid-1", ctx, force=True)
    assert result.action == "hard_deleted"
    assert result.media_deleted is False
    assert result.orphaned_note_uids == ["nuid-1"]
    mock_orphan.assert_called_once()
    mock_emb.assert_called_once()
    mock_chunks.assert_called_once()
    mock_hard.assert_called_once()


def test_delete_source_hard_delete_with_media(ctx, tmp_path):
    media_file = tmp_path / "video.mp4"
    media_file.write_bytes(b"fake")
    source = _make_source(media_path=str(media_file))
    with patch("infrastructure.db.get_source", return_value=source), \
         patch("infrastructure.db.orphan_notes_for_source", return_value=[]), \
         patch("infrastructure.db.delete_chunk_embeddings_for_source"), \
         patch("infrastructure.db.delete_chunks_for_source"), \
         patch("infrastructure.db.hard_delete_source"):
        from tools.vault.delete_source import delete_source
        result = delete_source("suid-1", ctx, force=True)
    assert result.media_deleted is True
    assert not media_file.exists()


def test_delete_source_not_found(ctx):
    with patch("infrastructure.db.get_source", return_value=None):
        from tools.vault.delete_source import delete_source
        with pytest.raises(NotFoundError):
            delete_source("nonexistent", ctx)


def test_delete_source_already_pending(ctx):
    source = _make_source(status="pending_deletion")
    with patch("infrastructure.db.get_source", return_value=source):
        from tools.vault.delete_source import delete_source
        with pytest.raises(ConflictError):
            delete_source("suid-1", ctx, force=False)
