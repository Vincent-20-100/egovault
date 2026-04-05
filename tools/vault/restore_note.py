"""
Note restore tool.

Input  : note uid
Output : RestoreNoteResult
Restores a note from pending_deletion to its previous sync_status.
"""

from core.context import VaultContext
from core.schemas import RestoreNoteResult
from core.logging import loggable


@loggable("restore_note")
def restore_note(uid: str, ctx: VaultContext) -> RestoreNoteResult:
    """
    Restore a note previously marked for deletion.
    Reverts the note to its sync status prior to the soft-delete.
    """
    from core.errors import NotFoundError, ConflictError

    note = ctx.db.get_note(uid)
    if note is None:
        raise NotFoundError("Note", uid)
    if note.sync_status != "pending_deletion":
        raise ConflictError("Note", uid, "not marked for deletion")

    restored_status = ctx.db.restore_note(uid)
    return RestoreNoteResult(uid=uid, restored_sync_status=restored_status)
