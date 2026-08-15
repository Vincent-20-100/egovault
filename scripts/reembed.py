#!/usr/bin/env python3
"""
Rebuild the vector tables from stored text.

Required after changing the embedding model or the distance metric: existing
`chunks_vec`/`notes_vec` are dropped and repopulated by re-embedding
`chunks.content` and notes (`title + docstring + body`). Source text is never re-fetched.

Usage:
    python scripts/reembed.py
"""
from __future__ import annotations

import sys

from core.config import load_settings
from infrastructure.context import build_context
from infrastructure.db import get_vault_connection, init_db


def reembed() -> tuple[int, int]:
    """Drop and rebuild both vec tables. Returns (chunks, notes) re-embedded."""
    settings = load_settings()
    ctx = build_context(settings)
    db_path = settings.vault_db_path

    conn = get_vault_connection(db_path)
    conn.execute("DROP TABLE IF EXISTS chunks_vec")
    conn.execute("DROP TABLE IF EXISTS notes_vec")
    conn.commit()
    conn.close()

    # init_db recreates the vec tables with distance_metric=cosine.
    init_db(
        db_path,
        dims=settings.system.embedding.dims,
        provider=settings.system.embedding.provider,
        model=settings.system.embedding.model,
    )

    conn = get_vault_connection(db_path)
    chunk_rows = conn.execute("SELECT uid, content FROM chunks").fetchall()
    note_rows = conn.execute(
        "SELECT uid, title, docstring, body FROM notes WHERE status != 'deleted'"
    ).fetchall()
    conn.close()

    for uid, content in chunk_rows:
        if content:
            ctx.db.insert_chunk_embeddings(uid, ctx.embed(content))

    for uid, title, docstring, body in note_rows:
        # Match embed_note.py canonical text concatenation
        text = "\n\n".join(filter(None, [title, docstring, body]))
        if text.strip():
            ctx.db.insert_note_embedding(uid, ctx.embed(text))

    return len(chunk_rows), len(note_rows)


if __name__ == "__main__":
    n_chunks, n_notes = reembed()
    print(f"Re-embedded {n_chunks} chunks and {n_notes} notes (cosine).")
    sys.exit(0)
