"""
Claim a note candidate for human or agent processing.

Input  : candidate_uid, VaultContext, session_id, optional is_human
Output : NoteCandidate
"""
from __future__ import annotations

from core.context import VaultContext
from core.schemas import NoteCandidate
from core.logging import loggable


@loggable("claim_note_candidate")
def claim_note_candidate(
    candidate_uid: str,
    ctx: VaultContext,
    session_id: str,
    is_human: bool = False,
) -> NoteCandidate:
    """
    Claim candidate lock with differentiated TTL (300s for agents, 3600s for humans).
    """
    seg_cfg = ctx.settings.system.note_segmentation
    ttl = seg_cfg.human_claim_ttl_seconds if is_human else seg_cfg.agent_claim_ttl_seconds
    return ctx.db.claim_note_candidate(candidate_uid, session_id=session_id, ttl_seconds=ttl)
