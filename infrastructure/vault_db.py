"""
VaultDB — thin facade that binds a db_path to all database operations.

Tools call ctx.db.method() instead of importing infrastructure/db directly.
Every method is a one-line delegation — no SQL, no logic, no new behavior.
"""

from pathlib import Path

from core.schemas import Note, Source, SearchResult, SearchFilters, ChunkResult

import infrastructure.db as _db


class VaultDB:
    """Facade over db.py — binds db_path so callers don't need to pass it."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    # -- Sources --

    def insert_source(self, source: Source) -> None:
        return _db.insert_source(self._db_path, source)

    def update_source_transcript(self, uid: str, transcript: str) -> None:
        return _db.update_source_transcript(self._db_path, uid, transcript)

    def get_source(self, uid: str) -> Source | None:
        return _db.get_source(self._db_path, uid)

    def update_source_status(self, uid: str, status: str) -> None:
        return _db.update_source_status(self._db_path, uid, status)

    def soft_delete_source(self, uid: str) -> None:
        return _db.soft_delete_source(self._db_path, uid)

    def hard_delete_source(self, uid: str) -> None:
        return _db.hard_delete_source(self._db_path, uid)

    def restore_source(self, uid: str) -> str:
        return _db.restore_source(self._db_path, uid)

    def list_sources_pending_deletion(self) -> list[Source]:
        return _db.list_sources_pending_deletion(self._db_path)

    # -- Notes --

    def get_note(self, uid: str) -> Note | None:
        return _db.get_note(self._db_path, uid)

    def get_note_by_source(self, source_uid: str) -> Note | None:
        return _db.get_note_by_source(self._db_path, source_uid)

    def insert_note(self, note: Note) -> None:
        return _db.insert_note(self._db_path, note)

    def update_note(self, uid: str, fields: dict) -> None:
        return _db.update_note(self._db_path, uid, fields)

    def soft_delete_note(self, uid: str) -> None:
        return _db.soft_delete_note(self._db_path, uid)

    def hard_delete_note(self, uid: str) -> None:
        return _db.hard_delete_note(self._db_path, uid)

    def restore_note(self, uid: str) -> str:
        return _db.restore_note(self._db_path, uid)

    def list_notes_pending_deletion(self) -> list[Note]:
        return _db.list_notes_pending_deletion(self._db_path)

    def set_note_tags(self, uid: str, tag_names: list[str]) -> None:
        return _db.set_note_tags(self._db_path, uid, tag_names)

    def list_notes(
        self,
        note_type: str | None,
        tags: list[str] | None,
        limit: int,
        offset: int,
    ) -> list[Note]:
        return _db.list_notes(self._db_path, note_type, tags, limit, offset)

    def list_sources(
        self,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[Source]:
        return _db.list_sources(self._db_path, status, limit, offset)

    def orphan_notes_for_source(self, source_uid: str) -> list[str]:
        return _db.orphan_notes_for_source(self._db_path, source_uid)

    # -- Chunks & embeddings --

    def insert_chunks(self, source_uid: str, chunks: list[ChunkResult]) -> None:
        return _db.insert_chunks(self._db_path, source_uid, chunks)

    def insert_chunk_embeddings(self, chunk_uid: str, embedding: list[float]) -> None:
        return _db.insert_chunk_embeddings(self._db_path, chunk_uid, embedding)

    def delete_chunks_for_source(self, source_uid: str) -> None:
        return _db.delete_chunks_for_source(self._db_path, source_uid)

    def delete_chunk_embeddings_for_source(self, uid: str) -> None:
        return _db.delete_chunk_embeddings_for_source(self._db_path, uid)

    def insert_note_embedding(self, note_uid: str, embedding: list[float]) -> None:
        return _db.insert_note_embedding(self._db_path, note_uid, embedding)

    def delete_note_embedding(self, note_uid: str) -> None:
        return _db.delete_note_embedding(self._db_path, note_uid)

    # -- Search --

    def search_chunks(
        self,
        query_embedding: list[float],
        filters: SearchFilters | None,
        limit: int,
    ) -> list[SearchResult]:
        return _db.search_chunks(self._db_path, query_embedding, filters, limit)

    def search_notes(
        self,
        query_embedding: list[float],
        filters: SearchFilters | None,
        limit: int,
    ) -> list[SearchResult]:
        return _db.search_notes(self._db_path, query_embedding, filters, limit)

    # -- Utility --

    def ping(self) -> bool:
        """Open a connection and execute a trivial query — used for health checks."""
        conn = _db.get_vault_connection(self._db_path)
        conn.execute("SELECT 1")
        conn.close()
        return True

    def get_existing_slugs(self, table: str) -> set[str]:
        """Return all slugs in the given table ('notes' or 'sources')."""
        allowed = {"notes", "sources"}
        if table not in allowed:
            raise ValueError(f"get_existing_slugs: table must be one of {allowed}, got '{table}'")
        # Safe f-string — table is from allowlist above
        conn = _db.get_vault_connection(self._db_path)
        rows = conn.execute(f"SELECT slug FROM {table}").fetchall()  # noqa: S608
        conn.close()
        return {row[0] for row in rows}

    def get_graph_data(
        self,
        note_uid: str | None = None,
        tag: str | None = None,
    ) -> dict:
        """Return nodes for Mermaid graph export, filtered by note or tag."""
        conn = _db.get_vault_connection(self._db_path)

        if note_uid is not None:
            # All notes sharing at least one tag with the pivot note
            rows = conn.execute(
                """
                SELECT DISTINCT n.uid, n.slug, n.title
                FROM notes n
                JOIN note_tags nt ON nt.note_uid = n.uid
                JOIN tags t ON t.uid = nt.tag_uid
                WHERE t.uid IN (
                    SELECT tag_uid FROM note_tags WHERE note_uid = ?
                )
                """,
                (note_uid,),
            ).fetchall()
            pivot = conn.execute(
                "SELECT slug FROM notes WHERE uid = ?", (note_uid,)
            ).fetchone()
            conn.close()
            return {
                "nodes": [dict(r) for r in rows],
                "pivot_slug": pivot["slug"] if pivot else None,
            }

        if tag is not None:
            rows = conn.execute(
                """
                SELECT DISTINCT n.uid, n.slug, n.title
                FROM notes n
                JOIN note_tags nt ON nt.note_uid = n.uid
                JOIN tags t ON t.uid = nt.tag_uid
                WHERE t.name = ?
                """,
                (tag,),
            ).fetchall()
            conn.close()
            return {"nodes": [dict(r) for r in rows], "pivot_slug": None}

        conn.close()
        return {"nodes": [], "pivot_slug": None}
