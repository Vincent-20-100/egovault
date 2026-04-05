"""Search router — semantic search over chunks and notes."""

from fastapi import APIRouter, HTTPException, Request

from api.models import SearchRequest, SearchResultResponse
from core.schemas import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


def _run_search(query: str, ctx, limit: int) -> list[SearchResult]:
    """Separated for mocking in tests."""
    from tools.vault.search import search
    return search(query, ctx, mode="notes", limit=limit)


@router.post("", response_model=list[SearchResultResponse])
def search_endpoint(body: SearchRequest, request: Request):
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")
    ctx = request.app.state.ctx
    results = _run_search(body.query, ctx, body.limit)
    output = []
    for r in results:
        if not r.note_uid:
            continue
        note = ctx.db.get_note(r.note_uid)
        output.append(SearchResultResponse(
            note_uid=r.note_uid,
            slug=note.slug if note else "",
            title=r.title,
            score=round(1 - r.distance, 4),
            excerpt=r.content[:300] if r.content else "",
        ))
    return output
