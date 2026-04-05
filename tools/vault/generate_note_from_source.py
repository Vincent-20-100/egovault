"""
Generate a draft note from an ingested source via the configured LLM.

Input  : source_uid (str) + VaultContext + optional template name
Output : NoteResult with note.status == 'draft'

The note is immediately embedded and searchable. It must be approved
(status set to 'active') before the source is finalized as vaulted.
"""

import logging
from datetime import date

from core.context import VaultContext
from core.schemas import Note, NoteResult, NoteSystemFields
from core.uid import generate_uid, make_unique_slug

logger = logging.getLogger(__name__)


def generate_note_from_source(
    source_uid: str,
    ctx: VaultContext,
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

    source = ctx.db.get_source(source_uid)
    if source is None:
        raise NotFoundError("Source", source_uid)

    if source.status != "rag_ready":
        raise ValueError(
            f"Source '{source_uid}' is not at rag_ready status (current: {source.status})"
        )

    if ctx.db.get_note_by_source(source_uid) is not None:
        raise ConflictError("Source", source_uid, "a note already exists for this source")

    metadata = {
        "title": source.title,
        "url": source.url,
        "author": source.author,
        "date_source": source.date_source,
        "source_type": source.source_type,
    }

    # ctx.generate holds the LLM callable; None means no LLM configured
    if ctx.generate is None:
        raise ValueError("No LLM provider configured. Cannot generate note content.")

    content_input = ctx.generate(source.transcript or "", metadata, template)

    # Fetch existing slugs to guarantee uniqueness
    existing_slugs = ctx.db.get_existing_slugs("notes")

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
    ctx.db.insert_note(note)

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = ctx.embed(text)
    ctx.db.insert_note_embedding(note.uid, embedding)

    ctx.vault_path.mkdir(parents=True, exist_ok=True)
    ctx.write_note(note, ctx.vault_path)

    updated_note = ctx.db.get_note(note.uid)
    return NoteResult(note=updated_note, markdown_path=str(ctx.vault_path / f"{note.slug}.md"))
