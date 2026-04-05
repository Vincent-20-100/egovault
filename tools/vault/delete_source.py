"""
Source deletion tool.

Input  : source uid + force flag
Output : DeleteSourceResult
Soft-delete: marks source as pending_deletion (reversible via restore_source).
Hard-delete: permanently removes source, chunks, embeddings, and media file.
Linked notes become orphaned (source_uid set to NULL) — they are NOT deleted.
"""

from pathlib import Path

from core.context import VaultContext
from core.schemas import DeleteSourceResult
from core.logging import loggable


@loggable("delete_source")
def delete_source(
    uid: str,
    ctx: VaultContext,
    force: bool = False,
) -> DeleteSourceResult:
    """Remove a source (soft or hard delete). Soft deletes are reversible. Linked notes become orphaned."""
    from core.errors import NotFoundError, ConflictError

    source = ctx.db.get_source(uid)
    if source is None:
        raise NotFoundError("Source", uid)

    if not force:
        if source.status == "pending_deletion":
            raise ConflictError("Source", uid, "already marked for deletion")
        ctx.db.soft_delete_source(uid)
        return DeleteSourceResult(
            uid=uid, action="soft_deleted", media_deleted=False, orphaned_note_uids=[]
        )

    orphaned = ctx.db.orphan_notes_for_source(uid)
    ctx.db.delete_chunk_embeddings_for_source(uid)
    ctx.db.delete_chunks_for_source(uid)

    media_deleted = False
    if source.media_path:
        media_file = Path(source.media_path)
        if media_file.exists():
            media_file.unlink()
            media_deleted = True

    ctx.db.hard_delete_source(uid)

    return DeleteSourceResult(
        uid=uid, action="hard_deleted",
        media_deleted=media_deleted,
        orphaned_note_uids=orphaned,
    )
