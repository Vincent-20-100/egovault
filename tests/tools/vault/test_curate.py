from unittest.mock import MagicMock

from core.schemas import SearchResult
from tools.vault.curate import curate


def _ctx_with(notes, chunks):
    ctx = MagicMock()
    ctx.embed.return_value = [0.0] * 8
    ctx.db.search_notes.return_value = notes
    ctx.db.search_chunks.return_value = chunks
    ctx.settings.system.curate.escalation_min_notes = 3
    ctx.settings.system.curate.escalation_max_distance = 0.5
    ctx.settings.system.curate.synthesis_max_chars_per_item = 800
    ctx.settings.system.curate.use_hybrid_retrieval = False
    return ctx


def test_notes_sufficient_no_chunk_escalation():
    notes = [
        SearchResult(note_uid=f"n{i}", source_uid="s1", content=f"body {i}",
                     title=f"Note {i}", distance=0.1)
        for i in range(3)
    ]
    ctx = _ctx_with(notes, [])
    result = curate("q", ctx)
    ctx.db.search_chunks.assert_not_called()
    assert result.confidence is None
    assert result.query == "q"
    assert len(result.sources) == 3
    assert all(s.tier == "note" for s in result.sources)
    assert "[note:n0] Note 0" in result.synthesis


def test_escalation_merges_notes_first_then_chunks():
    notes = [SearchResult(note_uid="n1", source_uid="s1", content="nbody",
                          title="N1", distance=0.2)]
    chunks = [SearchResult(chunk_uid="c1", source_uid="s2", content="cbody",
                           title="C1", distance=0.05)]
    ctx = _ctx_with(notes, chunks)
    result = curate("q", ctx, limit=5)
    ctx.db.search_chunks.assert_called_once()
    assert [s.tier for s in result.sources] == ["note", "chunk"]


def test_zero_results_no_error():
    ctx = _ctx_with([], [])
    result = curate("q", ctx)
    assert result.synthesis == ""
    assert result.sources == []
    assert result.confidence is None


def test_truncation_to_limit():
    notes = [SearchResult(note_uid=f"n{i}", source_uid="s", content="b",
                          title=f"N{i}", distance=0.9) for i in range(10)]
    ctx = _ctx_with(notes, [SearchResult(chunk_uid="c", source_uid="s",
                    content="b", title="C", distance=0.01)])
    result = curate("q", ctx, limit=3)
    assert len(result.sources) == 3


def test_conversation_summary_is_inert():
    notes = [SearchResult(note_uid="n1", source_uid="s", content="b",
                          title="N", distance=0.1) for _ in range(3)]
    a = curate("q", _ctx_with(notes, []))
    b = curate("q", _ctx_with(notes, []), conversation_summary="lots of context")
    assert a.model_dump() == b.model_dump()


def test_per_item_content_truncation():
    notes = [SearchResult(note_uid="n1", source_uid="s",
                          content="x" * 5000, title="N", distance=0.1)
             for _ in range(3)]
    ctx = _ctx_with(notes, [])
    ctx.settings.system.curate.synthesis_max_chars_per_item = 100
    result = curate("q", ctx)
    assert "x" * 100 in result.synthesis
    assert "x" * 101 not in result.synthesis


def test_hybrid_flag_routes_to_hybrid_methods():
    """use_hybrid_retrieval=True must call db.search_*_hybrid with query+embedding,
    and never the pure-cosine variants."""
    notes = [SearchResult(note_uid="nA", source_uid="s", content="b",
                          title="N", distance=0.1)]
    chunks = [SearchResult(chunk_uid="cA", source_uid="s", content="b",
                           title="C", distance=0.2)]
    ctx = _ctx_with(notes, chunks)
    ctx.settings.system.curate.use_hybrid_retrieval = True
    ctx.db.search_notes_hybrid.return_value = notes
    ctx.db.search_chunks_hybrid.return_value = []

    result = curate("fragilite des systemes", ctx)

    ctx.db.search_notes.assert_not_called()
    ctx.db.search_chunks.assert_not_called()
    ctx.db.search_notes_hybrid.assert_called_once()
    args, kwargs = ctx.db.search_notes_hybrid.call_args
    # signature: (query_text, query_embedding, filters, limit) — positional or kw
    flat = list(args) + list(kwargs.values())
    assert "fragilite des systemes" in flat
    assert result.sources[0].uid == "nA"
