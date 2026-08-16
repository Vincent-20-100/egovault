"""
PDF Maintenance & Safe Migration Script.

Re-ingests PDF sources with structural layout parsing & HD figure extraction.
Purges unconverted candidates while preserving converted active notes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from tools.text.chunk import chunk_text
from tools.text.embed import embed_text
from tools.text.segment import segment_chunks

if TYPE_CHECKING:
    from core.context import VaultContext


def reingest_pdf_sources(
    ctx: VaultContext,
    dry_run: bool = False,
    source_uid: str | None = None,
) -> dict:
    """
    Re-ingest PDF/livre sources with structural layout parsing & HD figure extraction.
    """
    all_sources = [s for s in ctx.db.list_sources(status=None, limit=1000, offset=0) if s.source_type in ("pdf", "livre")]

    if source_uid:
        all_sources = [s for s in all_sources if s.uid == source_uid]

    processed_count = 0
    resegmented_candidates_count = 0

    for src in all_sources:
        processed_count += 1
        if dry_run:
            continue

        # 1. Purge unconverted candidates
        candidates = ctx.db.list_note_candidates(source_uid=src.uid)
        for cand in candidates:
            if cand.status != "converted":
                ctx.db.delete_note_candidate(cand.uid)

        # 2. Extract new text & HD figures if media_path exists
        from tools.media.parse_document import parse_document
        output_media_dir = ctx.media_path / src.slug
        target_path = src.media_path or f"data/media/{src.slug}.pdf"
        if not Path(target_path).exists():
            continue

        parsed = parse_document(target_path, ctx, output_media_dir=output_media_dir)
        if parsed.is_scanned:
            from tools.media.ocr_document import ocr_document
            parsed = ocr_document(target_path, ctx)

        text = parsed.text
        if not text or not text.strip():
            continue

        # 3. Replace chunks and embeddings
        ctx.db.delete_chunks_for_source(src.uid)
        ctx.db.delete_chunk_embeddings_for_source(src.uid)
        ctx.db.update_source_transcript(src.uid, text)

        chunks = chunk_text(text, ctx.settings.system)
        ctx.db.insert_chunks(src.uid, chunks)
        embeddings = []
        for chunk in chunks:
            emb = embed_text(chunk.content, ctx)
            embeddings.append(emb)
            ctx.db.insert_chunk_embeddings(chunk.uid, emb)

        # 4. Re-run topic segmentation to create fresh candidates
        new_candidates = segment_chunks(src.uid, chunks, embeddings, ctx)
        if new_candidates:
            ctx.db.insert_note_candidates(new_candidates)
            resegmented_candidates_count += len(new_candidates)

    return {
        "processed_count": processed_count,
        "resegmented_candidates": resegmented_candidates_count,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="Re-ingest PDF sources with layout parsing & OCR.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate re-ingestion without modifying database.")
    parser.add_argument("--source-uid", type=str, help="Filter to a specific source UID.")
    args = parser.parse_args()

    from core.config import load_settings
    from infrastructure.context import build_context

    ctx = build_context(load_settings())
    summary = reingest_pdf_sources(ctx, dry_run=args.dry_run, source_uid=args.source_uid)
    print(f"Re-ingestion summary: {summary}")


if __name__ == "__main__":
    main()
