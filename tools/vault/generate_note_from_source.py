"""
Generate a draft note from an ingested source via the configured LLM.

Input  : source_uid (str) + Settings + optional template name
Output : NoteResult with note.status == 'draft'

The note is immediately embedded and searchable. It must be approved
(status set to 'active') before the source is finalized as vaulted.
"""

import logging
from datetime import date

from core.config import Settings
from core.schemas import Note, NoteResult, NoteSystemFields
from core.uid import generate_uid, make_unique_slug

logger = logging.getLogger(__name__)


def generate_note_from_source(
    source_uid: str,
    settings: Settings,
    template: str = "standard",
) -> NoteResult:
    """
    Generate a draft note from an ingested source at rag_ready status.

    Calls the configured LLM to produce note content, creates the note as draft,
    and embeds it immediately so it is searchable. The note must be approved
    (status → active) before the source is finalized as vaulted.

    Raises NotFoundError if source_uid does not exist.
    Raises ValueError if source is not at rag_ready status.
    Raises ConflictError if a note already exists for this source.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import (
        get_source,
        get_note_by_source,
        get_note,
        get_vault_connection,
        insert_note,
        insert_note_embedding,
    )
    from infrastructure.embedding_provider import embed
    from infrastructure.llm_provider import generate_note_content
    from infrastructure.vault_writer import write_note

    db = settings.vault_db_path

    source = get_source(db, source_uid)
    if source is None:
        raise NotFoundError("Source", source_uid)

    if source.status != "rag_ready":
        raise ValueError(
            f"Source '{source_uid}' is not at rag_ready status (current: {source.status})"
        )

    if get_note_by_source(db, source_uid) is not None:
        raise ConflictError("Source", source_uid, "a note already exists for this source")

    metadata = {
        "title": source.title,
        "url": source.url,
        "author": source.author,
        "date_source": source.date_source,
        "source_type": source.source_type,
    }
    content_input = generate_note_content(
        source.transcript or "", metadata, template, settings
    )

    conn = get_vault_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM notes").fetchall()}
    conn.close()

    today = date.today().isoformat()
    system_fields = NoteSystemFields(
        uid=generate_uid(),
        date_created=today,
        source_uid=source_uid,
        slug=make_unique_slug(content_input.title, existing_slugs),
        generation_template=template,
    )

    note = Note(
        **system_fields.model_dump(),
        **content_input.model_dump(),
        date_modified=today,
        sync_status="synced",
        status="draft",
    )
    insert_note(db, note)

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = embed(text, settings)
    insert_note_embedding(db, note.uid, embedding)

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    write_note(note, settings.vault_path)

    updated_note = get_note(db, note.uid)
    return NoteResult(note=updated_note, markdown_path=str(settings.vault_path / f"{note.slug}.md"))
