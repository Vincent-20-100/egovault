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

from core.context import VaultContext
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from tools.media.compress import compress_audio
from tools.media.transcribe import transcribe
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)


def _llm_is_configured(ctx: VaultContext) -> bool:
    """Return True only if a supported LLM is configured with credentials."""
    # ctx.generate is None when no LLM provider was wired at startup
    return ctx.generate is not None


def ingest_audio(
    file_path: str,
    ctx: VaultContext,
    title: str | None = None,
    source_type: str = "audio",
    auto_generate_note: bool | None = None,
) -> Source:
    """
    Run the full audio/video ingestion pipeline.
    Compresses media first, then transcribes using the configured engine.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if transcript exceeds token threshold.
    """
    today = date.today().isoformat()
    source_uid = generate_uid()
    file_stem = Path(file_path).stem

    existing_slugs = ctx.db.get_existing_slugs("sources")
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
    ctx.db.insert_source(source)

    # Step 1: Compress
    ctx.db.update_source_status(source_uid, "transcribing")
    compressed = compress_audio(file_path)

    # Step 2: Transcribe
    transcript_result = transcribe(compressed.output_path)
    ctx.db.update_source_transcript(source_uid, transcript_result.text)
    ctx.db.update_source_status(source_uid, "text_ready")

    # Step 3: Chunk + embed
    token_count = len(transcript_result.text.split())
    threshold = ctx.settings.system.llm.large_format_threshold_tokens

    ctx.db.update_source_status(source_uid, "embedding")
    chunks = chunk_text(transcript_result.text, ctx.settings.system)
    ctx.db.insert_chunks(source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, ctx)
        ctx.db.insert_chunk_embeddings(chunk.uid, embedding)

    ctx.db.update_source_status(source_uid, "rag_ready")

    should_generate = (
        auto_generate_note if auto_generate_note is not None
        else ctx.settings.user.llm.auto_generate_note
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
        if not _llm_is_configured(ctx):
            logger.info("LLM not configured, skipping note generation")
        else:
            generate_note_from_source(source_uid, ctx)

    return ctx.db.get_source(source_uid)
