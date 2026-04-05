"""
Text chunking tool.

Input  : raw text + config
Output : list[ChunkResult]
No DB write. Chunk size and overlap from system.yaml.
"""

from core.schemas import ChunkResult
from core.config import SystemConfig
from core.logging import loggable
from core.uid import generate_uid


@loggable("chunk_text")
def chunk_text(text: str, config: SystemConfig) -> list[ChunkResult]:
    """Split text into overlapping chunks with token counts."""
    words = text.split()
    if not words:
        return []

    size = config.chunking.size
    overlap = config.chunking.overlap
    step = max(1, size - overlap)

    chunks = []
    position = 0
    i = 0
    while i < len(words):
        chunk_words = words[i:i + size]
        chunks.append(ChunkResult(
            uid=generate_uid(),
            position=position,
            content=" ".join(chunk_words),
            token_count=len(chunk_words),
        ))
        position += 1
        i += step
    return chunks
