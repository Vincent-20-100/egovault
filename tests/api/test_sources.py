import pytest
from core.schemas import Source
from infrastructure.db import get_source, insert_source


@pytest.fixture(scope="session", autouse=True)
def seed_sources(tmp_settings):
    for uid, slug, st in [
        ("src-1", "src-yt-1", "youtube"),
        ("src-2", "src-pdf-1", "pdf"),
    ]:
        if get_source(tmp_settings.vault_db_path, uid) is None:
            insert_source(tmp_settings.vault_db_path, Source(
                uid=uid, slug=slug, source_type=st, status="vaulted",
                url="https://example.com", title=f"Source {uid}",
                date_added="2026-01-01",
            ))


def test_get_sources_returns_list(client):
    response = client.get("/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


def test_get_sources_filter_by_status(client):
    response = client.get("/sources?status=vaulted")
    assert response.status_code == 200
    for s in response.json():
        assert s["status"] == "vaulted"


def test_get_source_by_uid(client):
    response = client.get("/sources/src-1")
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == "src-1"
    assert "transcript" in data


def test_get_source_not_found(client):
    response = client.get("/sources/ghost-source")
    assert response.status_code == 404
