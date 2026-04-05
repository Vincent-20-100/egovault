"""
Text embedding tool.

Input  : text string + VaultContext
Output : list[float] (embedding vector)
No DB write. Provider is accessed via ctx.embed.
"""

from core.context import VaultContext
from core.logging import loggable


@loggable("embed_text")
def embed_text(text: str, ctx: VaultContext) -> list[float]:
    """
    Embed a text string using the configured provider.
    Returns a flat list of floats. No DB write.
    """
    return ctx.embed(text)
