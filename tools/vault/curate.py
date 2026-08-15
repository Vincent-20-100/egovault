"""
Librarian tool — Curate prefrontal working memory context.

Orchestrates the two-tier search (compiled notes → raw chunks) into a single
high-density CuratedContext with confidence weighting based on note review status.
"""
from __future__ import annotations

from core.context import VaultContext
from core.schemas import SearchFilters, CuratedSource, CuratedContext
from core.logging import loggable


@loggable("curate")
def curate(
    query: str,
    ctx: VaultContext,
    conversation_summary: str | None = None,  # accepted, inert in tier 0
    filters: SearchFilters | None = None,
    limit: int = 5,
) -> CuratedContext:
    """Curate working memory context: search notes, escalate to chunks if sparse, assemble."""
    cfg = ctx.settings.system.curate
    query_embedding = ctx.embed(query)

    # Opt-in hybrid retrieval (cosine + BM25 fused via RRF). When off, pure cosine.
    if cfg.use_hybrid_retrieval:
        notes = ctx.db.search_notes_hybrid(query, query_embedding, filters, limit)
    else:
        notes = ctx.db.search_notes(query_embedding, filters, limit)
    relevant = [n for n in notes if n.distance < cfg.escalation_max_distance]

    chunks = []
    if len(relevant) < cfg.escalation_min_notes:
        if cfg.use_hybrid_retrieval:
            chunks = ctx.db.search_chunks_hybrid(query, query_embedding, filters, limit)
        else:
            chunks = ctx.db.search_chunks(query_embedding, filters, limit)

    note_sources = [
        CuratedSource(tier="note", uid=n.note_uid, source_uid=n.source_uid,
                      title=n.title, content=n.content, distance=n.distance)
        for n in sorted(notes, key=lambda r: r.distance)
    ]
    chunk_sources = [
        CuratedSource(tier="chunk", uid=c.chunk_uid, source_uid=c.source_uid,
                      title=c.title, content=c.content, distance=c.distance)
        for c in sorted(chunks, key=lambda r: r.distance)
    ]
    sources = (note_sources + chunk_sources)[:limit]

    cap = cfg.synthesis_max_chars_per_item
    synthesis = "\n\n".join(
        f"[{s.tier}:{s.uid}] {s.title}\n{s.content[:cap]}" for s in sources
    )

    # Calculate confidence score weighted by note review_status
    confidence: float | None = None
    if sources:
        conf_cfg = getattr(cfg, "confidence", None)
        rev_weight = conf_cfg.reviewed_note_weight if conf_cfg else 1.0
        unrev_weight = conf_cfg.unreviewed_note_weight if conf_cfg else 0.7
        chunk_weight = 0.5

        weighted_sim_sum = 0.0
        weight_sum = 0.0

        for s in sources:
            sim = max(0.0, 1.0 - s.distance)
            if s.tier == "note":
                try:
                    note = ctx.db.get_note(s.uid)
                except Exception:
                    note = None
                w = rev_weight if (note and getattr(note, "review_status", None) == "reviewed") else unrev_weight
            else:
                w = chunk_weight

            weighted_sim_sum += w * sim
            weight_sum += w

        if weight_sum > 0:
            confidence = round(weighted_sim_sum / weight_sum, 3)

    return CuratedContext(
        synthesis=synthesis,
        sources=sources,
        confidence=confidence,
        query=query,
    )
