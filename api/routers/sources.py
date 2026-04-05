from fastapi import APIRouter, HTTPException, Request

from api.models import SourceDetail, SourceListItem
from infrastructure.db import get_source, list_sources

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
