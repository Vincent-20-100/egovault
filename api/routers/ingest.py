from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query

from api.models import IngestYoutubeRequest, IngestTextRequest, IngestWebRequest, IngestResponse
from core.uid import generate_uid
from core.sanitize import sanitize_error
from core.security import validate_youtube_url, validate_web_url
# System DB job functions (not in VaultDB)
from infrastructure.db import insert_job, update_job_status, update_job_done, update_job_failed

router = APIRouter(prefix="/ingest", tags=["ingest"])

_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}
_PDF_EXTENSIONS = {".pdf"}


def _submit_job(executor, fn, *args):
    """Submit a job function to the executor. Separated for easy mocking in tests."""
    executor.submit(fn, *args)


def _run_ingest(job_id: str, source_type: str, target: str, ctx, auto_generate_note=None, title=None) -> None:
    from workflows.ingest import ingest
    from core.errors import IngestError, LargeFormatError
    system_db = ctx.system_db_path
    try:
        update_job_status(system_db, job_id, "running")
        result = ingest(source_type, target, ctx, title=title, auto_generate_note=auto_generate_note)
        update_job_done(system_db, job_id, {"source_uid": result.uid, "slug": result.slug})
    except LargeFormatError as e:
        update_job_done(system_db, job_id, {"source_uid": e.source_uid, "slug": None, "large_format": True})
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))


@router.post("/youtube", status_code=202, response_model=IngestResponse)
def ingest_youtube_endpoint(body: IngestYoutubeRequest, request: Request):
    video_id = validate_youtube_url(body.url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="invalid youtube url")
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    ctx = request.app.state.ctx
    executor = request.app.state.executor
    job_id = generate_uid()
    insert_job(ctx.system_db_path, job_id, "youtube", {"url": canonical_url})
    _submit_job(executor, _run_ingest, job_id, "youtube", canonical_url, ctx,
                body.auto_generate_note)
    return IngestResponse(job_id=job_id)


@router.post("/audio", status_code=202, response_model=IngestResponse)
async def ingest_audio_endpoint(
    request: Request,
    file: UploadFile = File(...),
    auto_generate_note: bool | None = Query(None),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
    ctx = request.app.state.ctx
    executor = request.app.state.executor
    job_id = generate_uid()

    # Write file to stable path before submitting to executor
    content = await file.read()
    max_bytes = ctx.settings.system.upload.max_audio_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file too large (max {ctx.settings.system.upload.max_audio_mb} MB)")
    media_dir = ctx.media_path / job_id
    media_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"upload{suffix}"
    dest = media_dir / safe_name
    dest.write_bytes(content)

    insert_job(ctx.system_db_path, job_id, "audio",
               {"filename": f"media/{job_id}/{safe_name}"})
    _submit_job(executor, _run_ingest, job_id, "audio", str(dest), ctx, auto_generate_note)
    return IngestResponse(job_id=job_id)


@router.post("/pdf", status_code=202, response_model=IngestResponse)
async def ingest_pdf_endpoint(
    request: Request,
    file: UploadFile = File(...),
    auto_generate_note: bool | None = Query(None),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _PDF_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
    ctx = request.app.state.ctx
    executor = request.app.state.executor
    job_id = generate_uid()

    content = await file.read()
    max_bytes = ctx.settings.system.upload.max_pdf_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file too large (max {ctx.settings.system.upload.max_pdf_mb} MB)")
    media_dir = ctx.media_path / job_id
    media_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"upload{suffix}"
    dest = media_dir / safe_name
    dest.write_bytes(content)

    insert_job(ctx.system_db_path, job_id, "pdf",
               {"filename": f"media/{job_id}/{safe_name}"})
    _submit_job(executor, _run_ingest, job_id, "pdf", str(dest), ctx, auto_generate_note)
    return IngestResponse(job_id=job_id)


@router.post("/web", status_code=202, response_model=IngestResponse)
def ingest_web_endpoint(body: IngestWebRequest, request: Request):
    try:
        validate_web_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ctx = request.app.state.ctx
    executor = request.app.state.executor
    job_id = generate_uid()
    insert_job(ctx.system_db_path, job_id, "web", {"url": body.url})
    _submit_job(executor, _run_ingest, job_id, "web", body.url, ctx,
                body.auto_generate_note, body.title)
    return IngestResponse(job_id=job_id)


@router.post("/text", status_code=202, response_model=IngestResponse)
def ingest_text_endpoint(body: IngestTextRequest, request: Request):
    ctx = request.app.state.ctx
    max_chars = ctx.settings.system.upload.max_text_chars
    if len(body.text) > max_chars:
        raise HTTPException(status_code=413, detail=f"text too large (max {max_chars} characters)")
    executor = request.app.state.executor
    job_id = generate_uid()
    source_type = body.source_type or "texte"
    insert_job(ctx.system_db_path, job_id, source_type, {"title": body.title})
    _submit_job(executor, _run_ingest, job_id, source_type, body.text, ctx,
                body.auto_generate_note, body.title)
    return IngestResponse(job_id=job_id)
