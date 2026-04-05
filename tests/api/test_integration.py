"""
Integration test: full job lifecycle.

Uses a real ThreadPoolExecutor but mocked workflow functions.
Polls GET /jobs/{id} until terminal state.
"""
import time
from unittest.mock import patch


def _poll_job(client, job_id: str, timeout: float = 5.0) -> dict:
    """Poll GET /jobs/{id} until terminal state or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def test_youtube_job_lifecycle_done(client):
    with patch("api.routers.ingest._run_youtube") as mock_run:
        def fake_run(job_id, url, settings, auto_generate_note=None):
            from infrastructure.db import update_job_status, update_job_done
            update_job_status(settings.system_db_path, job_id, "running")
            update_job_done(settings.system_db_path, job_id, {"note_uid": None, "slug": "fake-video"})

        mock_run.side_effect = fake_run

        response = client.post("/ingest/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
        assert response.status_code == 202
        job_id = response.json()["job_id"]

    job = _poll_job(client, job_id)
    assert job["status"] == "done"
    assert job["result"]["slug"] == "fake-video"


def test_youtube_job_lifecycle_failed(client):
    with patch("api.routers.ingest._run_youtube") as mock_run:
        def fake_run(job_id, url, settings, auto_generate_note=None):
            from infrastructure.db import update_job_status, update_job_failed
            update_job_status(settings.system_db_path, job_id, "running")
            update_job_failed(settings.system_db_path, job_id, "Transcription error")

        mock_run.side_effect = fake_run

        response = client.post("/ingest/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
        job_id = response.json()["job_id"]

    job = _poll_job(client, job_id)
    assert job["status"] == "failed"
    assert "Transcription error" in job["error"]


def test_orphan_jobs_marked_failed_at_startup(tmp_settings):
    """Jobs left pending from a previous crash must be marked failed on startup."""
    from infrastructure.db import insert_job, mark_orphan_jobs_failed, get_job
    db = tmp_settings.system_db_path
    insert_job(db, "orphan-1", "audio", {"filename": "f.mp3"})
    mark_orphan_jobs_failed(db)
    job = get_job(db, "orphan-1")
    assert job["status"] == "failed"
    assert job["error"] == "process restarted"
