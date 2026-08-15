"""
Convert a NoteCandidate into a Note in a single atomic transaction.

Input  : candidate_uid, NoteContentInput, VaultContext, session_id
Output : NoteResult
"""
from __future__ import annotations

from datetime import date
from core.context import VaultContext
from core.schemas import Note, NoteContentInput, NoteResult, NoteSystemFields
from core.uid import generate_uid, make_unique_slug
from core.logging import loggable
from core.errors import NotFoundError
from tools.text.embed_note import embed_note


@loggable("create_note_from_candidate")
def create_note_from_candidate(
    candidate_uid: str,
    content: NoteContentInput,
    ctx: VaultContext,
    session_id: str,
    note_type: str = "synthese",
    tags: list[str] | None = None,
) -> NoteResult:
    """
    Atomically convert a NoteCandidate into a Note.
    1. Verifies candidate lock ownership.
    2. Writes Markdown note file to disk (if write_note is available).
    3. Atomically inserts Note and transitions candidate to 'converted' via single SQLite transaction.
    4. Computes note embedding and indexes into notes_vec.
    """
    candidate = ctx.db.get_note_candidate(candidate_uid)
    if candidate is None:
        raise NotFoundError("NoteCandidate", candidate_uid)

    today = date.today().isoformat()
    existing_slugs = ctx.db.get_existing_slugs("notes")
    slug = make_unique_slug(content.title, existing_slugs)

    note_uid = generate_uid()
    system_fields = NoteSystemFields(
        uid=note_uid,
        source_uid=candidate.source_uid,
        slug=slug,
        date_created=today,
        generation_template="standard",
        candidate_uid=candidate_uid,
    )

    resolved_tags = tags or (content.tags if getattr(content, "tags", None) else ["untagged"])

    note = Note(
        **system_fields.model_dump(),
        title=content.title,
        docstring=content.docstring,
        body=content.body,
        tags=resolved_tags,
        note_type=note_type,
        source_type="texte",
        date_modified=today,
        sync_status="synced",
        status="active",
        review_status="unreviewed",
    )

    # 1. Write markdown file to vault directory
    markdown_path = ""
    if ctx.write_note is not None:
        markdown_path = str(ctx.write_note(note, ctx.vault_path))

    # 2. Atomic SQLite transaction (insert note + mark candidate converted)
    ctx.db.create_note_from_candidate(note, candidate_uid, session_id)

    # 3. Compute vector embedding
    embed_note(note.uid, ctx)

    return NoteResult(note=note, markdown_path=markdown_path)
