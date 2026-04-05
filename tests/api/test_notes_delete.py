import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from core.schemas import DeleteNoteResult, RestoreNoteResult
from core.errors import NotFoundError, ConflictError


@pytest.fixture
def client(tmp_settings):
    from api.main import create_app
    app = create_app(tmp_settings)
    return TestClient(app)


def test_delete_note_soft(client):
    result = DeleteNoteResult(uid="nuid-1", action="soft_deleted")
    with patch("api.routers.notes.delete_note", return_value=result):
        resp = client.delete("/notes/nuid-1")
    assert resp.status_code == 200
    assert resp.json()["action"] == "soft_deleted"


def test_delete_note_hard(client):
    result = DeleteNoteResult(uid="nuid-1", action="hard_deleted")
    with patch("api.routers.notes.delete_note", return_value=result):
        resp = client.delete("/notes/nuid-1?force=true")
    assert resp.status_code == 200
    assert resp.json()["action"] == "hard_deleted"


def test_delete_note_not_found(client):
    with patch("api.routers.notes.delete_note", side_effect=NotFoundError("Note", "nuid-1")):
        resp = client.delete("/notes/nuid-1")
    assert resp.status_code == 404


def test_delete_note_conflict(client):
    with patch("api.routers.notes.delete_note", side_effect=ConflictError("Note", "nuid-1", "already pending")):
        resp = client.delete("/notes/nuid-1")
    assert resp.status_code == 409


def test_restore_note(client):
    result = RestoreNoteResult(uid="nuid-1", restored_sync_status="synced")
    with patch("api.routers.notes.restore_note", return_value=result):
        resp = client.post("/notes/nuid-1/restore")
    assert resp.status_code == 200
    assert resp.json()["restored_sync_status"] == "synced"
