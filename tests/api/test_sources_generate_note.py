"""Tests for the generate-note-from-source API endpoint."""

import pytest
from datetime import date

from tests.conftest import make_embedding

from core.schemas import NoteContentInput, Source, Note
from infrastructure.db import get_source, insert_source, insert_note as db_insert_note


def _make_content():
    return NoteContentInput(
        title="Generated Note Title",
        docstring="What this note is about.",
        body="# Generated Note\n\nBody content here, enough text.",
        tags=["test-tag"],
        note_type=None,
        source_type=None,
    )


@pytest.fixture(scope="session", autouse=True)
def seed(tmp_settings):
    """Seed once per session — matches test_notes.py pattern."""
    db = tmp_settings.vault_db_path
    if get_source(db, "gen-src-1") is None:
        insert_source(db, Source(
            uid="gen-src-1", slug="gen-src-1", source_type="youtube",
            status="rag_ready", url="https://example.com",
            title="Source For Generation",
            transcript="This is a test transcript long enough.",
            date_added=date.today().isoformat(),
        ))
    if get_source(db, "gen-src-raw") is None:
        insert_source(db, Source(
            uid="gen-src-raw", slug="gen-src-raw", source_type="youtube",
            status="raw", date_added=date.today().isoformat(),
        ))
    if get_source(db, "gen-src-conflict") is None:
        insert_source(db, Source(
            uid="gen-src-conflict", slug="gen-src-conflict",
            source_type="youtube", status="rag_ready",
            transcript="Transcript.", date_added=date.today().isoformat(),
        ))
        db_insert_note(db, Note(
            uid="note-for-conflict", source_uid="gen-src-conflict",
            slug="note-for-conflict", note_type=None, source_type=None,
            generation_template=None, rating=None, sync_status="synced",
            title="Existing Note", docstring="Already exists.",
            body="Body content here.", url=None,
            date_created=date.today().isoformat(),
            date_modified=date.today().isoformat(),
            tags=["test-tag"],
        ))


def test_generate_note_from_source_success(client, tmp_settings):
    vault_path = tmp_settings.vault_path
    vault_path.mkdir(parents=True, exist_ok=True)

    # Patch ctx callables directly — infrastructure patches don't reach ctx closures
    ctx = client.app.state.ctx
    original_generate = ctx.generate
    original_embed = ctx.embed
    ctx.generate = lambda content, metadata, template: _make_content()
    ctx.embed = lambda text: make_embedding()
    try:
        response = client.post("/sources/gen-src-1/generate-note")
    finally:
        ctx.generate = original_generate
        ctx.embed = original_embed

    assert response.status_code == 200
    data = response.json()
    assert data["note"]["source_uid"] == "gen-src-1"


def test_generate_note_source_not_found(client):
    response = client.post("/sources/nonexistent-gen/generate-note")
    assert response.status_code == 404


def test_generate_note_source_not_rag_ready_422(client):
    response = client.post("/sources/gen-src-raw/generate-note")
    assert response.status_code == 422


def test_generate_note_conflict_409(client, tmp_settings):
    response = client.post("/sources/gen-src-conflict/generate-note")
    assert response.status_code == 409


def test_generate_note_template_param(client, tmp_settings):
    db = tmp_settings.vault_db_path
    if get_source(db, "gen-src-tpl") is None:
        insert_source(db, Source(
            uid="gen-src-tpl", slug="gen-src-tpl", source_type="youtube",
            status="rag_ready", transcript="Transcript.",
            date_added=date.today().isoformat(),
        ))
    vault_path = tmp_settings.vault_path
    vault_path.mkdir(parents=True, exist_ok=True)

    ctx = client.app.state.ctx
    original_generate = ctx.generate
    original_embed = ctx.embed
    calls = []
    ctx.generate = lambda content, metadata, template: (calls.append(template), _make_content())[1]
    ctx.embed = lambda text: make_embedding()
    try:
        response = client.post("/sources/gen-src-tpl/generate-note?template=standard")
    finally:
        ctx.generate = original_generate
        ctx.embed = original_embed

    assert response.status_code == 200
    assert calls == ["standard"]
