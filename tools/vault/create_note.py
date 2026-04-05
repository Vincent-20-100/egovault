"""
Note creation tool.

Input  : NoteContentInput (LLM or manual) + NoteSystemFields
Output : NoteResult (note record + markdown path)
Writes to DB, embeds into notes_vec, and generates Markdown file.
Requires prior human approval of NoteContentInput before calling.
"""

from datetime import date

from core.context import VaultContext
from core.schemas import NoteContentInput, NoteSystemFields, NoteResult, Note
from core.logging import loggable
from core.uid import generate_uid, make_unique_slug


def create_note_from_content(
    content: NoteContentInput,
    ctx: VaultContext,
    source_uid: str | None = None,
) -> NoteResult:
    """Build system fields and create a note. Entry point for MCP and API."""
    existing_slugs = ctx.db.get_existing_slugs("notes")
    system_fields = NoteSystemFields(
        uid=generate_uid(),
        date_created=date.today().isoformat(),
        source_uid=source_uid if source_uid else None,
        slug=make_unique_slug(content.title, existing_slugs),
    )
    return create_note(content, system_fields, ctx)


@loggable("create_note")
def create_note(
    content: NoteContentInput,
    system_fields: NoteSystemFields,
    ctx: VaultContext,
) -> NoteResult:
    """Persist, embed, and write a note. Requires prior human approval of content."""
    if system_fields.source_uid:
        source = ctx.db.get_source(system_fields.source_uid)
        if (source and content.source_type
                and content.source_type != source.source_type):
            raise ValueError(
                f"content.source_type '{content.source_type}' does not match "
                f"source.source_type '{source.source_type}'"
            )

    today = date.today().isoformat()
    note = Note(
        **system_fields.model_dump(),
        **content.model_dump(),
        date_modified=today,
        sync_status="synced",
    )

    ctx.db.insert_note(note)

    semantic_text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = ctx.embed(semantic_text)
    ctx.db.insert_note_embedding(note.uid, embedding)

    ctx.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = ctx.write_note(note, ctx.vault_path)

    return NoteResult(note=note, markdown_path=str(markdown_path))
