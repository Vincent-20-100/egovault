"""
Audio/video file ingestion workflow.

Pipeline:
  compress → transcribe → chunk_text → embed_chunks → [LLM → create_note → embed_note]

Handles source_types: audio, video.
Status transitions: raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
"""

import logging
from datetime import date
from pathlib import Path

from core.config import Settings
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from infrastructure.db import (
    get_vault_connection,
    get_source,
    insert_chunk_embeddings,
    insert_chunks,
    insert_source,
    update_source_status,
    update_source_transcript,
)
from tools.media.compress import compress_audio
from tools.media.transcribe import transcribe
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)


def _llm_is_configured(settings) -> bool:
    """Return True only if a supported LLM is configured with credentials."""
    if settings.user.llm.provider == "claude":
        return bool(settings.install.providers.anthropic_api_key)
    return False


def ingest_audio(
    file_path: str,
    settings: Settings,
    title: str | None = None,
    source_type: str = "audio",
    auto_generate_note: bool | None = None,
) -> Source:
    """
    Run the full audio/video ingestion pipeline.
    Compresses media first (Opus), then transcribes via faster-whisper.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if transcript exceeds token threshold.
    """
    db = settings.vault_db_path
    today = date.today().isoformat()
    source_uid = generate_uid()
    file_stem = Path(file_path).stem

    conn = get_vault_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM sources").fetchall()}
    conn.close()

    base_name = title if title else file_stem
    slug = make_unique_slug(base_name, existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type=source_type,
        status="raw",
        title=title,
        date_added=today,
    )
    insert_source(db, source)

    # Step 1: Compress
    update_source_status(db, source_uid, "transcribing")
    compressed = compress_audio(file_path)

    # Step 2: Transcribe
    transcript_result = transcribe(compressed.output_path)
    update_source_transcript(db, source_uid, transcript_result.text)
    update_source_status(db, source_uid, "text_ready")

    # Step 3: Chunk + embed
    token_count = len(transcript_result.text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(transcript_result.text, settings.system)
    insert_chunks(db, source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, settings)
        insert_chunk_embeddings(db, chunk.uid, embedding)

    update_source_status(db, source_uid, "rag_ready")

    should_generate = (
        auto_generate_note if auto_generate_note is not None
        else settings.user.llm.auto_generate_note
    )

    if token_count > threshold:
        if should_generate:
            logger.info("Source exceeds token threshold, skipping note generation")
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    if should_generate:
        if not _llm_is_configured(settings):
            logger.info("LLM not configured, skipping note generation")
        else:
            generate_note_from_source(source_uid, settings)

    return get_source(db, source_uid)
