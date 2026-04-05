"""
Note deletion tool.

Input  : note uid + force flag
Output : DeleteNoteResult
Soft-delete: marks note as pending_deletion (reversible via restore_note).
Hard-delete: permanently removes note, embedding, and Markdown file.
The --delete-source cascade is handled by the routing layer, not this tool.
"""

from core.schemas import DeleteNoteResult
from core.config import Settings
from core.logging import loggable


@loggable("delete_note")
def delete_note(
    uid: str,
    settings: Settings,
    force: bool = False,
) -> DeleteNoteResult:
    """
    Remove a note from the vault.
    Soft-delete (default): marks as pending_deletion, reversible via restore.
    Hard-delete (force=True): permanently removes note, embedding, and Markdown file.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import (
        get_note, soft_delete_note, hard_delete_note, delete_note_embedding,
    )

    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise NotFoundError("Note", uid)

    if not force:
        if note.sync_status == "pending_deletion":
            raise ConflictError("Note", uid, "already marked for deletion")
        soft_delete_note(settings.vault_db_path, uid)
        return DeleteNoteResult(uid=uid, action="soft_deleted")

    delete_note_embedding(settings.vault_db_path, uid)
    hard_delete_note(settings.vault_db_path, uid)

    md_file = settings.vault_path / f"{note.slug}.md"
    if md_file.exists():
        md_file.unlink()

    return DeleteNoteResult(uid=uid, action="hard_deleted")
