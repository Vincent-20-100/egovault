import pytest
from unittest.mock import patch
from core.schemas import SearchResult


def _fake_results():
    return [
        SearchResult(
            note_uid="n1", source_uid="s1", chunk_uid=None,
            content="Some relevant excerpt about economics.",
            title="Note Alpha", distance=0.12,
        )
    ]


def test_search_returns_results(client):
    with patch("api.routers.search._run_search", return_value=_fake_results()):
        response = client.post("/search", json={"query": "economics", "limit": 5})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["note_uid"] == "n1"
    assert results[0]["score"] == pytest.approx(0.88, abs=0.01)  # 1 - 0.12
    assert "excerpt" in results[0]


def test_search_empty_query_rejected(client):
    response = client.post("/search", json={"query": "", "limit": 5})
    assert response.status_code == 422


def test_search_limit_too_high(client):
    response = client.post("/search", json={"query": "test", "limit": 999})
    assert response.status_code == 422
