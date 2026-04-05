import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_embedding, EMBEDDING_DIMS


def test_embed_ollama_returns_vector(tmp_settings):
    from infrastructure.embedding_provider import embed

    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": make_embedding()}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = embed("hello world", tmp_settings)

    assert isinstance(result, list)
    assert len(result) == EMBEDDING_DIMS
    assert result[0] == pytest.approx(0.1)

    call_kwargs = mock_post.call_args
    assert "nomic-embed-text" in str(call_kwargs)
    assert "hello world" in str(call_kwargs)


def test_embed_ollama_uses_correct_url(tmp_settings):
    from infrastructure.embedding_provider import embed

    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": make_embedding(0.0)}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        embed("test", tmp_settings)

    url = mock_post.call_args[0][0]
    assert url == "http://localhost:11434/api/embeddings"


def test_embed_openai_raises_not_implemented(tmp_settings):
    from infrastructure.embedding_provider import embed
    from core.config import EmbeddingUserConfig

    openai_settings = tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"embedding": EmbeddingUserConfig(provider="openai", model="text-embedding-3-small")}
        )}
    )
    with pytest.raises(NotImplementedError):
        embed("test", openai_settings)


def test_embed_unknown_provider_raises(tmp_settings):
    from infrastructure.embedding_provider import embed
    from core.config import EmbeddingUserConfig

    bad_settings = tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"embedding": EmbeddingUserConfig(provider="unknown", model="x")}
        )}
    )
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        embed("test", bad_settings)
