import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from core.schemas import Source, NoteCandidate


def test_reingest_pdf_sources_dry_run(ctx):
    from scripts.maintenance.reingest_pdf_sources import reingest_pdf_sources

    # Insert a dummy pdf source
    src = Source(
        uid="src_pdf_1",
        slug="pdf-doc-1",
        source_type="pdf",
        status="rag_ready",
        date_added="2026-08-16",
    )
    ctx.db.insert_source(src)

    cand = NoteCandidate(
        uid="cand_1",
        source_uid="src_pdf_1",
        sequence_index=0,
        chunk_uids=["c1"],
        label="Test Candidate",
        status="queued",
        model_version="1.0",
        created_at="2026-08-16",
    )
    ctx.db.insert_note_candidates([cand])

    summary = reingest_pdf_sources(ctx, dry_run=True, source_uid="src_pdf_1")
    assert summary["processed_count"] == 1
    assert summary["dry_run"] is True
