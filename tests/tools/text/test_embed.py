import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_embedding, EMBEDDING_DIMS


def test_embed_text_returns_vector(tmp_settings):
    from tools.text.embed import embed_text

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": make_embedding(0.5)}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        result = embed_text("hello", tmp_settings)

    assert isinstance(result, list)
    assert len(result) == EMBEDDING_DIMS


def test_embed_text_delegates_to_provider(tmp_settings):
    from tools.text.embed import embed_text

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": make_embedding()}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        embed_text("test text", tmp_settings)

    assert mock_post.called
    assert "test text" in str(mock_post.call_args)
