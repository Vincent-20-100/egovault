# tests/infrastructure/test_db_constraints.py
"""Tests for database security constraints."""

import sqlite3
import pytest
from pathlib import Path
from infrastructure.db import get_vault_connection, init_db


def test_foreign_keys_enabled(tmp_path):
    """PRAGMA foreign_keys must be ON for all vault connections."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    conn.close()
    assert result[0] == 1


def test_cascade_delete_chunks_when_source_deleted(tmp_path):
    """Deleting a source must cascade-delete its chunks."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)

    # Insert a source
    conn.execute(
        "INSERT INTO sources (uid, slug, source_type, status, date_added) VALUES (?, ?, ?, ?, ?)",
        ("s1", "test-source", "youtube", "raw", "2026-01-01"),
    )
    # Insert a chunk referencing the source
    conn.execute(
        "INSERT INTO chunks (uid, source_uid, position, content, token_count) VALUES (?, ?, ?, ?, ?)",
        ("c1", "s1", 0, "chunk text", 10),
    )
    conn.commit()

    # Delete the source
    conn.execute("DELETE FROM sources WHERE uid = ?", ("s1",))
    conn.commit()

    # Chunk should be gone (cascade)
    row = conn.execute("SELECT * FROM chunks WHERE uid = ?", ("c1",)).fetchone()
    conn.close()
    assert row is None


def test_slug_check_constraint_rejects_invalid(tmp_path):
    """Slugs with path traversal characters must be rejected by CHECK constraint."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO sources (uid, slug, source_type, status, date_added) VALUES (?, ?, ?, ?, ?)",
            ("s1", "../../../etc", "youtube", "raw", "2026-01-01"),
        )
    conn.close()


def test_slug_check_constraint_accepts_valid(tmp_path):
    """Valid kebab-case slugs must be accepted."""
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    conn.execute(
        "INSERT INTO sources (uid, slug, source_type, status, date_added) VALUES (?, ?, ?, ?, ?)",
        ("s1", "valid-slug-123", "youtube", "raw", "2026-01-01"),
    )
    conn.commit()
    row = conn.execute("SELECT slug FROM sources WHERE uid = 's1'").fetchone()
    conn.close()
    assert row[0] == "valid-slug-123"
