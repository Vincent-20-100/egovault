"""
Generate a Note from a NoteCandidate via the configured LLM.

Input  : candidate_uid, VaultContext, session_id, template
Output : NoteResult
"""
from __future__ import annotations

from core.context import VaultContext
from core.schemas import NoteResult, NoteContentInput
from core.logging import loggable
from tools.vault.create_note_from_candidate import create_note_from_candidate


@loggable("generate_note_from_candidate")
def generate_note_from_candidate(
    candidate_uid: str,
    ctx: VaultContext,
    session_id: str = "agent_session",
    template: str = "standard",
) -> NoteResult:
    """Generate and atomically save a Note from a NoteCandidate via LLM synthesis."""
    if ctx.generate is None:
        raise ValueError("No LLM provider configured. Cannot generate note content.")

    # 1. Claim candidate lock
    ttl = ctx.settings.system.note_segmentation.agent_claim_ttl_seconds
    cand = ctx.db.claim_note_candidate(candidate_uid, session_id=session_id, ttl_seconds=ttl)

    # 2. Fetch all chunk contents for the candidate
    chunks = ctx.db.get_chunks(cand.chunk_uids)
    joined_text = "\n\n".join(c.content for c in chunks)

    # 3. Fetch source metadata
    source = ctx.db.get_source(cand.source_uid)
    metadata = {
        "title": cand.label,
        "source_title": source.title if source else None,
        "url": source.url if source else None,
        "author": source.author if source else None,
        "date_source": source.date_source if source else None,
        "source_type": source.source_type if source else "texte",
        "locator": cand.locator,
    }

    # 4. Synthesize note content via LLM
    content_input: NoteContentInput = ctx.generate(joined_text, metadata, template)

    # 5. Atomically convert candidate to Note
    return create_note_from_candidate(
        candidate_uid=candidate_uid,
        content=content_input,
        ctx=ctx,
        session_id=session_id,
        note_type="synthese",
    )
