"""Query router — Librarian working memory retrieval context."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.schemas import CuratedContext

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(..., description="Knowledge question for the vault")
    limit: int = Field(default=5, ge=1, le=50)


def _run_query(query: str, ctx, limit: int) -> CuratedContext:
    """Separated for testing."""
    from tools.vault.query_vault import query_vault
    return query_vault(query, ctx, limit=limit)


@router.post("", response_model=dict)
def query_endpoint(body: QueryRequest, request: Request):
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")
    ctx = request.app.state.ctx
    result = _run_query(body.query, ctx, body.limit)
    return result.model_dump(mode="json")
