from infrastructure.db import insert_job


def test_get_jobs_empty(client):
    response = client.get("/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_jobs_returns_list(client, tmp_settings):
    insert_job(tmp_settings.system_db_path, "job-test-1", "youtube", {"url": "https://youtu.be/x"})
    response = client.get("/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert any(j["id"] == "job-test-1" for j in jobs)


def test_get_jobs_filter_by_status(client, tmp_settings):
    insert_job(tmp_settings.system_db_path, "job-pending-1", "pdf", {"filename": "f.pdf"})
    response = client.get("/jobs?status=pending")
    assert response.status_code == 200
    for job in response.json():
        assert job["status"] == "pending"


def test_get_job_by_id(client, tmp_settings):
    insert_job(tmp_settings.system_db_path, "job-detail-1", "audio", {"filename": "a.mp3"})
    response = client.get("/jobs/job-detail-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "job-detail-1"
    assert data["job_type"] == "audio"


def test_get_job_not_found(client):
    response = client.get("/jobs/nonexistent-id")
    assert response.status_code == 404
