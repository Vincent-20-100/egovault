"""
Text embedding tool.

Input  : text string + settings
Output : list[float] (embedding vector)
No DB write. Provider configured via user.yaml.
"""

from core.config import Settings
from core.logging import loggable


@loggable("embed_text")
def embed_text(text: str, settings: Settings) -> list[float]:
    """
    Embed a text string using the configured provider (Ollama or OpenAI).
    Returns a flat list of floats. No DB write.
    """
    from infrastructure.embedding_provider import embed
    return embed(text, settings)
