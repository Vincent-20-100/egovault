"""
Note embedding tool.

Input  : note_uid string + settings
Output : EmbedNoteResult
Populates notes_vec. Safe to call multiple times (delete + reinsert).
"""

from core.schemas import EmbedNoteResult
from core.config import Settings
from core.logging import loggable


@loggable("embed_note")
def embed_note(note_uid: str, settings: Settings) -> EmbedNoteResult:
    """
    Embed a note into notes_vec using the configured embedding provider.
    Combines title + docstring + body for embedding.
    Safe to call multiple times — deletes the existing embedding before reinserting.
    Sets sync_status to 'synced'.
    """
    from infrastructure.db import (
        get_note, delete_note_embedding, insert_note_embedding,
        update_note as db_update,
    )
    from infrastructure.embedding_provider import embed

    note = get_note(settings.vault_db_path, note_uid)
    if note is None:
        raise ValueError(f"Note not found: {note_uid}")

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = embed(text, settings)

    delete_note_embedding(settings.vault_db_path, note_uid)
    insert_note_embedding(settings.vault_db_path, note_uid, embedding)
    db_update(settings.vault_db_path, note_uid, {"sync_status": "synced"})

    return EmbedNoteResult(note_uid=note_uid, embedding_dim=len(embedding))
