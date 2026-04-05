"""
Note restore tool.

Input  : note uid
Output : RestoreNoteResult
Restores a note from pending_deletion to its previous sync_status.
"""

from core.schemas import RestoreNoteResult
from core.config import Settings
from core.logging import loggable


@loggable("restore_note")
def restore_note(uid: str, settings: Settings) -> RestoreNoteResult:
    """
    Restore a note previously marked for deletion.
    Reverts the note to its sync status prior to the soft-delete.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import get_note, restore_note as restore_note_db

    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise NotFoundError("Note", uid)
    if note.sync_status != "pending_deletion":
        raise ConflictError("Note", uid, "not marked for deletion")

    restored_status = restore_note_db(settings.vault_db_path, uid)
    return RestoreNoteResult(uid=uid, restored_sync_status=restored_status)
