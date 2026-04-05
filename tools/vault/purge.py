"""
Vault purge tool.

Input  : settings
Output : PurgeResult
Hard-deletes all notes and sources currently in pending_deletion.
"""

from pathlib import Path

from core.schemas import PurgeResult
from core.config import Settings
from core.logging import loggable


@loggable("purge")
def purge(settings: Settings) -> PurgeResult:
    """
    Permanently remove all items marked for deletion from the vault.
    Purges all pending notes (embeddings, files) and sources (chunks, embeddings, media).
    """
    from infrastructure.db import (
        list_notes_pending_deletion, list_sources_pending_deletion,
        delete_note_embedding, hard_delete_note,
        orphan_notes_for_source, delete_chunk_embeddings_for_source,
        delete_chunks_for_source, hard_delete_source,
    )

    notes_purged = 0
    for note in list_notes_pending_deletion(settings.vault_db_path):
        delete_note_embedding(settings.vault_db_path, note.uid)
        hard_delete_note(settings.vault_db_path, note.uid)
        md_file = settings.vault_path / f"{note.slug}.md"
        if md_file.exists():
            md_file.unlink()
        notes_purged += 1

    sources_purged = 0
    media_files_deleted = 0
    for source in list_sources_pending_deletion(settings.vault_db_path):
        orphan_notes_for_source(settings.vault_db_path, source.uid)
        delete_chunk_embeddings_for_source(settings.vault_db_path, source.uid)
        delete_chunks_for_source(settings.vault_db_path, source.uid)
        if source.media_path:
            media_file = Path(source.media_path)
            if media_file.exists():
                media_file.unlink()
                media_files_deleted += 1
        hard_delete_source(settings.vault_db_path, source.uid)
        sources_purged += 1

    return PurgeResult(
        notes_purged=notes_purged,
        sources_purged=sources_purged,
        media_files_deleted=media_files_deleted,
    )
