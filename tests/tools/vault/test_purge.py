import pytest
from unittest.mock import patch, MagicMock
from core.schemas import PurgeResult


def test_purge_empty_vault(ctx):
    with patch("infrastructure.db.list_notes_pending_deletion", return_value=[]), \
         patch("infrastructure.db.list_sources_pending_deletion", return_value=[]):
        from tools.vault.purge import purge
        result = purge(ctx)
    assert result.notes_purged == 0
    assert result.sources_purged == 0
    assert result.media_files_deleted == 0


def test_purge_deletes_pending_notes(ctx):
    from core.schemas import Note
    note = Note(
        uid="nuid-1", slug="test", title="Test", docstring="Doc",
        body="Body content here.", tags=["t"], note_type=None, source_type=None,
        date_created="2026-03-30", date_modified="2026-03-30",
        sync_status="pending_deletion", source_uid=None,
    )
    with patch("infrastructure.db.list_notes_pending_deletion", return_value=[note]), \
         patch("infrastructure.db.list_sources_pending_deletion", return_value=[]), \
         patch("infrastructure.db.delete_note_embedding"), \
         patch("infrastructure.db.hard_delete_note"):
        from tools.vault.purge import purge
        result = purge(ctx)
    assert result.notes_purged == 1


def test_purge_deletes_pending_sources(ctx):
    from core.schemas import Source
    source = Source(
        uid="suid-1", slug="test-source", source_type="youtube",
        status="pending_deletion", date_added="2026-03-30",
    )
    with patch("infrastructure.db.list_notes_pending_deletion", return_value=[]), \
         patch("infrastructure.db.list_sources_pending_deletion", return_value=[source]), \
         patch("infrastructure.db.orphan_notes_for_source", return_value=[]), \
         patch("infrastructure.db.delete_chunk_embeddings_for_source"), \
         patch("infrastructure.db.delete_chunks_for_source"), \
         patch("infrastructure.db.hard_delete_source"):
        from tools.vault.purge import purge
        result = purge(ctx)
    assert result.sources_purged == 1
    assert result.media_files_deleted == 0
