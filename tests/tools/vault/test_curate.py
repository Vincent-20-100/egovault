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
