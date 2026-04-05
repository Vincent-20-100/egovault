import pytest
from core.schemas import Note, Source
from infrastructure.db import insert_note, insert_source
from datetime import date


def _make_note(uid: str, slug: str, status: str = "draft", source_uid: str | None = None):
    return Note(
        uid=uid, source_uid=source_uid, slug=slug, note_type=None,
        source_type=None, generation_template="standard", rating=None,
        sync_status="synced", title=f"Note {uid}", docstring="A short description.",
        body="# Title\n\nBody content here.", url=None, status=status,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )


def _make_source(uid: str, status: str = "rag_ready"):
    return Source(
        uid=uid, slug=uid, source_type="youtube", status=status,
        url="https://example.com", title=f"Source {uid}",
        date_added=date.today().isoformat(),
    )


@pytest.fixture(scope="module", autouse=True)
def seed(tmp_settings):
    insert_source(tmp_settings.vault_db_path, _make_source("approve-src-1"))
    insert_note(tmp_settings.vault_db_path,
                _make_note("approve-note-1", "approve-note-1", "draft", "approve-src-1"))
    insert_note(tmp_settings.vault_db_path,
                _make_note("approve-note-2", "approve-note-2", "draft"))
    insert_note(tmp_settings.vault_db_path,
                _make_note("approve-note-3", "approve-note-3", "active"))


def test_approve_draft_note_with_source(client):
    response = client.post("/notes/approve-note-1/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    source = client.app.state.ctx.db.get_source("approve-src-1")
    assert source.status == "vaulted"


def test_approve_draft_note_without_source(client):
    response = client.post("/notes/approve-note-2/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_approve_not_found(client):
    response = client.post("/notes/nonexistent-uid/approve")
    assert response.status_code == 404


def test_approve_already_active_returns_409(client):
    response = client.post("/notes/approve-note-3/approve")
    assert response.status_code == 409
