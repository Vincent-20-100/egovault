"""
Candidates and Chunks router — segmentation queue and proof drill-down endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Annotated

from api.models import (
    CandidateResponse,
    ClaimCandidateRequest,
    ConvertCandidateRequest,
    ChunkResponse,
    NoteDetail,
)
from core.schemas import NoteContentInput
from tools.vault.list_note_candidates import list_note_candidates
from tools.vault.claim_note_candidate import claim_note_candidate
from tools.vault.create_note_from_candidate import create_note_from_candidate
from tools.vault.skip_note_candidate import skip_note_candidate
from tools.vault.get_chunks import get_chunks

router = APIRouter(tags=["candidates"])


@router.get("/candidates", response_model=list[CandidateResponse])
def get_candidates(
    request: Request,
    source_uid: str | None = None,
    status: str | None = None,
):
    ctx = request.app.state.ctx
    candidates = list_note_candidates(ctx, source_uid=source_uid, status=status)
    return [CandidateResponse(**c.model_dump()) for c in candidates]


@router.get("/candidates/{uid}", response_model=CandidateResponse)
def get_candidate_by_uid(uid: str, request: Request):
    ctx = request.app.state.ctx
    candidate = ctx.db.get_note_candidate(uid)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate '{uid}' not found")
    return CandidateResponse(**candidate.model_dump())


@router.post("/candidates/{uid}/claim", response_model=CandidateResponse)
def claim_candidate_endpoint(
    uid: str,
    payload: ClaimCandidateRequest,
    request: Request,
):
    ctx = request.app.state.ctx
    candidate = claim_note_candidate(
        candidate_uid=uid,
        ctx=ctx,
        session_id=payload.session_id,
        is_human=payload.is_human,
    )
    return CandidateResponse(**candidate.model_dump())


@router.post("/candidates/{uid}/convert", response_model=NoteDetail)
def convert_candidate_endpoint(
    uid: str,
    payload: ConvertCandidateRequest,
    request: Request,
):
    ctx = request.app.state.ctx
    content_input = NoteContentInput(
        title=payload.title,
        docstring=payload.docstring,
        body=payload.body,
        tags=payload.tags,
    )
    result = create_note_from_candidate(
        candidate_uid=uid,
        content=content_input,
        ctx=ctx,
        session_id=payload.session_id,
        note_type=payload.note_type,
        tags=payload.tags,
    )
    note = result.note
    return NoteDetail(
        uid=note.uid,
        slug=note.slug,
        title=note.title,
        body=note.body,
        note_type=note.note_type,
        source_type=note.source_type,
        rating=note.rating,
        tags=note.tags,
        date_created=note.date_created,
        date_modified=note.date_modified,
        status=note.status,
        review_status=note.review_status,
        candidate_uid=note.candidate_uid,
    )


@router.post("/candidates/{uid}/skip")
def skip_candidate_endpoint(uid: str, request: Request):
    ctx = request.app.state.ctx
    return skip_note_candidate(uid, ctx)


@router.get("/chunks", response_model=list[ChunkResponse])
def get_chunks_endpoint(
    request: Request,
    uids: Annotated[list[str], Query()] = [],
):
    ctx = request.app.state.ctx
    chunks = get_chunks(uids, ctx)
    return [
        ChunkResponse(
            uid=c.uid,
            position=c.position,
            content=c.content,
            token_count=c.token_count,
        )
        for c in chunks
    ]
