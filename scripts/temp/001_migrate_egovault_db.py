# scripts/temp/001_migrate_egovault_db.py
"""
One-shot migration: egovault.db → vault.db + move tool_logs to .system.db.

Run once before first launch of v2 API:
    .venv/Scripts/python scripts/temp/001_migrate_egovault_db.py

Safe to re-run: if vault.db already exists, the rename step is skipped.
"""

import shutil
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import load_settings
from infrastructure.db import init_system_db, get_system_connection


def migrate(config_dir: Path | None = None) -> None:
    settings = load_settings(config_dir)
    data_dir = settings.vault_db_path.parent

    old_db = data_dir / "egovault.db"
    new_db = settings.vault_db_path
    system_db = settings.system_db_path

    # Step 1: Rename egovault.db → vault.db
    if old_db.exists() and not new_db.exists():
        print(f"Renaming {old_db} → {new_db}")
        shutil.move(str(old_db), str(new_db))
    elif new_db.exists():
        print(f"vault.db already exists at {new_db} — skipping rename")
    else:
        print(f"Neither {old_db} nor {new_db} found — nothing to rename")

    # Step 2: Init .system.db
    print(f"Initialising {system_db}")
    init_system_db(system_db)

    # Step 3: Move tool_logs from vault.db to .system.db (if any rows exist)
    if not new_db.exists():
        print("vault.db not found — skipping tool_logs migration")
        return

    vault_conn = sqlite3.connect(str(new_db))
    vault_conn.row_factory = sqlite3.Row
    try:
        rows = vault_conn.execute("SELECT * FROM tool_logs").fetchall()
    except sqlite3.OperationalError:
        rows = []
    print(f"Migrating {len(rows)} tool_log rows to .system.db")

    if rows:
        sys_conn = get_system_connection(system_db)
        sys_conn.executemany(
            "INSERT OR IGNORE INTO tool_logs "
            "(uid, tool_name, input_json, output_json, duration_ms, status, error, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["uid"], r["tool_name"], r["input_json"], r["output_json"],
              r["duration_ms"], r["status"], r["error"], r["timestamp"]) for r in rows],
        )
        sys_conn.commit()
        sys_conn.close()

    # Step 4: Drop tool_logs from vault.db
    vault_conn.execute("DROP TABLE IF EXISTS tool_logs")
    vault_conn.commit()
    vault_conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
