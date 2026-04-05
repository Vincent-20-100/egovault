import pytest
from pathlib import Path

from tests.conftest import make_embedding


def test_get_vault_connection_loads_sqlite_vec(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_vault_connection(db_file)
    # sqlite-vec provides vec_f32 SQL function
    result = conn.execute("SELECT vec_length(vec_f32('[1.0, 2.0, 3.0]'))").fetchone()
    assert result[0] == 3
    conn.close()


def test_get_vault_connection_has_wal(tmp_path):
    from infrastructure.db import get_vault_connection, init_db
    db = tmp_path / "vault.db"
    init_db(db)
    conn = get_vault_connection(db)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    conn.close()
    assert mode == "wal"
    assert timeout == 5000


def test_get_system_connection_has_wal(tmp_path):
    from infrastructure.db import get_system_connection
    db = tmp_path / ".system.db"
    conn = get_system_connection(db)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    conn.close()
    assert mode == "wal"
    assert timeout == 5000


def test_init_db_creates_all_tables(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_vault_connection(db_file)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'shadow')"
        ).fetchall()
    }
    conn.close()
    for expected in ["sources", "notes", "chunks", "tags", "note_tags", "tool_logs", "db_metadata"]:
        assert expected in tables, f"Table '{expected}' not found. Found: {tables}"


def test_init_db_creates_vec_virtual_tables(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_vault_connection(db_file)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master").fetchall()}
    assert "chunks_vec" in tables
    assert "notes_vec" in tables
    conn.close()


def test_init_db_inserts_metadata(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_vault_connection(db_file)
    meta = dict(conn.execute("SELECT key, value FROM db_metadata").fetchall())
    conn.close()
    assert meta["embedding_provider"] == "ollama"
    assert meta["embedding_model"] == "nomic-embed-text"
    assert meta["embedding_dim"] == "768"


def test_init_db_idempotent(tmp_path):
    from infrastructure.db import init_db
    db_file = tmp_path / "test.db"
    init_db(db_file)
    init_db(db_file)  # second call must not raise


def test_init_db_creates_vec_tables_with_custom_dims(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "custom_dims.db"
    init_db(db_file, dims=512)
    conn = get_vault_connection(db_file)
    meta = dict(conn.execute("SELECT key, value FROM db_metadata").fetchall())
    conn.close()
    assert meta["embedding_dim"] == "512"


def test_init_db_metadata_reflects_params(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "params.db"
    init_db(db_file, dims=1536, provider="openai", model="text-embedding-3-small")
    conn = get_vault_connection(db_file)
    meta = dict(conn.execute("SELECT key, value FROM db_metadata").fetchall())
    conn.close()
    assert meta["embedding_dim"] == "1536"
    assert meta["embedding_provider"] == "openai"
    assert meta["embedding_model"] == "text-embedding-3-small"


def test_init_db_warns_on_dim_mismatch(tmp_path, caplog):
    import logging
    from infrastructure.db import init_db
    db_file = tmp_path / "mismatch.db"
    init_db(db_file, dims=768)
    with caplog.at_level(logging.WARNING, logger="infrastructure.db"):
        init_db(db_file, dims=1536)
    assert any("do not match" in r.message for r in caplog.records)


def test_init_db_no_warning_when_dims_match(tmp_path, caplog):
    import logging
    from infrastructure.db import init_db
    db_file = tmp_path / "match.db"
    init_db(db_file, dims=768)
    with caplog.at_level(logging.WARNING, logger="infrastructure.db"):
        init_db(db_file, dims=768)
    assert not any("does not match" in r.message for r in caplog.records)


# ---- Sources CRUD ----

def _make_source():
    from core.schemas import Source
    return Source(
        uid="src-uid-1",
        slug="test-source",
        source_type="youtube",
        status="raw",
        url="https://youtube.com/watch?v=test",
        title="Test Source",
        author=None,
        date_added="2026-03-26",
        date_source=None,
        media_path=None,
        transcript=None,
        raw_metadata=None,
    )


def test_insert_and_get_source(tmp_db):
    from infrastructure.db import insert_source, get_source
    source = _make_source()
    insert_source(tmp_db, source)
    retrieved = get_source(tmp_db, "src-uid-1")
    assert retrieved is not None
    assert retrieved.slug == "test-source"
    assert retrieved.source_type == "youtube"


def test_get_source_not_found(tmp_db):
    from infrastructure.db import get_source
    assert get_source(tmp_db, "nonexistent") is None


def test_update_source_status(tmp_db):
    from infrastructure.db import insert_source, update_source_status, get_source
    source = _make_source()
    insert_source(tmp_db, source)
    update_source_status(tmp_db, "src-uid-1", "rag_ready")
    assert get_source(tmp_db, "src-uid-1").status == "rag_ready"


def test_list_sources_by_status(tmp_db):
    from infrastructure.db import insert_source, list_sources_by_status
    from core.schemas import Source
    s1 = _make_source()
    s2 = Source(**{**s1.model_dump(), "uid": "src-uid-2", "slug": "test-source-2"})
    s3 = Source(**{**s1.model_dump(), "uid": "src-uid-3", "slug": "test-source-3", "status": "rag_ready"})
    insert_source(tmp_db, s1)
    insert_source(tmp_db, s2)
    insert_source(tmp_db, s3)
    raw_sources = list_sources_by_status(tmp_db, "raw")
    assert len(raw_sources) == 2
    assert all(s.status == "raw" for s in raw_sources)


# ---- Notes CRUD ----

def _make_note():
    from core.schemas import Note
    return Note(
        uid="note-uid-1",
        source_uid=None,
        slug="test-note",
        note_type="reflexion",
        source_type=None,
        generation_template=None,
        rating=None,
        sync_status="synced",
        title="Test Note",
        docstring="A test note for testing.",
        body="This is the body of the test note.",
        url=None,
        date_created="2026-03-26",
        date_modified="2026-03-26",
        tags=["test-tag"],
    )


def test_insert_and_get_note(tmp_db):
    from infrastructure.db import insert_note, get_note
    note = _make_note()
    insert_note(tmp_db, note)
    retrieved = get_note(tmp_db, "note-uid-1")
    assert retrieved is not None
    assert retrieved.title == "Test Note"
    assert retrieved.slug == "test-note"


def test_get_note_not_found(tmp_db):
    from infrastructure.db import get_note
    assert get_note(tmp_db, "nonexistent") is None


def test_update_note_fields(tmp_db):
    from infrastructure.db import insert_note, update_note, get_note
    note = _make_note()
    insert_note(tmp_db, note)
    update_note(tmp_db, "note-uid-1", {"rating": 4, "sync_status": "needs_re_embedding"})
    updated = get_note(tmp_db, "note-uid-1")
    assert updated.rating == 4
    assert updated.sync_status == "needs_re_embedding"


def test_get_note_by_source(tmp_db):
    from infrastructure.db import insert_source, insert_note, get_note_by_source
    from core.schemas import Note
    source = _make_source()
    insert_source(tmp_db, source)
    note = Note(**{**_make_note().model_dump(), "source_uid": "src-uid-1"})
    insert_note(tmp_db, note)
    result = get_note_by_source(tmp_db, "src-uid-1")
    assert result is not None
    assert result.uid == "note-uid-1"


def test_list_notes_by_sync_status(tmp_db):
    from infrastructure.db import insert_note, list_notes_by_sync_status
    from core.schemas import Note
    n1 = _make_note()
    n2 = Note(**{**n1.model_dump(), "uid": "note-uid-2", "slug": "test-note-2",
                 "sync_status": "needs_re_embedding"})
    insert_note(tmp_db, n1)
    insert_note(tmp_db, n2)
    synced = list_notes_by_sync_status(tmp_db, "synced")
    assert len(synced) == 1
    assert synced[0].uid == "note-uid-1"


# ---- Chunks ----

def _make_chunks():
    from core.schemas import ChunkResult
    return [
        ChunkResult(uid=f"chunk-{i}", position=i, content=f"content {i}", token_count=100)
        for i in range(3)
    ]


def test_insert_and_retrieve_chunks(tmp_db):
    from infrastructure.db import insert_source, insert_chunks, get_vault_connection
    insert_source(tmp_db, _make_source())
    insert_chunks(tmp_db, "src-uid-1", _make_chunks())
    conn = get_vault_connection(tmp_db)
    rows = conn.execute("SELECT * FROM chunks WHERE source_uid = 'src-uid-1'").fetchall()
    conn.close()
    assert len(rows) == 3
    assert rows[0]["position"] == 0


def test_delete_chunks_for_source(tmp_db):
    from infrastructure.db import insert_source, insert_chunks, delete_chunks_for_source, get_vault_connection
    insert_source(tmp_db, _make_source())
    insert_chunks(tmp_db, "src-uid-1", _make_chunks())
    delete_chunks_for_source(tmp_db, "src-uid-1")
    conn = get_vault_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM chunks WHERE source_uid = 'src-uid-1'").fetchone()[0]
    conn.close()
    assert count == 0


def test_insert_chunk_embeddings(tmp_db):
    from infrastructure.db import insert_source, insert_chunks, insert_chunk_embeddings, get_vault_connection
    insert_source(tmp_db, _make_source())
    insert_chunks(tmp_db, "src-uid-1", _make_chunks())
    embedding = make_embedding()
    insert_chunk_embeddings(tmp_db, "chunk-0", embedding)
    conn = get_vault_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM chunks_vec").fetchone()[0]
    conn.close()
    assert count == 1


# ---- Note vectors + search ----

def test_insert_and_delete_note_embedding(tmp_db):
    from infrastructure.db import insert_note, insert_note_embedding, delete_note_embedding, get_vault_connection
    insert_note(tmp_db, _make_note())
    insert_note_embedding(tmp_db, "note-uid-1", make_embedding())
    conn = get_vault_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM notes_vec").fetchone()[0]
    assert count == 1
    conn.close()
    delete_note_embedding(tmp_db, "note-uid-1")
    conn = get_vault_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM notes_vec").fetchone()[0]
    conn.close()
    assert count == 0


def test_search_chunks_returns_results(tmp_db):
    from infrastructure.db import (
        insert_source, insert_chunks, insert_chunk_embeddings, search_chunks
    )
    source = _make_source()
    insert_source(tmp_db, source)
    chunks = _make_chunks()
    insert_chunks(tmp_db, "src-uid-1", chunks)
    for chunk in chunks:
        insert_chunk_embeddings(tmp_db, chunk.uid, make_embedding())

    query = make_embedding()
    results = search_chunks(tmp_db, query, filters=None, limit=5)
    assert len(results) == 3
    assert all(r.distance >= 0 for r in results)
    assert results[0].content.startswith("content")


def test_search_notes_returns_results(tmp_db):
    from infrastructure.db import insert_note, insert_note_embedding, search_notes
    insert_note(tmp_db, _make_note())
    insert_note_embedding(tmp_db, "note-uid-1", make_embedding())
    results = search_notes(tmp_db, make_embedding(), filters=None, limit=5)
    assert len(results) == 1
    assert results[0].title == "Test Note"
    assert results[0].note_uid == "note-uid-1"


# ---- Tags ----

def test_upsert_tags_creates_new(tmp_db):
    from infrastructure.db import upsert_tags, get_vault_connection
    tag_uids = upsert_tags(tmp_db, ["bitcoin", "decentralisation"], "fr")
    assert len(tag_uids) == 2
    conn = get_vault_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    conn.close()
    assert count == 2


def test_upsert_tags_idempotent(tmp_db):
    from infrastructure.db import upsert_tags, get_vault_connection
    upsert_tags(tmp_db, ["bitcoin"], "fr")
    upsert_tags(tmp_db, ["bitcoin", "ethereum"], "fr")
    conn = get_vault_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    conn.close()
    assert count == 2  # no duplicate


def test_set_note_tags_full_replace(tmp_db):
    from infrastructure.db import insert_note, set_note_tags, get_vault_connection
    insert_note(tmp_db, _make_note())
    set_note_tags(tmp_db, "note-uid-1", ["bitcoin", "crypto"])
    conn = get_vault_connection(tmp_db)
    count1 = conn.execute(
        "SELECT COUNT(*) FROM note_tags WHERE note_uid = 'note-uid-1'"
    ).fetchone()[0]
    conn.close()
    assert count1 == 2

    # Full replace: second call removes old tags
    set_note_tags(tmp_db, "note-uid-1", ["monnaie"])
    conn = get_vault_connection(tmp_db)
    count2 = conn.execute(
        "SELECT COUNT(*) FROM note_tags WHERE note_uid = 'note-uid-1'"
    ).fetchone()[0]
    conn.close()
    assert count2 == 1


# ---- Tool logs ----

def test_insert_tool_log(tmp_db):
    from infrastructure.db import insert_tool_log, get_vault_connection
    insert_tool_log(tmp_db, "transcribe", '{"file": "test.mp3"}', '{"text": "hello"}', 250, "success")
    conn = get_vault_connection(tmp_db)
    row = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'transcribe'").fetchone()
    conn.close()
    assert row["status"] == "success"
    assert row["duration_ms"] == 250


def test_insert_tool_log_failed(tmp_db):
    from infrastructure.db import insert_tool_log, get_vault_connection
    insert_tool_log(tmp_db, "embed", None, None, 100, "failed", "Connection refused")
    conn = get_vault_connection(tmp_db)
    row = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'embed'").fetchone()
    conn.close()
    assert row["status"] == "failed"
    assert "Connection refused" in row["error"]


def test_update_source_transcript(tmp_db):
    from infrastructure.db import insert_source, update_source_transcript, get_source
    from core.schemas import Source
    source = Source(
        uid="src-1", slug="src-one", source_type="youtube",
        status="raw", date_added="2026-03-26",
    )
    insert_source(tmp_db, source)
    update_source_transcript(tmp_db, "src-1", "full transcript text here")
    updated = get_source(tmp_db, "src-1")
    assert updated.transcript == "full transcript text here"


def test_init_system_db_creates_jobs_table(tmp_path):
    from infrastructure.db import get_system_connection, init_system_db
    db = tmp_path / ".system.db"
    init_system_db(db)
    conn = get_system_connection(db)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "jobs" in tables
    assert "tool_logs" in tables


def test_insert_and_get_job(tmp_path):
    from infrastructure.db import init_system_db, insert_job, get_job
    db = tmp_path / ".system.db"
    init_system_db(db)
    insert_job(db, job_id="abc123", job_type="youtube", input_data={"url": "https://youtu.be/x"})
    job = get_job(db, "abc123")
    assert job is not None
    assert job["id"] == "abc123"
    assert job["status"] == "pending"
    assert job["job_type"] == "youtube"


def test_update_job_status_to_running(tmp_path):
    from infrastructure.db import init_system_db, insert_job, update_job_status, get_job
    db = tmp_path / ".system.db"
    init_system_db(db)
    insert_job(db, job_id="j1", job_type="audio", input_data={"filename": "a.mp3"})
    update_job_status(db, "j1", "running")
    assert get_job(db, "j1")["status"] == "running"


def test_update_job_done_with_result(tmp_path):
    from infrastructure.db import init_system_db, insert_job, update_job_done, get_job
    db = tmp_path / ".system.db"
    init_system_db(db)
    insert_job(db, job_id="j2", job_type="pdf", input_data={"filename": "b.pdf"})
    update_job_done(db, "j2", result={"note_uid": "uid-abc", "slug": "my-note"})
    job = get_job(db, "j2")
    assert job["status"] == "done"
    assert "note_uid" in job["result"]


def test_update_job_failed(tmp_path):
    from infrastructure.db import init_system_db, insert_job, update_job_failed, get_job
    db = tmp_path / ".system.db"
    init_system_db(db)
    insert_job(db, job_id="j3", job_type="youtube", input_data={"url": "https://youtu.be/x"})
    update_job_failed(db, "j3", error="Transcription failed")
    job = get_job(db, "j3")
    assert job["status"] == "failed"
    assert job["error"] == "Transcription failed"


def test_list_jobs_filtered_by_status(tmp_path):
    from infrastructure.db import init_system_db, insert_job, update_job_status, list_jobs
    db = tmp_path / ".system.db"
    init_system_db(db)
    insert_job(db, "j1", "youtube", {"url": "u1"})
    insert_job(db, "j2", "audio", {"filename": "f.mp3"})
    update_job_status(db, "j2", "running")
    pending = list_jobs(db, status="pending", limit=20)
    assert len(pending) == 1
    assert pending[0]["id"] == "j1"


def test_mark_orphan_jobs_failed(tmp_path):
    from infrastructure.db import init_system_db, insert_job, update_job_status, mark_orphan_jobs_failed, get_job
    db = tmp_path / ".system.db"
    init_system_db(db)
    insert_job(db, "j1", "youtube", {"url": "u"})
    insert_job(db, "j2", "audio", {"filename": "f.mp3"})
    update_job_status(db, "j2", "running")
    mark_orphan_jobs_failed(db)
    assert get_job(db, "j1")["status"] == "failed"
    assert get_job(db, "j2")["status"] == "failed"


def test_list_notes_no_filter(tmp_path):
    from infrastructure.db import init_db, insert_note, list_notes
    from core.schemas import Note
    db = tmp_path / "vault.db"
    init_db(db)
    note = Note(
        uid="n1", source_uid=None, slug="test-note", note_type="synthese",
        source_type="youtube", generation_template=None, rating=None,
        sync_status="synced", title="Test Note", docstring="A test.",
        body="Body content.", url=None, date_created="2026-01-01",
        date_modified="2026-01-01", tags=["test"],
    )
    insert_note(db, note)
    results = list_notes(db, note_type=None, tags=None, limit=20, offset=0)
    assert len(results) == 1
    assert results[0].uid == "n1"


def test_list_notes_filter_by_note_type(tmp_path):
    from infrastructure.db import init_db, insert_note, list_notes
    from core.schemas import Note
    db = tmp_path / "vault.db"
    init_db(db)
    for i, ntype in enumerate(["synthese", "reflexion", "synthese"]):
        note = Note(
            uid=f"n{i}", source_uid=None, slug=f"note-{i}", note_type=ntype,
            source_type="youtube", generation_template=None, rating=None,
            sync_status="synced", title=f"Note {i}", docstring="description.",
            body="Body content here.", url=None, date_created="2026-01-01",
            date_modified="2026-01-01", tags=["t"],
        )
        insert_note(db, note)
    results = list_notes(db, note_type="synthese", tags=None, limit=20, offset=0)
    assert len(results) == 2


def test_list_sources_no_filter(tmp_path):
    from infrastructure.db import init_db, insert_source, list_sources
    from core.schemas import Source
    db = tmp_path / "vault.db"
    init_db(db)
    s = Source(uid="s1", slug="src-1", source_type="youtube", status="vaulted",
               url="https://youtu.be/x", date_added="2026-01-01")
    insert_source(db, s)
    results = list_sources(db, status=None, limit=20, offset=0)
    assert len(results) == 1
    assert results[0].uid == "s1"


def test_list_sources_filter_by_status(tmp_path):
    from infrastructure.db import init_db, insert_source, list_sources
    from core.schemas import Source
    db = tmp_path / "vault.db"
    init_db(db)
    for i, st in enumerate(["vaulted", "rag_ready", "vaulted"]):
        s = Source(uid=f"s{i}", slug=f"src-{i}", source_type="youtube",
                   status=st, date_added="2026-01-01")
        insert_source(db, s)
    results = list_sources(db, status="vaulted", limit=20, offset=0)
    assert len(results) == 2
