import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_embedding

from core.schemas import SearchResult


def _mock_embedding():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": make_embedding()}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_search_chunks_returns_results(tmp_settings, tmp_db, tmp_path):
    from tools.vault.search import search
    from infrastructure.db import insert_source, insert_chunks, insert_chunk_embeddings
    from core.schemas import Source, ChunkResult
    from datetime import date
    import unittest.mock as mock

    source = Source(uid="s1", slug="s1", source_type="youtube", status="rag_ready",
                    date_added=date.today().isoformat())
    insert_source(tmp_db, source)
    chunk = ChunkResult(uid="c1", position=0, content="hello world content", token_count=3)
    insert_chunks(tmp_db, "s1", [chunk])
    insert_chunk_embeddings(tmp_db, "c1", make_embedding())

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("requests.post", return_value=_mock_embedding()):
        results = search("hello world", tmp_settings, mode="chunks", limit=5)

    assert len(results) == 1
    assert results[0].content == "hello world content"


def test_search_notes_returns_results(tmp_settings, tmp_db, tmp_path):
    from tools.vault.search import search
    from infrastructure.db import insert_note, insert_note_embedding
    from core.schemas import Note
    from datetime import date
    import unittest.mock as mock

    note = Note(
        uid="n1", slug="test-note", title="Test Note", tags=["tag1"],
        body="Test body content here.", docstring="Short description.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )
    insert_note(tmp_db, note)
    insert_note_embedding(tmp_db, "n1", make_embedding())

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         patch("requests.post", return_value=_mock_embedding()):
        results = search("test content", tmp_settings, mode="notes", limit=5)

    assert len(results) == 1
    assert results[0].note_uid == "n1"


def test_search_invalid_mode_raises(tmp_settings):
    from tools.vault.search import search

    with patch("requests.post", return_value=_mock_embedding()):
        with pytest.raises(ValueError, match="mode"):
            search("test", tmp_settings, mode="invalid")
