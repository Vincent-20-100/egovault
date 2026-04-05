"""
Note update tool.

Input  : note uid + partial field update
Output : NoteResult
Writes to DB, re-embeds into notes_vec, regenerates Markdown.
"""

from datetime import date

from core.schemas import NoteResult
from core.config import Settings
from core.logging import loggable
from core.errors import NotFoundError

_SYSTEM_FIELDS = {"uid", "date_created", "source_uid", "generation_template"}


@loggable("update_note")
def update_note(uid: str, fields: dict, settings: Settings) -> NoteResult:
    """
    Update editable fields of an existing note.
    SYSTEM fields (uid, date_created, source_uid, generation_template) are silently ignored.
    Re-embeds the note into notes_vec after any update.
    Updates date_modified. Regenerates Markdown file via vault_writer.
    """
    from infrastructure.db import (
        get_note, update_note as db_update,
        delete_note_embedding, insert_note_embedding,
    )
    from infrastructure.embedding_provider import embed
    from infrastructure.vault_writer import write_note

    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise NotFoundError("Note", uid)

    safe_fields = {k: v for k, v in fields.items() if k not in _SYSTEM_FIELDS}
    safe_fields["date_modified"] = date.today().isoformat()

    db_update(settings.vault_db_path, uid, safe_fields)
    updated_note = get_note(settings.vault_db_path, uid)

    text = "\n\n".join(filter(None, [updated_note.title, updated_note.docstring, updated_note.body]))
    embedding = embed(text, settings)
    delete_note_embedding(settings.vault_db_path, uid)
    insert_note_embedding(settings.vault_db_path, uid, embedding)
    db_update(settings.vault_db_path, uid, {"sync_status": "synced"})
    updated_note = get_note(settings.vault_db_path, uid)

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(updated_note, settings.vault_path)

    return NoteResult(note=updated_note, markdown_path=str(markdown_path))
