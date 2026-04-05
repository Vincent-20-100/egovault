import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from tests.conftest import make_embedding

from core.schemas import ChunkResult, Source
from core.errors import LargeFormatError


def _chunk(uid="c1", pos=0):
    return ChunkResult(uid=uid, position=pos, content="pdf chunk content", token_count=3)


def test_ingest_pdf_returns_rag_ready_source(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_bytes(b"fake pdf bytes")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="PDF extracted text content."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        result = ingest_pdf(str(pdf_file), settings, title="Mon Document")

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "pdf"


def test_ingest_pdf_stores_transcript(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf
    from infrastructure.db import get_source

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="PDF content here."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        result = ingest_pdf(str(pdf_file), settings)

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

    pdf_file = tmp_path / "book.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="Book content here."), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        result = ingest_pdf(str(pdf_file), settings, source_type="livre")

    assert result.source_type == "livre"


def test_ingest_pdf_raises_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "big.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text",
               return_value=" ".join(["word"] * 50001)), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()):

        with pytest.raises(LargeFormatError):
            ingest_pdf(str(pdf_file), settings)


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

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="pdf text content"), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_pdf._llm_is_configured", return_value=True), \
         patch("workflows.ingest_pdf.generate_note_from_source",
               return_value=_make_pdf_note_result()) as mock_gen:

        result = ingest_pdf(str(pdf_file), settings, auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_pdf_auto_generate_false_skips_note(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_pdf import ingest_pdf

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    pdf_file = tmp_path / "test2.pdf"
    pdf_file.write_bytes(b"fake pdf")

    with patch("workflows.ingest_pdf._extract_pdf_text", return_value="pdf text content"), \
         patch("workflows.ingest_pdf.chunk_text", return_value=[_chunk("c2")]), \
         patch("workflows.ingest_pdf.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_pdf.generate_note_from_source") as mock_gen:

        result = ingest_pdf(str(pdf_file), settings, auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
