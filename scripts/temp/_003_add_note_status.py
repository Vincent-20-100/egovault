"""
One-shot migration: add status column to notes table.

status TEXT NOT NULL DEFAULT 'active'
All existing notes keep status = 'active' (no data loss).
Safe to re-run (idempotent).
"""
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent.parent / "egovault-user" / "data" / "vault.db"


def run(db_path: Path = DEFAULT_DB) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        conn.commit()
        print(f"Migration applied: status column added to notes ({db_path})")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column already exists — skipping ({db_path})")
        else:
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    run(path)
