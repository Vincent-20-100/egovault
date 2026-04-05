from fastapi import APIRouter, HTTPException, Request

from api.models import SourceDetail, SourceListItem
from core.schemas import DeleteSourceResult, RestoreSourceResult
from infrastructure.db import get_source, list_sources
from tools.vault.delete_source import delete_source
from tools.vault.restore_source import restore_source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceListItem])
def get_sources(request: Request, status: str | None = None, limit: int = 20, offset: int = 0):
    db = request.app.state.settings.vault_db_path
    sources = list_sources(db, status=status, limit=limit, offset=offset)
    return [SourceListItem(
        uid=s.uid, slug=s.slug, source_type=s.source_type,
        status=s.status, title=s.title, date_added=s.date_added,
    ) for s in sources]


@router.get("/{uid}", response_model=SourceDetail)
def get_source_by_uid(uid: str, request: Request):
    source = get_source(request.app.state.settings.vault_db_path, uid)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source '{uid}' not found")
    return SourceDetail(
        uid=source.uid, slug=source.slug, source_type=source.source_type,
        status=source.status, title=source.title, url=source.url,
        transcript=source.transcript, date_added=source.date_added,
        date_source=source.date_source,
    )


@router.delete("/{uid}", response_model=DeleteSourceResult)
def delete_source_endpoint(uid: str, request: Request, force: bool = False):
    from core.errors import NotFoundError, ConflictError
    settings = request.app.state.settings
    try:
        return delete_source(uid, settings, force=force)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Source '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{uid}/restore", response_model=RestoreSourceResult)
def restore_source_endpoint(uid: str, request: Request):
    from core.errors import NotFoundError, ConflictError
    settings = request.app.state.settings
    try:
        return restore_source(uid, settings)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Source '{uid}' not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
