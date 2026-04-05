"""
Source deletion tool.

Input  : source uid + force flag
Output : DeleteSourceResult
Soft-delete: marks source as pending_deletion (reversible via restore_source).
Hard-delete: permanently removes source, chunks, embeddings, and media file.
Linked notes become orphaned (source_uid set to NULL) — they are NOT deleted.
"""

from pathlib import Path

from core.schemas import DeleteSourceResult
from core.config import Settings
from core.logging import loggable


@loggable("delete_source")
def delete_source(
    uid: str,
    settings: Settings,
    force: bool = False,
) -> DeleteSourceResult:
    """
    Remove a source from the vault.
    Soft-delete (default): marks as pending_deletion, reversible via restore.
    Hard-delete (force=True): permanently removes source, all chunks, embeddings, and media file.
    Linked notes become orphaned — their source_uid is set to NULL.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import (
        get_source, soft_delete_source, hard_delete_source,
        orphan_notes_for_source, delete_chunk_embeddings_for_source,
        delete_chunks_for_source,
    )

    source = get_source(settings.vault_db_path, uid)
    if source is None:
        raise NotFoundError("Source", uid)

    if not force:
        if source.status == "pending_deletion":
            raise ConflictError("Source", uid, "already marked for deletion")
        soft_delete_source(settings.vault_db_path, uid)
        return DeleteSourceResult(
            uid=uid, action="soft_deleted", media_deleted=False, orphaned_note_uids=[]
        )

    orphaned = orphan_notes_for_source(settings.vault_db_path, uid)
    delete_chunk_embeddings_for_source(settings.vault_db_path, uid)
    delete_chunks_for_source(settings.vault_db_path, uid)

    media_deleted = False
    if source.media_path:
        media_file = Path(source.media_path)
        if media_file.exists():
            media_file.unlink()
            media_deleted = True

    hard_delete_source(settings.vault_db_path, uid)

    return DeleteSourceResult(
        uid=uid, action="hard_deleted",
        media_deleted=media_deleted,
        orphaned_note_uids=orphaned,
    )
