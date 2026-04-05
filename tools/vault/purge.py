"""
Vault purge tool.

Input  : ctx (VaultContext)
Output : PurgeResult
Hard-deletes all notes and sources currently in pending_deletion.
"""

from pathlib import Path

from core.context import VaultContext
from core.schemas import PurgeResult
from core.logging import loggable


@loggable("purge")
def purge(ctx: VaultContext) -> PurgeResult:
    """
    Permanently remove all items marked for deletion from the vault.
    Purges all pending notes (embeddings, files) and sources (chunks, embeddings, media).
    """
    notes_purged = 0
    for note in ctx.db.list_notes_pending_deletion():
        ctx.db.delete_note_embedding(note.uid)
        ctx.db.hard_delete_note(note.uid)
        # Remove markdown file from vault if it exists
        md_file = ctx.vault_path / f"{note.slug}.md"
        if md_file.exists():
            md_file.unlink()
        notes_purged += 1

    sources_purged = 0
    media_files_deleted = 0
    for source in ctx.db.list_sources_pending_deletion():
        ctx.db.orphan_notes_for_source(source.uid)
        ctx.db.delete_chunk_embeddings_for_source(source.uid)
        ctx.db.delete_chunks_for_source(source.uid)
        if source.media_path:
            media_file = Path(source.media_path)
            if media_file.exists():
                media_file.unlink()
                media_files_deleted += 1
        ctx.db.hard_delete_source(source.uid)
        sources_purged += 1

    return PurgeResult(
        notes_purged=notes_purged,
        sources_purged=sources_purged,
        media_files_deleted=media_files_deleted,
    )
