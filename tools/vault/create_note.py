"""
Note creation tool.

Input  : NoteContentInput (LLM or manual) + NoteSystemFields
Output : NoteResult (note record + markdown path)
Writes to DB, embeds into notes_vec, and generates Markdown file.
Requires prior human approval of NoteContentInput before calling.
"""

from datetime import date

from core.schemas import NoteContentInput, NoteSystemFields, NoteResult, Note
from core.config import Settings
from core.logging import loggable


@loggable("create_note")
def create_note(
    content: NoteContentInput,
    system_fields: NoteSystemFields,
    settings: Settings,
) -> NoteResult:
    """
    Validate and persist a note.
    - Validates content.source_type matches source.source_type when source_uid is set.
    - Writes note to DB (notes + note_tags tables).
    - Embeds note into notes_vec automatically (title + docstring + body).
    - Generates Markdown via vault_writer.write_note().
    Requires prior human approval of NoteContentInput before calling.
    """
    from infrastructure.db import insert_note, get_source, insert_note_embedding
    from infrastructure.embedding_provider import embed
    from infrastructure.vault_writer import write_note

    if system_fields.source_uid:
        source = get_source(settings.vault_db_path, system_fields.source_uid)
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

    insert_note(settings.vault_db_path, note)

    text = "\n\n".join(filter(None, [note.title, note.docstring, note.body]))
    embedding = embed(text, settings)
    insert_note_embedding(settings.vault_db_path, note.uid, embedding)

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    markdown_path = write_note(note, settings.vault_path)

    return NoteResult(note=note, markdown_path=str(markdown_path))
