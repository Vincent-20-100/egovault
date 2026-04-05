"""
Note deletion tool.

Input  : note uid + force flag
Output : DeleteNoteResult
Soft-delete: marks note as pending_deletion (reversible via restore_note).
Hard-delete: permanently removes note, embedding, and Markdown file.
The --delete-source cascade is handled by the routing layer, not this tool.
"""

from core.context import VaultContext
from core.schemas import DeleteNoteResult
from core.logging import loggable


@loggable("delete_note")
def delete_note(
    uid: str,
    ctx: VaultContext,
    force: bool = False,
) -> DeleteNoteResult:
    """
    Remove a note from the vault.
    Soft-delete (default): marks as pending_deletion, reversible via restore.
    Hard-delete (force=True): permanently removes note, embedding, and Markdown file.
    """
    from core.errors import NotFoundError, ConflictError

    note = ctx.db.get_note(uid)
    if note is None:
        raise NotFoundError("Note", uid)

    if not force:
        if note.sync_status == "pending_deletion":
            raise ConflictError("Note", uid, "already marked for deletion")
        ctx.db.soft_delete_note(uid)
        return DeleteNoteResult(uid=uid, action="soft_deleted")

    ctx.db.delete_note_embedding(uid)
    ctx.db.hard_delete_note(uid)

    md_file = ctx.vault_path / f"{note.slug}.md"
    if md_file.exists():
        md_file.unlink()

    return DeleteNoteResult(uid=uid, action="hard_deleted")
