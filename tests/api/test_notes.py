import pytest
from core.schemas import Note
from infrastructure.db import insert_note


def _make_note(uid: str, slug: str, title: str, note_type: str = "synthese",
               rating: int | None = None, tags: list[str] | None = None) -> Note:
    return Note(
        uid=uid, source_uid=None, slug=slug, note_type=note_type,
        source_type="youtube", generation_template=None, rating=rating,
        sync_status="synced", title=title, docstring="A short description.",
        body="# Title\n\nBody content.", url=None,
        date_created="2026-01-01", date_modified="2026-01-01",
        tags=tags or ["untagged"],
    )


@pytest.fixture(scope="session", autouse=True)
def seed_notes(tmp_settings):
    from infrastructure.db import get_note
    for uid, slug, title in [
        ("note-a", "note-a", "Note Alpha"),
        ("note-b", "note-b", "Note Beta"),
    ]:
        if get_note(tmp_settings.vault_db_path, uid) is None:
            insert_note(tmp_settings.vault_db_path, _make_note(uid, slug, title))


def test_get_notes_returns_list(client):
    response = client.get("/notes")
    assert response.status_code == 200
    notes = response.json()
    assert isinstance(notes, list)
    assert len(notes) >= 2


def test_get_notes_filter_by_type(client):
    response = client.get("/notes?note_type=synthese")
    assert response.status_code == 200
    for note in response.json():
        assert note["note_type"] == "synthese"


def test_get_note_by_uid(client):
    response = client.get("/notes/note-a")
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == "note-a"
    assert "body" in data


def test_get_note_not_found(client):
    response = client.get("/notes/does-not-exist")
    assert response.status_code == 404


def test_patch_note_rating(client):
    response = client.patch("/notes/note-a", json={"rating": 4})
    assert response.status_code == 200
    assert response.json()["rating"] == 4


def test_patch_note_invalid_rating(client):
    response = client.patch("/notes/note-a", json={"rating": 99})
    assert response.status_code == 422


def test_patch_note_tags(client):
    response = client.patch("/notes/note-a", json={"tags": ["economics", "theory"]})
    assert response.status_code == 200
    assert "economics" in response.json()["tags"]


def test_patch_note_not_found(client):
    response = client.patch("/notes/ghost-note", json={"rating": 3})
    assert response.status_code == 404
