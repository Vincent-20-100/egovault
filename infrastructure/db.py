"""
SQLite + sqlite-vec database layer for EgoVault v2.

Single source of truth. Swappable: zero changes in core/ or tools/
if this file is replaced by a PostgreSQL implementation.

Schema defined in docs/architecture/DATABASES.md.
"""

import sqlite3
from datetime import timezone
from pathlib import Path

import sqlite_vec

from core.schemas import (
    Note, Source, ChunkResult, SearchResult, SearchFilters
)


def get_vault_connection(db_path: Path) -> sqlite3.Connection:
    """vault.db — loads sqlite-vec, WAL mode, 5s busy timeout."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_system_connection(db_path: Path) -> sqlite3.Connection:
    """.system.db — plain SQLite, WAL mode, 5s busy timeout."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn



_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    uid          TEXT PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL CHECK(slug GLOB '[a-z0-9][a-z0-9-]*'),
    source_type  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'raw',
    url          TEXT,
    title        TEXT,
    author       TEXT,
    date_added   DATE NOT NULL,
    date_source  DATE,
    media_path   TEXT,
    transcript   TEXT,
    raw_metadata TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    uid                 TEXT PRIMARY KEY,
    source_uid          TEXT REFERENCES sources(uid),
    slug                TEXT UNIQUE NOT NULL CHECK(slug GLOB '[a-z0-9][a-z0-9-]*'),
    note_type           TEXT,
    source_type         TEXT,
    generation_template TEXT,
    rating              INTEGER CHECK(rating BETWEEN 1 AND 5),
    sync_status         TEXT NOT NULL DEFAULT 'synced',
    title               TEXT NOT NULL,
    docstring           TEXT,
    body                TEXT NOT NULL,
    url                 TEXT,
    date_created        DATE NOT NULL,
    date_modified       DATE NOT NULL,
    language            TEXT DEFAULT 'fr'
);

CREATE TABLE IF NOT EXISTS chunks (
    uid          TEXT PRIMARY KEY,
    source_uid   TEXT NOT NULL REFERENCES sources(uid) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    content      TEXT NOT NULL,
    token_count  INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
    chunk_uid    TEXT,
    embedding    FLOAT[768]
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_vec USING vec0(
    note_uid     TEXT,
    embedding    FLOAT[768]
);

CREATE TABLE IF NOT EXISTS db_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    uid          TEXT PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,
    language     TEXT DEFAULT 'fr',
    date_created DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_uid TEXT REFERENCES notes(uid) ON DELETE CASCADE,
    tag_uid  TEXT REFERENCES tags(uid) ON DELETE CASCADE,
    PRIMARY KEY (note_uid, tag_uid)
);

CREATE TABLE IF NOT EXISTS tool_logs (
    uid         TEXT PRIMARY KEY,
    tool_name   TEXT NOT NULL,
    input_json  TEXT,
    output_json TEXT,
    duration_ms INTEGER,
    status      TEXT NOT NULL,
    error       TEXT,
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_METADATA_SQL = """
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_provider', 'ollama');
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_model', 'nomic-embed-text');
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_dim', '768');
"""

_SYSTEM_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'pending',
    job_type    TEXT NOT NULL,
    input       TEXT NOT NULL,
    result      TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_logs (
    uid         TEXT PRIMARY KEY,
    tool_name   TEXT NOT NULL,
    input_json  TEXT,
    output_json TEXT,
    duration_ms INTEGER,
    status      TEXT NOT NULL,
    error       TEXT,
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_system_db(db_path: Path) -> None:
    """Create jobs and tool_logs tables in .system.db. Safe to call repeatedly."""
    conn = get_system_connection(db_path)
    conn.executescript(_SYSTEM_SCHEMA_SQL)
    conn.commit()
    conn.close()
    from core.security import set_restrictive_permissions
    set_restrictive_permissions(db_path)


def init_db(db_path: Path) -> None:
    """
    Create all tables and virtual tables if they do not exist.
    Inserts initial db_metadata (embedding_provider, embedding_model, embedding_dim).
    Safe to call on an existing DB (idempotent).
    """
    conn = get_vault_connection(db_path)
    conn.executescript(_SCHEMA_SQL)
    conn.executescript(_METADATA_SQL)
    conn.commit()
    conn.close()
    from core.security import set_restrictive_permissions
    set_restrictive_permissions(db_path)


# ============================================================
# SOURCES
# ============================================================

def insert_source(db_path: Path, source: Source) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        """INSERT INTO sources
           (uid, slug, source_type, status, url, title, author,
            date_added, date_source, media_path, transcript, raw_metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source.uid, source.slug, source.source_type, source.status,
         source.url, source.title, source.author, source.date_added,
         source.date_source, source.media_path, source.transcript,
         source.raw_metadata),
    )
    conn.commit()
    conn.close()


def get_source(db_path: Path, uid: str) -> Source | None:
    conn = get_vault_connection(db_path)
    row = conn.execute("SELECT * FROM sources WHERE uid = ?", (uid,)).fetchone()
    conn.close()
    if row is None:
        return None
    return Source(**dict(row))


def update_source_status(db_path: Path, uid: str, status: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute("UPDATE sources SET status = ? WHERE uid = ?", (status, uid))
    conn.commit()
    conn.close()


def update_source_transcript(db_path: Path, uid: str, transcript: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute("UPDATE sources SET transcript = ? WHERE uid = ?", (transcript, uid))
    conn.commit()
    conn.close()


def list_sources_by_status(db_path: Path, status: str) -> list[Source]:
    conn = get_vault_connection(db_path)
    rows = conn.execute("SELECT * FROM sources WHERE status = ?", (status,)).fetchall()
    conn.close()
    return [Source(**dict(row)) for row in rows]


# ============================================================
# NOTES
# ============================================================

def insert_note(db_path: Path, note: Note) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        """INSERT INTO notes
           (uid, source_uid, slug, note_type, source_type, generation_template,
            rating, sync_status, title, docstring, body, url, date_created, date_modified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (note.uid, note.source_uid, note.slug, note.note_type, note.source_type,
         note.generation_template, note.rating, note.sync_status,
         note.title, note.docstring, note.body, note.url,
         note.date_created, note.date_modified),
    )
    conn.commit()
    conn.close()
    if note.tags:
        set_note_tags(db_path, note.uid, note.tags)


def _fetch_note_tags(conn: sqlite3.Connection, note_uid: str) -> list[str]:
    rows = conn.execute(
        "SELECT t.name FROM tags t JOIN note_tags nt ON nt.tag_uid = t.uid WHERE nt.note_uid = ?",
        (note_uid,),
    ).fetchall()
    return [row[0] for row in rows]


def get_note(db_path: Path, uid: str) -> Note | None:
    conn = get_vault_connection(db_path)
    row = conn.execute("SELECT * FROM notes WHERE uid = ?", (uid,)).fetchone()
    if row is None:
        conn.close()
        return None
    data = dict(row)
    tags = _fetch_note_tags(conn, uid)
    conn.close()
    data["tags"] = tags if tags else ["untagged"]
    return Note(**data)


def update_note(db_path: Path, uid: str, fields: dict) -> None:
    if not fields:
        return
    allowed = {
        "title", "docstring", "body", "note_type", "source_type",
        "rating", "sync_status", "date_modified", "url", "status",
    }
    set_clauses = ", ".join(f"{k} = ?" for k in fields if k in allowed)
    values = [v for k, v in fields.items() if k in allowed]
    if not set_clauses:
        return
    conn = get_vault_connection(db_path)
    conn.execute(f"UPDATE notes SET {set_clauses} WHERE uid = ?", values + [uid])
    conn.commit()
    conn.close()


def get_note_by_source(db_path: Path, source_uid: str) -> Note | None:
    conn = get_vault_connection(db_path)
    row = conn.execute(
        "SELECT * FROM notes WHERE source_uid = ?", (source_uid,)
    ).fetchone()
    if row is None:
        conn.close()
        return None
    data = dict(row)
    tags = _fetch_note_tags(conn, data["uid"])
    conn.close()
    data["tags"] = tags if tags else ["untagged"]
    return Note(**data)


def list_notes_by_sync_status(db_path: Path, sync_status: str) -> list[Note]:
    conn = get_vault_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM notes WHERE sync_status = ?", (sync_status,)
    ).fetchall()
    results = []
    for row in rows:
        data = dict(row)
        tags = _fetch_note_tags(conn, data["uid"])
        data["tags"] = tags if tags else ["untagged"]
        results.append(Note(**data))
    conn.close()
    return results


# ============================================================
# CHUNKS
# ============================================================

def insert_chunks(db_path: Path, source_uid: str, chunks: list[ChunkResult]) -> None:
    conn = get_vault_connection(db_path)
    conn.executemany(
        "INSERT INTO chunks (uid, source_uid, position, content, token_count) VALUES (?, ?, ?, ?, ?)",
        [(c.uid, source_uid, c.position, c.content, c.token_count) for c in chunks],
    )
    conn.commit()
    conn.close()


def delete_chunks_for_source(db_path: Path, source_uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute("DELETE FROM chunks WHERE source_uid = ?", (source_uid,))
    conn.commit()
    conn.close()


# ============================================================
# VECTORS (sqlite-vec)
# ============================================================

def insert_chunk_embeddings(db_path: Path, chunk_uid: str, embedding: list[float]) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        "INSERT INTO chunks_vec(chunk_uid, embedding) VALUES (?, ?)",
        (chunk_uid, sqlite_vec.serialize_float32(embedding)),
    )
    conn.commit()
    conn.close()


def insert_note_embedding(db_path: Path, note_uid: str, embedding: list[float]) -> None:
    conn = get_vault_connection(db_path)
    conn.execute(
        "INSERT INTO notes_vec(note_uid, embedding) VALUES (?, ?)",
        (note_uid, sqlite_vec.serialize_float32(embedding)),
    )
    conn.commit()
    conn.close()


def delete_note_embedding(db_path: Path, note_uid: str) -> None:
    conn = get_vault_connection(db_path)
    conn.execute("DELETE FROM notes_vec WHERE note_uid = ?", (note_uid,))
    conn.commit()
    conn.close()


def search_chunks(
    db_path: Path, query_embedding: list[float], filters: SearchFilters | None, limit: int
) -> list[SearchResult]:
    conn = get_vault_connection(db_path)
    embedding_bytes = sqlite_vec.serialize_float32(query_embedding)
    rows = conn.execute(
        """SELECT c.content, c.uid AS chunk_uid, c.source_uid, s.title, cv.distance
           FROM chunks_vec cv
           JOIN chunks c ON c.uid = cv.chunk_uid
           JOIN sources s ON s.uid = c.source_uid
           WHERE cv.embedding MATCH ? AND k = ?
           ORDER BY cv.distance""",
        (embedding_bytes, limit),
    ).fetchall()
    conn.close()
    return [
        SearchResult(
            chunk_uid=row["chunk_uid"],
            source_uid=row["source_uid"],
            content=row["content"],
            title=row["title"] or "",
            distance=row["distance"],
        )
        for row in rows
    ]


def search_notes(
    db_path: Path, query_embedding: list[float], filters: SearchFilters | None, limit: int
) -> list[SearchResult]:
    conn = get_vault_connection(db_path)
    embedding_bytes = sqlite_vec.serialize_float32(query_embedding)
    rows = conn.execute(
        """SELECT n.uid AS note_uid, n.source_uid, n.title, n.docstring AS content, nv.distance
           FROM notes_vec nv
           JOIN notes n ON n.uid = nv.note_uid
           WHERE nv.embedding MATCH ? AND k = ?
           ORDER BY nv.distance""",
        (embedding_bytes, limit),
    ).fetchall()
    conn.close()
    return [
        SearchResult(
            note_uid=row["note_uid"],
            source_uid=row["source_uid"],
            content=row["content"] or "",
            title=row["title"],
            distance=row["distance"],
        )
        for row in rows
    ]


# ============================================================
# TAGS
# ============================================================

def upsert_tags(db_path: Path, names: list[str], language: str) -> list[str]:
    """Insert tags that don't exist yet. Return list of tag UIDs."""
    from datetime import date
    from core.uid import generate_uid
    conn = get_vault_connection(db_path)
    today = date.today().isoformat()
    tag_uids = []
    for name in names:
        existing = conn.execute("SELECT uid FROM tags WHERE name = ?", (name,)).fetchone()
        if existing:
            tag_uids.append(existing["uid"])
        else:
            uid = generate_uid()
            conn.execute(
                "INSERT INTO tags (uid, name, language, date_created) VALUES (?, ?, ?, ?)",
                (uid, name, language, today),
            )
            tag_uids.append(uid)
    conn.commit()
    conn.close()
    return tag_uids


def set_note_tags(db_path: Path, note_uid: str, tag_names: list[str]) -> None:
    """Full replace: delete existing note_tags, reinsert with new tag list."""
    conn = get_vault_connection(db_path)
    conn.execute("DELETE FROM note_tags WHERE note_uid = ?", (note_uid,))
    conn.commit()
    conn.close()
    if not tag_names:
        return
    tag_uids = upsert_tags(db_path, tag_names, "fr")
    conn = get_vault_connection(db_path)
    conn.executemany(
        "INSERT INTO note_tags (note_uid, tag_uid) VALUES (?, ?)",
        [(note_uid, tag_uid) for tag_uid in tag_uids],
    )
    conn.commit()
    conn.close()


# ============================================================
# TOOL LOGS
# ============================================================

def list_notes(
    db_path: Path,
    note_type: str | None,
    tags: list[str] | None,
    limit: int,
    offset: int,
    status: str | None = None,
) -> list[Note]:
    conn = get_vault_connection(db_path)
    params: list = []
    where_clauses: list[str] = []

    if note_type:
        where_clauses.append("n.note_type = ?")
        params.append(note_type)

    if tags:
        placeholders = ",".join("?" * len(tags))
        where_clauses.append(
            f"n.uid IN (SELECT nt.note_uid FROM note_tags nt "
            f"JOIN tags t ON t.uid = nt.tag_uid WHERE t.name IN ({placeholders}))"
        )
        params.extend(tags)

    if status:
        where_clauses.append("n.status = ?")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    query = f"SELECT n.* FROM notes n {where_sql} ORDER BY n.date_created DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    results = []
    for row in rows:
        data = dict(row)
        data["tags"] = _fetch_note_tags(conn, data["uid"])
        if not data["tags"]:
            data["tags"] = ["untagged"]
        results.append(Note(**data))
    conn.close()
    return results


def list_sources(
    db_path: Path,
    status: str | None,
    limit: int,
    offset: int,
) -> list[Source]:
    conn = get_vault_connection(db_path)
    if status:
        rows = conn.execute(
            "SELECT * FROM sources WHERE status = ? ORDER BY date_added DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sources ORDER BY date_added DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    conn.close()
    return [Source(**dict(row)) for row in rows]


# ============================================================
# JOBS (.system.db)
# ============================================================

def insert_job(db_path: Path, job_id: str, job_type: str, input_data: dict) -> None:
    import json
    from datetime import datetime
    now = datetime.now(timezone.utc).isoformat()
    conn = get_system_connection(db_path)
    conn.execute(
        "INSERT INTO jobs (id, status, job_type, input, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "pending", job_type, json.dumps(input_data), now, now),
    )
    conn.commit()
    conn.close()


def get_job(db_path: Path, job_id: str) -> dict | None:
    import json
    conn = get_system_connection(db_path)
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["input"] = json.loads(d["input"]) if d["input"] else {}
    d["result"] = json.loads(d["result"]) if d["result"] else None
    return d


def update_job_status(db_path: Path, job_id: str, status: str) -> None:
    from datetime import datetime
    conn = get_system_connection(db_path)
    conn.execute(
        "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now(timezone.utc).isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def update_job_done(db_path: Path, job_id: str, result: dict) -> None:
    import json
    from datetime import datetime
    conn = get_system_connection(db_path)
    conn.execute(
        "UPDATE jobs SET status = 'done', result = ?, updated_at = ? WHERE id = ?",
        (json.dumps(result), datetime.now(timezone.utc).isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def update_job_failed(db_path: Path, job_id: str, error: str) -> None:
    from datetime import datetime
    conn = get_system_connection(db_path)
    conn.execute(
        "UPDATE jobs SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
        (error, datetime.now(timezone.utc).isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def list_jobs(db_path: Path, status: str | None = None, limit: int = 20) -> list[dict]:
    import json
    conn = get_system_connection(db_path)
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["input"] = json.loads(d["input"]) if d["input"] else {}
        d["result"] = json.loads(d["result"]) if d["result"] else None
        result.append(d)
    return result


def mark_orphan_jobs_failed(db_path: Path) -> None:
    """Mark pending/running jobs as failed — called at API startup after process restart."""
    from datetime import datetime
    conn = get_system_connection(db_path)
    conn.execute(
        "UPDATE jobs SET status = 'failed', error = 'process restarted', updated_at = ? "
        "WHERE status IN ('pending', 'running')",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    conn.close()


def insert_tool_log(
    db_path: Path,
    tool_name: str,
    input_json: str | None,
    output_json: str | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
) -> None:
    from core.uid import generate_uid
    conn = get_vault_connection(db_path)
    conn.execute(
        """INSERT INTO tool_logs (uid, tool_name, input_json, output_json, duration_ms, status, error)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (generate_uid(), tool_name, input_json, output_json, duration_ms, status, error),
    )
    conn.commit()
    conn.close()
