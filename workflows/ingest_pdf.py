"""
PDF/book ingestion workflow.

Pipeline:
  extract_text (pypdf) → chunk_text → embed_chunks → [LLM → create_note → embed_note]

Handles source_types: pdf, livre (same pipeline, different taxonomy value).
Status transitions: raw → transcribing → text_ready → embedding → rag_ready [→ pre_vaulted → vaulted]

Note: pypdf used in v1 for simplicity. Docling is a future upgrade for better layout analysis.
"""

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
from tools.text.chunk import chunk_text
from tools.text.embed import embed_text


def _extract_pdf_text(file_path: str) -> str:
    """Extract full text from a PDF using pypdf."""
    import pypdf
    reader = pypdf.PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def ingest_pdf(
    file_path: str,
    settings: Settings,
    title: str | None = None,
    source_type: str = "pdf",
) -> Source:
    """
    Run the full PDF ingestion pipeline.
    source_type: 'pdf' or 'livre' — same pipeline, different metadata.
    Returns the Source record at rag_ready status.
    Raises LargeFormatError if extracted text exceeds token threshold.
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

    # Step 1: Extract text
    update_source_status(db, source_uid, "transcribing")
    text = _extract_pdf_text(file_path)
    update_source_transcript(db, source_uid, text)
    update_source_status(db, source_uid, "text_ready")

    # Step 2: Chunk + embed
    token_count = len(text.split())
    threshold = settings.system.llm.large_format_threshold_tokens

    update_source_status(db, source_uid, "embedding")
    chunks = chunk_text(text, settings.system)
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
