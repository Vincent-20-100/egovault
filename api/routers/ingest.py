from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from api.models import IngestYoutubeRequest, IngestResponse
from core.uid import generate_uid
from core.sanitize import sanitize_error
from core.security import validate_youtube_url
from infrastructure.db import insert_job, update_job_status, update_job_done, update_job_failed

router = APIRouter(prefix="/ingest", tags=["ingest"])

_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}
_PDF_EXTENSIONS = {".pdf"}


def _submit_job(executor, fn, *args):
    """Submit a job function to the executor. Separated for easy mocking in tests."""
    executor.submit(fn, *args)


def _run_youtube(job_id: str, url: str, settings) -> None:
    from workflows.ingest_youtube import ingest_youtube
    system_db = settings.system_db_path
    try:
        update_job_status(system_db, job_id, "running")
        result = ingest_youtube(url, settings)
        update_job_done(system_db, job_id, {"note_uid": None, "slug": result.slug})
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))


def _run_audio(job_id: str, file_path: Path, settings) -> None:
    from workflows.ingest_audio import ingest_audio
    system_db = settings.system_db_path
    try:
        update_job_status(system_db, job_id, "running")
        result = ingest_audio(str(file_path), settings)
        update_job_done(system_db, job_id, {"note_uid": None, "slug": result.slug})
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))


def _run_pdf(job_id: str, file_path: Path, settings) -> None:
    from workflows.ingest_pdf import ingest_pdf
    system_db = settings.system_db_path
    try:
        update_job_status(system_db, job_id, "running")
        result = ingest_pdf(str(file_path), settings)
        update_job_done(system_db, job_id, {"note_uid": None, "slug": result.slug})
    except Exception as e:
        update_job_failed(system_db, job_id, sanitize_error(e))


@router.post("/youtube", status_code=202, response_model=IngestResponse)
def ingest_youtube_endpoint(body: IngestYoutubeRequest, request: Request):
    video_id = validate_youtube_url(body.url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="invalid youtube url")
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    settings = request.app.state.settings
    executor = request.app.state.executor
    job_id = generate_uid()
    insert_job(settings.system_db_path, job_id, "youtube", {"url": canonical_url})
    _submit_job(executor, _run_youtube, job_id, canonical_url, settings)
    return IngestResponse(job_id=job_id)


@router.post("/audio", status_code=202, response_model=IngestResponse)
async def ingest_audio_endpoint(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
    settings = request.app.state.settings
    executor = request.app.state.executor
    job_id = generate_uid()

    # Write file to stable path before submitting to executor
    content = await file.read()
    max_bytes = settings.system.upload.max_audio_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file too large (max {settings.system.upload.max_audio_mb} MB)")
    media_dir = settings.media_path / job_id
    media_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"upload{suffix}"
    dest = media_dir / safe_name
    dest.write_bytes(content)

    insert_job(settings.system_db_path, job_id, "audio",
               {"filename": f"media/{job_id}/{safe_name}"})
    _submit_job(executor, _run_audio, job_id, dest, settings)
    return IngestResponse(job_id=job_id)


@router.post("/pdf", status_code=202, response_model=IngestResponse)
async def ingest_pdf_endpoint(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _PDF_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
    settings = request.app.state.settings
    executor = request.app.state.executor
    job_id = generate_uid()

    content = await file.read()
    max_bytes = settings.system.upload.max_pdf_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file too large (max {settings.system.upload.max_pdf_mb} MB)")
    media_dir = settings.media_path / job_id
    media_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"upload{suffix}"
    dest = media_dir / safe_name
    dest.write_bytes(content)

    insert_job(settings.system_db_path, job_id, "pdf",
               {"filename": f"media/{job_id}/{safe_name}"})
    _submit_job(executor, _run_pdf, job_id, dest, settings)
    return IngestResponse(job_id=job_id)
