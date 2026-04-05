"""
Unified ingest pipeline.

Single entry point for all source types. Dispatches text extraction
to type-specific extractors, then runs the common pipeline:
  extract → chunk → embed → [generate note]
"""

import logging
import re
from datetime import date
from pathlib import Path

from core.context import VaultContext
from core.errors import EmptyContentError, LargeFormatError
from core.schemas import Source
from core.uid import generate_uid, make_unique_slug
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.vault.generate_note_from_source import generate_note_from_source

logger = logging.getLogger(__name__)


# -- Extractors: each returns (text, metadata) --


def _extract_youtube(target: str, ctx: VaultContext) -> tuple[str, dict]:
    from tools.media.fetch_subtitles import fetch_subtitles
    result = fetch_subtitles(target)
    return result.text, {"language": result.language, "source": result.source}


def _extract_audio(target: str, ctx: VaultContext) -> tuple[str, dict]:
    from tools.media.compress import compress_audio
    from tools.media.transcribe import transcribe
    compressed = compress_audio(target)
    result = transcribe(compressed.output_path)
    return result.text, {"language": result.language}


def _extract_pdf(target: str, ctx: VaultContext) -> tuple[str, dict]:
    import pypdf
    reader = pypdf.PdfReader(target)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    return text, {"page_count": len(reader.pages)}


def _extract_text(target: str, ctx: VaultContext) -> tuple[str, dict]:
    return target, {}


def _extract_html(target: str, ctx: VaultContext) -> tuple[str, dict]:
    from tools.text.parse_html import parse_html
    result = parse_html(target)
    metadata = {}
    if result.title:
        metadata["title"] = result.title
    if result.author:
        metadata["author"] = result.author
    return result.text, metadata


_EXTRACTORS: dict[str, callable] = {
    "youtube": _extract_youtube,
    "audio": _extract_audio,
    "video": _extract_audio,
    "pdf": _extract_pdf,
    "livre": _extract_pdf,
    "texte": _extract_text,
    "html": _extract_html,
}


# -- Slug generation helpers --


def _youtube_video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else "unknown"


def _make_slug(source_type: str, target: str, title: str | None, ctx: VaultContext) -> str:
    existing = ctx.db.get_existing_slugs("sources")
    if source_type == "youtube":
        base = f"youtube-{_youtube_video_id(target)}"
    elif title:
        base = title
    elif source_type in ("audio", "video", "pdf", "livre"):
        base = Path(target).stem
    else:
        base = source_type
    return make_unique_slug(base, existing)


# -- Common pipeline --


def ingest(
    source_type: str,
    target: str,
    ctx: VaultContext,
    title: str | None = None,
    auto_generate_note: bool | None = None,
) -> Source:
    """
    Unified ingest pipeline. Dispatches to the right extractor
    based on source_type, then runs chunk → embed → [generate note].
    """
    extractor = _EXTRACTORS.get(source_type)
    if extractor is None:
        raise ValueError(f"No extractor for source type '{source_type}'")

    today = date.today().isoformat()
    source_uid = generate_uid()
    slug = _make_slug(source_type, target, title, ctx)

    # URL only for youtube sources
    url = target if source_type == "youtube" else None

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type=source_type,
        status="raw",
        url=url,
        title=title,
        date_added=today,
    )
    ctx.db.insert_source(source)

    # Step 1: Extract text
    ctx.db.update_source_status(source_uid, "transcribing")
    text, metadata = extractor(target, ctx)

    if not text or not text.strip():
        raise EmptyContentError()

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

    # Step 3: Optional note generation
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
        if ctx.generate is None:
            logger.info("LLM not configured, skipping note generation")
        else:
            generate_note_from_source(source_uid, ctx)

    return ctx.db.get_source(source_uid)
