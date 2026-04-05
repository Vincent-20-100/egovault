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

import re
from datetime import date

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
from tools.media.fetch_subtitles import fetch_subtitles
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL for slug generation."""
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else "unknown"


def ingest_youtube(url: str, settings: Settings) -> Source:
    """
    Run the full YouTube ingestion pipeline.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if source exceeds token threshold.
    """
    db = settings.vault_db_path
    today = date.today().isoformat()
    source_uid = generate_uid()
    video_id = _extract_video_id(url)

    conn = get_vault_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM sources").fetchall()}
    conn.close()

    slug = make_unique_slug(f"youtube-{video_id}", existing_slugs)

    source = Source(
        uid=source_uid,
        slug=slug,
        source_type="youtube",
        status="raw",
        url=url,
        date_added=today,
    )
    insert_source(db, source)

    # Step 1: Fetch subtitles
    update_source_status(db, source_uid, "transcribing")
    subtitle_result = fetch_subtitles(url, settings)
    update_source_transcript(db, source_uid, subtitle_result.text)
    update_source_status(db, source_uid, "text_ready")

    # Step 2: Check size — rough word-count estimate
    token_count = len(subtitle_result.text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    # Step 3: Chunk + embed regardless of size (source must reach rag_ready)
    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(subtitle_result.text, settings.system)
    insert_chunks(db, source_uid, chunks)
    for chunk in chunks:
        embedding = embed_text(chunk.content, settings)
        insert_chunk_embeddings(db, chunk.uid, embedding)

    update_source_status(db, source_uid, "rag_ready")

    if token_count > threshold:
        raise LargeFormatError(
            source_uid=source_uid,
            token_count=token_count,
            threshold=threshold,
        )

    return get_source(db, source_uid)
