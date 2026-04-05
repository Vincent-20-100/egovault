import sqlite3
import pytest
from pathlib import Path
from infrastructure.db import init_db


def _get_columns(db_path: Path, table: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    conn.close()
    return [row[1] for row in rows]


def test_migration_adds_previous_status(tmp_path):
    db = tmp_path / "vault.db"
    init_db(db)
    from scripts.temp._002_add_previous_status import run
    run(db)
    assert "previous_status" in _get_columns(db, "sources")
    assert "previous_sync_status" in _get_columns(db, "notes")


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "vault.db"
    init_db(db)
    from scripts.temp._002_add_previous_status import run
    run(db)
    run(db)  # second call must not raise
    assert "previous_status" in _get_columns(db, "sources")
