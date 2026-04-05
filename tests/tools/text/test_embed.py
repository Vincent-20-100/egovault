import pytest
from unittest.mock import patch, MagicMock


def test_embed_text_returns_vector(tmp_settings):
    from tools.text.embed import embed_text

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": [0.5] * 768}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        result = embed_text("hello", tmp_settings)

    assert isinstance(result, list)
    assert len(result) == 768


def test_embed_text_delegates_to_provider(tmp_settings):
    from tools.text.embed import embed_text

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": [0.1] * 768}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        embed_text("test text", tmp_settings)

    assert mock_post.called
    assert "test text" in str(mock_post.call_args)
