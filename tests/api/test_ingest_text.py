"""Tests for POST /ingest/text endpoint."""

from unittest.mock import patch


def test_ingest_text_returns_202(client):
    with patch("api.routers.ingest._submit_job") as mock_submit:
        mock_submit.return_value = None
        response = client.post("/ingest/text", json={
            "text": "This is a test document with enough content.",
            "title": "Test Document",
        })
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 36  # UUID4


def test_ingest_text_empty_text_returns_422(client):
    response = client.post("/ingest/text", json={
        "text": "",
        "title": "Test Document",
    })
    assert response.status_code == 422


def test_ingest_text_missing_title_returns_422(client):
    response = client.post("/ingest/text", json={
        "text": "This is a test document.",
    })
    assert response.status_code == 422


def test_ingest_text_too_large_returns_413(client):
    upload_cfg = client.app.state.ctx.settings.system.upload
    original = upload_cfg.max_text_chars
    upload_cfg.max_text_chars = 10
    try:
        response = client.post("/ingest/text", json={
            "text": "x" * 11,
            "title": "Test Document",
        })
    finally:
        upload_cfg.max_text_chars = original
    assert response.status_code == 413


def test_ingest_text_custom_source_type(client):
    with patch("api.routers.ingest._submit_job") as mock_submit:
        mock_submit.return_value = None
        response = client.post("/ingest/text", json={
            "text": "Some HTML content.",
            "title": "Web Page",
            "source_type": "html",
        })
    assert response.status_code == 202
    assert "job_id" in response.json()
