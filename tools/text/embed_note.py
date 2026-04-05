"""
Note embedding tool.

Input  : note_uid string + VaultContext
Output : EmbedNoteResult
Populates notes_vec. Safe to call multiple times (delete + reinsert).
"""

from core.schemas import EmbedNoteResult
from core.context import VaultContext
from core.logging import loggable


@loggable("embed_note")
def embed_note(note_uid: str, ctx: VaultContext) -> EmbedNoteResult:
    """
    Embed a note into notes_vec using the configured embedding provider.
    Combines title + docstring + body for embedding.
    Safe to call multiple times — deletes the existing embedding before reinserting.
    Sets sync_status to 'synced'.
    """
    note = ctx.db.get_note(note_uid)
    if note is None:
        raise ValueError(f"Note not found: {note_uid}")

    # Concatenate all text fields that carry semantic meaning
    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = ctx.embed(text)

    # Delete-then-reinsert ensures idempotency (no duplicate rows in notes_vec)
    ctx.db.delete_note_embedding(note_uid)
    ctx.db.insert_note_embedding(note_uid, embedding)
    ctx.db.update_note(note_uid, {"sync_status": "synced"})

    return EmbedNoteResult(note_uid=note_uid, embedding_dim=len(embedding))
