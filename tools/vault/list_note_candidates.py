"""
List note candidates from the candidate queue.

Input  : VaultContext, optional source_uid, optional status
Output : list[NoteCandidate]
"""
from __future__ import annotations

from core.context import VaultContext
from core.schemas import NoteCandidate
from core.logging import loggable


@loggable("list_note_candidates")
def list_note_candidates(
    ctx: VaultContext,
    source_uid: str | None = None,
    status: str | None = None,
) -> list[NoteCandidate]:
    """Retrieve note candidates optionally filtered by source_uid and status."""
    return ctx.db.list_note_candidates(source_uid=source_uid, status=status)
