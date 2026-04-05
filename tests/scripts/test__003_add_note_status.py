import sqlite3
import pytest
from pathlib import Path


def test_migration_adds_status_column(tmp_db):
    from scripts.temp._003_add_note_status import run
    run(tmp_db)
    conn = sqlite3.connect(tmp_db)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]
    conn.close()
    assert "status" in cols


def test_migration_existing_notes_default_active(tmp_db):
    from scripts.temp._003_add_note_status import run
    from infrastructure.db import insert_note
    from core.schemas import Note
    from datetime import date

    note = Note(
        uid="n1", source_uid=None, slug="test-note", note_type=None,
        source_type=None, generation_template=None, rating=None,
        sync_status="synced", title="Test Note", docstring="Short description.",
        body="Body content here for testing.", url=None,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    insert_note(tmp_db, note)
    run(tmp_db)
    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT status FROM notes WHERE uid = 'n1'").fetchone()
    conn.close()
    assert row[0] == "active"


def test_migration_idempotent(tmp_db):
    from scripts.temp._003_add_note_status import run
    run(tmp_db)
    run(tmp_db)  # must not raise
