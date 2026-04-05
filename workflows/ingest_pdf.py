"""
PDF/book ingestion workflow.

Pipeline:
  extract_text → chunk_text → embed_chunks → [LLM → create_note → embed_note]

Handles source_types: pdf, livre (same pipeline, different taxonomy value).
Status transitions: raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]
"""

import logging
from datetime import date
from pathlib import Path

from core.context import VaultContext
from core.errors import LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)


def _llm_is_configured(ctx: VaultContext) -> bool:
    """Return True only if a supported LLM is configured with credentials."""
    # ctx.generate is None when no LLM provider was wired at startup
    return ctx.generate is not None


def _extract_pdf_text(file_path: str) -> str:
    """Extract full text from a PDF using the configured PDF parser."""
    import pypdf
    reader = pypdf.PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def ingest_pdf(
    file_path: str,
    ctx: VaultContext,
    title: str | None = None,
    source_type: str = "pdf",
    auto_generate_note: bool | None = None,
) -> Source:
    """
    Run the full PDF ingestion pipeline.
    source_type: 'pdf' or 'livre' — same pipeline, different metadata.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if extracted text exceeds token threshold.
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

    # Step 1: Extract text
    ctx.db.update_source_status(source_uid, "transcribing")
    text = _extract_pdf_text(file_path)
    ctx.db.update_source_transcript(source_uid, text)
    ctx.db.update_source_status(source_uid, "text_ready")

    # Step 2: Chunk + embed
    token_count = len(text.split())
    threshold = ctx.settings.system.llm.large_format_threshold_tokens

    ctx.db.update_source_status(source_uid, "embedding")
    chunks = chunk_text(text, ctx.settings.system)
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
