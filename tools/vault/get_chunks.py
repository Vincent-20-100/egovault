"""
Retrieve raw chunks by their UIDs for verbatim proof drill-down.

Input  : chunk_uids (list[str]), VaultContext
Output : list[ChunkResult]
"""
from __future__ import annotations

from core.context import VaultContext
from core.schemas import ChunkResult
from core.logging import loggable


@loggable("get_chunks")
def get_chunks(
    chunk_uids: list[str],
    ctx: VaultContext,
) -> list[ChunkResult]:
    """Retrieve verbatim chunk records for inspection or note proof verification."""
    return ctx.db.get_chunks(chunk_uids)
