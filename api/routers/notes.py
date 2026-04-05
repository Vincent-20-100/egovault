"""Notes router — CRUD, generation, delete/restore operations."""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Annotated

from api.models import NoteDetail, NoteListItem, NotePatch
from core.schemas import DeleteNoteResult, RestoreNoteResult
from tools.vault.delete_note import delete_note
from tools.vault.restore_note import restore_note

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
        status=note.status,
    )


@router.get("", response_model=list[NoteListItem])
def get_notes(
    request: Request,
    note_type: str | None = None,
    tags: Annotated[list[str], Query()] = [],
    limit: int = 20,
    offset: int = 0,
):
    ctx = request.app.state.ctx
    notes = ctx.db.list_notes(note_type=note_type, tags=tags or None, limit=limit, offset=offset)
    return [_to_list_item(n) for n in notes]


@router.get("/{uid}", response_model=NoteDetail)
def get_note_by_uid(uid: str, request: Request):
    note = request.app.state.ctx.db.get_note(uid)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    return _to_detail(note)


@router.patch("/{uid}", response_model=NoteDetail)
def patch_note(uid: str, patch: NotePatch, request: Request):
    ctx = request.app.state.ctx
    if ctx.db.get_note(uid) is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")

    from datetime import date
    fields: dict = {}
    if patch.rating is not None:
        fields["rating"] = patch.rating
    if patch.tags is not None:
        ctx.db.set_note_tags(uid, patch.tags)
    if patch.status is not None:
        fields["status"] = patch.status
    if fields:
        fields["date_modified"] = date.today().isoformat()
        ctx.db.update_note(uid, fields)

    updated = ctx.db.get_note(uid)
    return _to_detail(updated)


@router.post("/{uid}/approve", response_model=NoteDetail)
def approve_note(uid: str, request: Request):
    """Approve a draft note and finalize its linked source if applicable."""
    ctx = request.app.state.ctx

    note = ctx.db.get_note(uid)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    if note.status != "draft":
        raise HTTPException(status_code=409,
                            detail=f"Note '{uid}' is not in draft status")

    from datetime import date
    ctx.db.update_note(uid, {"status": "active", "date_modified": date.today().isoformat()})

    if note.source_uid:
        source = ctx.db.get_source(note.source_uid)
        if source and source.status == "rag_ready":
            from tools.vault.finalize_source import finalize_source
            finalize_source(note.source_uid, ctx)

    updated = ctx.db.get_note(uid)
    return _to_detail(updated)


@router.delete("/{uid}", response_model=DeleteNoteResult)
def delete_note_endpoint(
    uid: str,
    request: Request,
    force: bool = False,
    delete_source: bool = False,
):
    from core.errors import NotFoundError, ConflictError
    ctx = request.app.state.ctx

    # Pre-fetch source_uid for cascade before note is deleted
    source_uid = None
    if delete_source and force:
        note = ctx.db.get_note(uid)
        if note:
            source_uid = note.source_uid

    try:
        result = delete_note(uid, ctx, force=force)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if source_uid and delete_source and force:
        from tools.vault.delete_source import delete_source as _delete_source
        try:
            _delete_source(source_uid, ctx, force=True)
            result = result.model_copy(update={"deleted_source_uid": source_uid})
        except Exception:
            pass  # source deletion is best-effort; note already deleted

    return result


@router.post("/{uid}/restore", response_model=RestoreNoteResult)
def restore_note_endpoint(uid: str, request: Request):
    from core.errors import NotFoundError, ConflictError
    ctx = request.app.state.ctx
    try:
        return restore_note(uid, ctx)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Note '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
