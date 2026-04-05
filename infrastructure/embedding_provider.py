"""
Embedding provider for EgoVault v2.

Dispatches to Ollama (v1) or OpenAI (future, raises NotImplementedError).
See spec section 4.2 warning before adding new providers:
changing the embedding model requires full re-embedding of all chunks + notes.
"""

import requests
from core.config import Settings


def embed(text: str, settings: Settings) -> list[float]:
    """
    Embed text using the configured provider.
    Returns a list of floats (dimension depends on model).
    Raises NotImplementedError for providers not yet implemented in v1.
    """
    provider = settings.user.embedding.provider
    model = settings.user.embedding.model

    if provider == "ollama":
        return _embed_ollama(text, model, settings.install.providers.ollama_base_url)
    elif provider == "openai":
        raise NotImplementedError(
            "OpenAI embedding is not implemented in v1. "
            "See spec section 4.2 for prerequisites before adding new providers."
        )
    else:
        raise ValueError(f"Unknown embedding provider: '{provider}'. Supported: ollama")


def _embed_ollama(text: str, model: str, base_url: str) -> list[float]:
    url = f"{base_url}/api/embeddings"
    try:
        response = requests.post(url, json={"model": model, "prompt": text}, timeout=60)
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        from core.sanitize import sanitize_error
        raise RuntimeError(sanitize_error(e)) from None
