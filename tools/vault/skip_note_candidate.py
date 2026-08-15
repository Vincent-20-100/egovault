"""
Skip a note candidate without converting it.

Input  : candidate_uid, VaultContext
Output : dict
"""
from __future__ import annotations

from core.context import VaultContext
from core.logging import loggable


@loggable("skip_note_candidate")
def skip_note_candidate(
    candidate_uid: str,
    ctx: VaultContext,
) -> dict:
    """Mark a candidate as skipped."""
    ctx.db.mark_candidate_skipped(candidate_uid)
    return {"candidate_uid": candidate_uid, "status": "skipped"}
