import io
from unittest.mock import patch


def test_ingest_youtube_returns_202(client):
    with patch("api.routers.ingest._submit_job") as mock_submit:
        mock_submit.return_value = None
        response = client.post("/ingest/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 36  # UUID4


def test_ingest_youtube_bad_url(client):
    response = client.post("/ingest/youtube", json={"url": "not-a-youtube-url"})
    assert response.status_code == 400
    assert "youtube" in response.json()["detail"].lower()


def test_ingest_audio_returns_202(client):
    with patch("api.routers.ingest._submit_job") as mock_submit:
        mock_submit.return_value = None
        audio_bytes = b"fake audio content"
        response = client.post(
            "/ingest/audio",
            files={"file": ("podcast.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
        )
    assert response.status_code == 202
    assert "job_id" in response.json()


def test_ingest_audio_unsupported_extension(client):
    response = client.post(
        "/ingest/audio",
        files={"file": ("malware.exe", io.BytesIO(b"bad"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_ingest_pdf_returns_202(client):
    with patch("api.routers.ingest._submit_job") as mock_submit:
        mock_submit.return_value = None
        response = client.post(
            "/ingest/pdf",
            files={"file": ("paper.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert response.status_code == 202
    assert "job_id" in response.json()


def test_ingest_pdf_unsupported_extension(client):
    response = client.post(
        "/ingest/pdf",
        files={"file": ("image.png", io.BytesIO(b"PNG"), "image/png")},
    )
    assert response.status_code == 400


def test_audio_upload_too_large_returns_413(client):
    """Uploads exceeding configured limit should return 413."""
    upload_cfg = client.app.state.settings.system.upload
    original = upload_cfg.max_audio_mb
    upload_cfg.max_audio_mb = 1  # 1 MB
    try:
        resp = client.post(
            "/ingest/audio",
            files={"file": ("test.mp3", io.BytesIO(b"x" * (1024 * 1024 + 1)), "audio/mpeg")},
        )
    finally:
        upload_cfg.max_audio_mb = original
    assert resp.status_code == 413


def test_pdf_upload_too_large_returns_413(client):
    """Uploads exceeding configured limit should return 413."""
    upload_cfg = client.app.state.settings.system.upload
    original = upload_cfg.max_pdf_mb
    upload_cfg.max_pdf_mb = 1  # 1 MB
    try:
        resp = client.post(
            "/ingest/pdf",
            files={"file": ("test.pdf", io.BytesIO(b"x" * (1024 * 1024 + 1)), "application/pdf")},
        )
    finally:
        upload_cfg.max_pdf_mb = original
    assert resp.status_code == 413
