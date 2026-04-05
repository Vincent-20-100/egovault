"""
Note update tool.

Input  : note uid + partial field update
Output : NoteResult
Writes to DB, re-embeds into notes_vec, regenerates Markdown.
"""

from datetime import date

from core.context import VaultContext
from core.schemas import NoteResult
from core.logging import loggable
from core.errors import NotFoundError

# System fields are immutable — silently ignored if included in the update dict
_SYSTEM_FIELDS = {"uid", "date_created", "source_uid", "generation_template"}


@loggable("update_note")
def update_note(uid: str, fields: dict, ctx: VaultContext) -> NoteResult:
    """
    Update editable fields of an existing note.
    SYSTEM fields (uid, date_created, source_uid, generation_template) are silently ignored.
    Re-embeds the note into notes_vec after any update.
    Updates date_modified. Regenerates Markdown file via write_note().
    """
    note = ctx.db.get_note(uid)
    if note is None:
        raise NotFoundError("Note", uid)

    safe_fields = {k: v for k, v in fields.items() if k not in _SYSTEM_FIELDS}
    safe_fields["date_modified"] = date.today().isoformat()

    ctx.db.update_note(uid, safe_fields)
    updated_note = ctx.db.get_note(uid)

    # Re-embed after content change so search index stays current
    text = "\n\n".join(filter(None, [updated_note.title, updated_note.docstring, updated_note.body]))
    embedding = ctx.embed(text)
    ctx.db.delete_note_embedding(uid)
    ctx.db.insert_note_embedding(uid, embedding)
    ctx.db.update_note(uid, {"sync_status": "synced"})
    updated_note = ctx.db.get_note(uid)

    ctx.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = ctx.write_note(updated_note, ctx.vault_path)

    return NoteResult(note=updated_note, markdown_path=str(markdown_path))
