"""
Migration 002 — add previous_status columns for soft-delete tracking.

Adds:
  sources.previous_status      TEXT  (NULL default)
  notes.previous_sync_status   TEXT  (NULL default)

Idempotent: silently skips if column already exists.
"""

import sqlite3
from pathlib import Path
from core.config import load_settings


def run(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    for sql in [
        "ALTER TABLE sources ADD COLUMN previous_status TEXT",
        "ALTER TABLE notes ADD COLUMN previous_sync_status TEXT",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                raise
    conn.commit()
    conn.close()
    print(f"Migration 002 applied to {db_path}")


if __name__ == "__main__":
    settings = load_settings()
    run(settings.vault_db_path)
    print("Done.")
