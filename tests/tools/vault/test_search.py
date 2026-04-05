import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_embedding

from core.schemas import SearchResult


def _mock_embedding():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": make_embedding()}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_search_chunks_returns_results(ctx):
    from tools.vault.search import search
    from core.schemas import Source, ChunkResult
    from datetime import date

    source = Source(uid="s1", slug="s1", source_type="youtube", status="rag_ready",
                    date_added=date.today().isoformat())
    ctx.db.insert_source(source)
    chunk = ChunkResult(uid="c1", position=0, content="hello world content", token_count=3)
    ctx.db.insert_chunks("s1", [chunk])
    ctx.db.insert_chunk_embeddings("c1", make_embedding())

    with patch("requests.post", return_value=_mock_embedding()):
        results = search("hello world", ctx, mode="chunks", limit=5)

    assert len(results) == 1
    assert results[0].content == "hello world content"


def test_search_notes_returns_results(ctx):
    from tools.vault.search import search
    from core.schemas import Note
    from datetime import date

    note = Note(
        uid="n1", slug="test-note", title="Test Note", tags=["tag1"],
        body="Test body content here.", docstring="Short description.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )
    ctx.db.insert_note(note)
    ctx.db.insert_note_embedding("n1", make_embedding())

    with patch("requests.post", return_value=_mock_embedding()):
        results = search("test content", ctx, mode="notes", limit=5)

    assert len(results) == 1
    assert results[0].note_uid == "n1"


def test_search_invalid_mode_raises(ctx):
    from tools.vault.search import search

    with patch("requests.post", return_value=_mock_embedding()):
        with pytest.raises(ValueError, match="mode"):
            search("test", ctx, mode="invalid")
