from fastapi import APIRouter, HTTPException, Request, Query
from typing import Annotated

from api.models import NoteDetail, NoteListItem, NotePatch
from infrastructure.db import get_note, list_notes, update_note, set_note_tags

router = APIRouter(prefix="/notes", tags=["notes"])


def _to_list_item(note) -> NoteListItem:
    return NoteListItem(
        uid=note.uid, slug=note.slug, title=note.title,
        note_type=note.note_type, rating=note.rating,
        tags=note.tags, date_created=note.date_created,
    )


def _to_detail(note) -> NoteDetail:
    return NoteDetail(
        uid=note.uid, slug=note.slug, title=note.title,
        body=note.body, note_type=note.note_type,
        source_type=note.source_type, rating=note.rating,
        tags=note.tags, date_created=note.date_created,
        date_modified=note.date_modified,
    )


@router.get("", response_model=list[NoteListItem])
def get_notes(
    request: Request,
    note_type: str | None = None,
    tags: Annotated[list[str], Query()] = [],
    limit: int = 20,
    offset: int = 0,
):
    db = request.app.state.settings.vault_db_path
    notes = list_notes(db, note_type=note_type, tags=tags or None, limit=limit, offset=offset)
    return [_to_list_item(n) for n in notes]


@router.get("/{uid}", response_model=NoteDetail)
def get_note_by_uid(uid: str, request: Request):
    note = get_note(request.app.state.settings.vault_db_path, uid)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    return _to_detail(note)


@router.patch("/{uid}", response_model=NoteDetail)
def patch_note(uid: str, patch: NotePatch, request: Request):
    db = request.app.state.settings.vault_db_path
    if get_note(db, uid) is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")

    from datetime import date
    fields: dict = {}
    if patch.rating is not None:
        fields["rating"] = patch.rating
    if patch.tags is not None:
        set_note_tags(db, uid, patch.tags)
    if fields:
        fields["date_modified"] = date.today().isoformat()
        update_note(db, uid, fields)

    updated = get_note(db, uid)
    return _to_detail(updated)
