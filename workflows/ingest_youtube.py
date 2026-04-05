"""
YouTube ingestion workflow.

Pipeline:
  fetch_subtitles → chunk_text → embed_chunks → [LLM → create_note → embed_note]

The LLM + note steps are skipped if:
  - No LLM configured (LLM-free mode) → source stays rag_ready
  - Source exceeds large_format_threshold_tokens → LargeFormatError raised

Status transitions managed here:
  raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
"""

import logging
import re
from datetime import date

from core.context import VaultContext
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from tools.media.fetch_subtitles import fetch_subtitles
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL for slug generation."""
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else "unknown"


def _llm_is_configured(ctx: VaultContext) -> bool:
    """Return True only if a supported LLM is configured with credentials."""
    # ctx.generate is None when no LLM provider was wired at startup
    return ctx.generate is not None


def ingest_youtube(url: str, ctx: VaultContext, auto_generate_note: bool | None = None) -> Source:
    """
    Run the full YouTube ingestion pipeline.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if source exceeds token threshold.
    """
    today = date.today().isoformat()
    source_uid = generate_uid()
    video_id = _extract_video_id(url)

    existing_slugs = ctx.db.get_existing_slugs("sources")
    slug = make_unique_slug(f"youtube-{video_id}", existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type="youtube",
        status="raw",
        url=url,
        date_added=today,
    )
    ctx.db.insert_source(source)

    # Step 1: Fetch subtitles
    ctx.db.update_source_status(source_uid, "transcribing")
    subtitle_result = fetch_subtitles(url)
    ctx.db.update_source_transcript(source_uid, subtitle_result.text)
    ctx.db.update_source_status(source_uid, "text_ready")

    # Step 2: Check size — rough word-count estimate
    token_count = len(subtitle_result.text.split())
    threshold = ctx.settings.system.llm.large_format_threshold_tokens

    # Step 3: Chunk + embed regardless of size (source must reach rag_ready)
    ctx.db.update_source_status(source_uid, "embedding")
    chunks = chunk_text(subtitle_result.text, ctx.settings.system)
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
