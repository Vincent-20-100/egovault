"""
Semantic search tool.

Input  : query string + optional filters
Output : list[SearchResult]
mode='chunks': chunk-level RAG
mode='notes' : note-level semantic search
"""

from core.schemas import SearchResult, SearchFilters
from core.config import Settings
from core.logging import loggable


@loggable("search")
def search(
    query: str,
    settings: Settings,
    filters: SearchFilters | None = None,
    mode: str = "chunks",
    limit: int = 5,
) -> list[SearchResult]:
    """
    Semantic search over the vault.
    mode='chunks': chunk-level RAG (Pattern A1/A2 from spec section 4.3)
    mode='notes' : note-level semantic search (Pattern B)
    """
    from tools.text.embed import embed_text
    from infrastructure.db import search_chunks, search_notes

    if mode not in ("chunks", "notes"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'chunks' or 'notes'.")

    query_embedding = embed_text(query, settings)

    if mode == "notes":
        return search_notes(settings.vault_db_path, query_embedding, filters, limit)
    else:
        return search_chunks(settings.vault_db_path, query_embedding, filters, limit)
