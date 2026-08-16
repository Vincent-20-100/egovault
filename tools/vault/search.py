"""
Semantic search tool.

Input  : query string + optional filters
Output : list[SearchResult]
mode='chunks': chunk-level RAG
mode='notes' : note-level semantic search
"""

from core.context import VaultContext
from core.schemas import SearchResult, SearchFilters
from core.logging import loggable


@loggable("search")
def search(
    query: str,
    ctx: VaultContext,
    filters: SearchFilters | None = None,
    mode: str = "chunks",
    limit: int = 5,
) -> list[SearchResult]:
    """
    Semantic search over the vault.
    mode='chunks': chunk-level RAG
    mode='notes' : note-level semantic search
    mode='all'   : dual-space search across both notes and chunks
    """
    if mode not in ("chunks", "notes", "all"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'chunks', 'notes', or 'all'.")

    # Embed the query directly via ctx — no tool wrapper needed for search
    query_embedding = ctx.embed(query)

    if mode == "notes":
        return ctx.db.search_notes(query_embedding, filters, limit)
    elif mode == "chunks":
        return ctx.db.search_chunks(query_embedding, filters, limit)
    else:
        notes_res = ctx.db.search_notes(query_embedding, filters, limit)
        chunks_res = ctx.db.search_chunks(query_embedding, filters, limit)
        combined = sorted(notes_res + chunks_res, key=lambda r: r.distance)
        return combined[:limit]

