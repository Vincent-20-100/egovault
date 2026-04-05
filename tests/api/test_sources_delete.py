import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from core.schemas import DeleteSourceResult, RestoreSourceResult, PurgeResult
from core.errors import NotFoundError, ConflictError


@pytest.fixture
def client(tmp_settings):
    from api.main import create_app
    app = create_app(tmp_settings)
    return TestClient(app)


def test_delete_source_soft(client):
    result = DeleteSourceResult(uid="suid-1", action="soft_deleted", media_deleted=False, orphaned_note_uids=[])
    with patch("api.routers.sources.delete_source", return_value=result):
        resp = client.delete("/sources/suid-1")
    assert resp.status_code == 200
    assert resp.json()["action"] == "soft_deleted"


def test_delete_source_hard(client):
    result = DeleteSourceResult(uid="suid-1", action="hard_deleted", media_deleted=False, orphaned_note_uids=[])
    with patch("api.routers.sources.delete_source", return_value=result):
        resp = client.delete("/sources/suid-1?force=true")
    assert resp.status_code == 200


def test_delete_source_not_found(client):
    with patch("api.routers.sources.delete_source", side_effect=NotFoundError("Source", "suid-1")):
        resp = client.delete("/sources/suid-1")
    assert resp.status_code == 404


def test_restore_source(client):
    result = RestoreSourceResult(uid="suid-1", restored_status="rag_ready")
    with patch("api.routers.sources.restore_source", return_value=result):
        resp = client.post("/sources/suid-1/restore")
    assert resp.status_code == 200


def test_purge(client):
    result = PurgeResult(notes_purged=2, sources_purged=1, media_files_deleted=1)
    with patch("api.routers.vault.purge", return_value=result):
        resp = client.post("/vault/purge")
    assert resp.status_code == 200
    assert resp.json()["notes_purged"] == 2
