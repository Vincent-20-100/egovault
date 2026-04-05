from fastapi import APIRouter, Request, HTTPException

from api.models import JobListItem, JobResponse
from infrastructure.db import get_job, list_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListItem])
def get_jobs(request: Request, status: str | None = None, limit: int = 20):
    jobs = list_jobs(request.app.state.settings.system_db_path, status=status, limit=limit)
    return [JobListItem(
        id=j["id"], status=j["status"],
        job_type=j["job_type"], created_at=j["created_at"],
    ) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: str, request: Request):
    job = get_job(request.app.state.settings.system_db_path, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobResponse(
        id=job["id"], status=job["status"], job_type=job["job_type"],
        input=job["input"], result=job["result"], error=job["error"],
        created_at=job["created_at"], updated_at=job["updated_at"],
    )
