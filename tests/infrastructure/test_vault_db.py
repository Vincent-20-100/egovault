"""
Tests for infrastructure/vault_db.py — VaultDB facade.

Verifies that each VaultDB method correctly delegates to the underlying
db.py functions using a real temp SQLite DB.
"""

import pytest
from datetime import date
from pathlib import Path

from core.schemas import Note, Source, SearchFilters
from tests.conftest import make_embedding, EMBEDDING_DIMS


# ============================================================
# HELPERS
# ============================================================

def _make_source(uid: str = "src-1", slug: str = "test-source", **overrides) -> Source:
    data = {
        "uid": uid,
        "slug": slug,
        "source_type": "youtube",
        "status": "raw",
        "date_added": date.today().isoformat(),
    }
    data.update(overrides)
    return Source(**data)


def _make_note(uid: str = "note-1", slug: str = "test-note", **overrides) -> Note:
    data = {
        "uid": uid,
        "slug": slug,
        "source_uid": None,
        "note_type": "synthese",
        "source_type": "youtube",
        "generation_template": "standard",
        "rating": None,
        "sync_status": "synced",
        "status": "active",
        "title": "Test Note",
        "docstring": "What, why, thesis.",
        "body": "Body content for testing.",
        "url": None,
        "date_created": date.today().isoformat(),
        "date_modified": date.today().isoformat(),
        "tags": ["test-tag"],
    }
    data.update(overrides)
    return Note(**data)


def _init_db_with_migrations(db_path: Path) -> None:
    """Initialize DB and apply all migrations (mirrors production setup)."""
    from infrastructure.db import init_db
    from scripts.temp._002_add_previous_status import run as apply_002
    init_db(db_path)
    apply_002(db_path)


@pytest.fixture
def vault_db(tmp_path):
    """Initialized VaultDB pointing at a temp SQLite DB (with migrations)."""
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    return VaultDB(db_path)


@pytest.fixture
def vault_db_path(tmp_path):
    """Return both a VaultDB and the underlying path."""
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    return VaultDB(db_path), db_path


# ============================================================
# CONSTRUCTION
# ============================================================

def test_vault_db_instantiates(tmp_path):
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    vdb = VaultDB(db_path)
    assert vdb is not None


# ============================================================
# SOURCES
# ============================================================

def test_get_source_returns_none_when_missing(vault_db):
    assert vault_db.get_source("nonexistent") is None


def test_get_source_returns_source_after_insert(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    src = _make_source()
    insert_source(db_path, src)
    vdb = VaultDB(db_path)
    result = vdb.get_source("src-1")
    assert result is not None
    assert result.uid == "src-1"
    assert result.slug == "test-source"


def test_update_source_status(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    vdb = VaultDB(db_path)
    vdb.update_source_status("src-1", "rag_ready")
    result = vdb.get_source("src-1")
    assert result.status == "rag_ready"


def test_soft_delete_source(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    vdb = VaultDB(db_path)
    vdb.soft_delete_source("src-1")
    result = vdb.get_source("src-1")
    assert result.status == "pending_deletion"


def test_restore_source_returns_previous_status(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source(status="rag_ready"))
    vdb = VaultDB(db_path)
    vdb.soft_delete_source("src-1")
    restored_status = vdb.restore_source("src-1")
    assert restored_status == "rag_ready"


def test_hard_delete_source(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    vdb = VaultDB(db_path)
    vdb.hard_delete_source("src-1")
    assert vdb.get_source("src-1") is None


def test_list_sources_pending_deletion(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    vdb = VaultDB(db_path)
    vdb.soft_delete_source("src-1")
    pending = vdb.list_sources_pending_deletion()
    assert len(pending) == 1
    assert pending[0].uid == "src-1"


# ============================================================
# NOTES
# ============================================================

def test_get_note_returns_none_when_missing(vault_db):
    assert vault_db.get_note("nonexistent") is None


def test_insert_and_get_note(vault_db):
    note = _make_note()
    vault_db.insert_note(note)
    result = vault_db.get_note("note-1")
    assert result is not None
    assert result.uid == "note-1"
    assert result.title == "Test Note"


def test_get_note_by_source(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    vdb = VaultDB(db_path)
    note = _make_note(source_uid="src-1")
    vdb.insert_note(note)
    result = vdb.get_note_by_source("src-1")
    assert result is not None
    assert result.uid == "note-1"


def test_get_note_by_source_returns_none_when_missing(vault_db):
    assert vault_db.get_note_by_source("nonexistent") is None


def test_update_note(vault_db):
    vault_db.insert_note(_make_note())
    vault_db.update_note("note-1", {"title": "Updated Title"})
    result = vault_db.get_note("note-1")
    assert result.title == "Updated Title"


def test_soft_delete_note(vault_db):
    vault_db.insert_note(_make_note())
    vault_db.soft_delete_note("note-1")
    result = vault_db.get_note("note-1")
    assert result.sync_status == "pending_deletion"


def test_restore_note_returns_previous_sync_status(vault_db):
    vault_db.insert_note(_make_note(sync_status="synced"))
    vault_db.soft_delete_note("note-1")
    restored = vault_db.restore_note("note-1")
    assert restored == "synced"


def test_hard_delete_note(vault_db):
    vault_db.insert_note(_make_note())
    vault_db.hard_delete_note("note-1")
    assert vault_db.get_note("note-1") is None


def test_list_notes_pending_deletion(vault_db):
    vault_db.insert_note(_make_note())
    vault_db.soft_delete_note("note-1")
    pending = vault_db.list_notes_pending_deletion()
    assert len(pending) == 1
    assert pending[0].uid == "note-1"


def test_orphan_notes_for_source(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    vdb = VaultDB(db_path)
    vdb.insert_note(_make_note(source_uid="src-1"))
    orphaned = vdb.orphan_notes_for_source("src-1")
    assert "note-1" in orphaned
    result = vdb.get_note("note-1")
    assert result.source_uid is None


# ============================================================
# CHUNKS & EMBEDDINGS
# ============================================================

def test_delete_chunks_for_source(tmp_path):
    from infrastructure.db import insert_source, insert_chunks, get_vault_connection
    from infrastructure.vault_db import VaultDB
    from core.schemas import ChunkResult
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    chunk = ChunkResult(uid="chunk-1", position=0, content="hello", token_count=1)
    insert_chunks(db_path, "src-1", [chunk])
    vdb = VaultDB(db_path)
    vdb.delete_chunks_for_source("src-1")
    conn = get_vault_connection(db_path)
    rows = conn.execute("SELECT * FROM chunks WHERE source_uid = 'src-1'").fetchall()
    conn.close()
    assert len(rows) == 0


def test_delete_chunk_embeddings_for_source(tmp_path):
    from infrastructure.db import (
        insert_source, insert_chunks, insert_chunk_embeddings,
        get_vault_connection,
    )
    from infrastructure.vault_db import VaultDB
    from core.schemas import ChunkResult
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source())
    chunk = ChunkResult(uid="chunk-1", position=0, content="hello", token_count=1)
    insert_chunks(db_path, "src-1", [chunk])
    insert_chunk_embeddings(db_path, "chunk-1", make_embedding())
    vdb = VaultDB(db_path)
    vdb.delete_chunk_embeddings_for_source("src-1")
    conn = get_vault_connection(db_path)
    rows = conn.execute("SELECT * FROM chunks_vec WHERE chunk_uid = 'chunk-1'").fetchall()
    conn.close()
    assert len(rows) == 0


def test_insert_and_delete_note_embedding(vault_db):
    vault_db.insert_note(_make_note())
    vault_db.insert_note_embedding("note-1", make_embedding())
    # No error — embedding inserted
    vault_db.delete_note_embedding("note-1")
    # No error — embedding deleted


# ============================================================
# SEARCH
# ============================================================

def test_search_chunks_returns_list(vault_db):
    results = vault_db.search_chunks(make_embedding(), None, 5)
    assert isinstance(results, list)


def test_search_notes_returns_list(vault_db):
    results = vault_db.search_notes(make_embedding(), None, 5)
    assert isinstance(results, list)


def test_search_notes_returns_inserted_note(vault_db):
    vault_db.insert_note(_make_note())
    vault_db.insert_note_embedding("note-1", make_embedding(0.1))
    results = vault_db.search_notes(make_embedding(0.1), None, 5)
    assert len(results) >= 1
    assert results[0].note_uid == "note-1"


# ============================================================
# UTILITY
# ============================================================

def test_get_existing_slugs_notes(vault_db):
    vault_db.insert_note(_make_note(slug="my-note"))
    slugs = vault_db.get_existing_slugs("notes")
    assert "my-note" in slugs


def test_get_existing_slugs_sources(tmp_path):
    from infrastructure.db import insert_source
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    insert_source(db_path, _make_source(slug="my-source"))
    vdb = VaultDB(db_path)
    slugs = vdb.get_existing_slugs("sources")
    assert "my-source" in slugs


def test_get_existing_slugs_invalid_table_raises(vault_db):
    with pytest.raises(ValueError, match="must be one of"):
        vault_db.get_existing_slugs("injected_table; DROP TABLE notes")


def test_get_graph_data_empty_when_no_notes(vault_db):
    result = vault_db.get_graph_data()
    assert result["nodes"] == []
    assert result["pivot_slug"] is None


def test_get_graph_data_by_note_uid(tmp_path):
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    vdb = VaultDB(db_path)
    vdb.insert_note(_make_note(uid="note-1", slug="note-one"))
    vdb.insert_note(_make_note(uid="note-2", slug="note-two"))
    # Both notes share "test-tag" (set by _make_note default)
    result = vdb.get_graph_data(note_uid="note-1")
    assert result["pivot_slug"] == "note-one"
    node_uids = {n["uid"] for n in result["nodes"]}
    assert "note-1" in node_uids


def test_get_graph_data_by_tag(tmp_path):
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    _init_db_with_migrations(db_path)
    vdb = VaultDB(db_path)
    vdb.insert_note(_make_note(uid="note-1", slug="note-one", tags=["science"]))
    result = vdb.get_graph_data(tag="science")
    assert len(result["nodes"]) >= 1
    assert result["pivot_slug"] is None
