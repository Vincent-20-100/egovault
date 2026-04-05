import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from tests.conftest import make_embedding

from core.schemas import ChunkResult, Source
from core.errors import LargeFormatError


# -- Helpers --

def _chunk(uid="c1", pos=0):
    return ChunkResult(uid=uid, position=pos, content="pdf chunk content", token_count=3)


def _make_ctx(tmp_settings, tmp_db, tmp_path, generate=None):
    """Build a VaultContext wired to the test database."""
    from infrastructure.vault_db import VaultDB
    from core.context import VaultContext
    from infrastructure.vault_writer import write_note as _write_note

    vault_path = tmp_path / "vault"
    vault_path.mkdir(exist_ok=True)
    media_path = tmp_path / "media"
    media_path.mkdir(exist_ok=True)

    return VaultContext(
        settings=tmp_settings,
        db=VaultDB(tmp_db),
        system_db_path=tmp_path / ".system.db",
        embed=lambda text: make_embedding(0.0),
        generate=generate,
        write_note=_write_note,
        vault_path=vault_path,
        media_path=media_path,
    )


# -- Tests --

def test_ingest_pdf_returns_rag_ready_source(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_bytes(b"fake pdf bytes")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="PDF extracted text content."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        result = ingest_pdf(str(pdf_file), ctx, title="Mon Document")

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "pdf"


def test_ingest_pdf_stores_transcript(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf
    from infrastructure.db import get_source

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="PDF content here."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        result = ingest_pdf(str(pdf_file), ctx)

    stored = get_source(tmp_db, result.uid)
    assert stored.transcript == "PDF content here."


def test_ingest_pdf_livre_source_type(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    # Add "livre" to source_types for this test using a fresh settings
    import yaml
    config_dir = tmp_path / "config2"
    config_dir.mkdir()
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese"],
            "source_types": ["youtube", "audio", "pdf", "livre"],
            "generation_templates": ["standard"],
        },
    }))
    user_dir = tmp_path / "eu"
    (user_dir / "data").mkdir(parents=True)
    (user_dir / "vault" / "notes").mkdir(parents=True)
    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {"content_language": "fr", "obsidian_sync": True, "default_generation_template": "standard"},
    }))
    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir), "db_file": str(tmp_db)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))
    from core.config import load_settings
    settings = load_settings(config_dir)

    ctx = _make_ctx(settings, tmp_db, tmp_path)
    pdf_file = tmp_path / "book.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="Book content here."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        result = ingest_pdf(str(pdf_file), ctx, source_type="livre")

    assert result.source_type == "livre"


def test_ingest_pdf_raises_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    pdf_file = tmp_path / "big.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text",
               return_value=" ".join(["word"] * 50001)), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        with pytest.raises(LargeFormatError):
            ingest_pdf(str(pdf_file), ctx)


def test_ingest_pdf_auto_generate_true_creates_draft(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf
    from core.schemas import NoteResult, Note
    from datetime import date

    def _make_pdf_note_result():
        note = Note(
            uid="note-pdf", source_uid="pdf-src", slug="pdf-note",
            note_type=None, source_type=None, generation_template="standard",
            rating=None, sync_status="synced", title="PDF Note",
            docstring="PDF note desc.", body="PDF note body content.",
            url=None, status="draft",
            date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
            tags=["test-tag"],
        )
        return NoteResult(note=note, markdown_path="/vault/pdf-note.md")

    # Non-None generate so _llm_is_configured returns True
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path, generate=lambda *a: None)
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="pdf text content"), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_pdf.generate_note_from_source",
               return_value=_make_pdf_note_result()) as mock_gen:

        result = ingest_pdf(str(pdf_file), ctx, auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_pdf_auto_generate_false_skips_note(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    pdf_file = tmp_path / "test2.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="pdf text content"), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk("c2")]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_pdf.generate_note_from_source") as mock_gen:

        result = ingest_pdf(str(pdf_file), ctx, auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
