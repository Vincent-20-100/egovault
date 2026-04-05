"""Tests for the unified ingest pipeline."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from tests.conftest import make_embedding

from core.schemas import SubtitleResult, ChunkResult, Source, NoteResult, Note
from core.errors import LargeFormatError, EmptyContentError


# -- Helpers --

def _make_ctx(tmp_settings, tmp_db, tmp_path, generate=None):
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


def _make_chunk(uid="c1", pos=0, text="chunk content"):
    return ChunkResult(uid=uid, position=pos, content=text, token_count=3)


def _make_note_result(source_uid="src"):
    note = Note(
        uid="note-1", source_uid=source_uid, slug="test-note",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Test Note", docstring="desc",
        body="body", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test"],
    )
    return NoteResult(note=note, markdown_path="/vault/test-note.md")


# -- Extractor registry --

def test_unknown_source_type_raises(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    with pytest.raises(ValueError, match="No extractor for source type"):
        ingest("unknown_type", "target", ctx)


def test_text_extractor_identity(tmp_settings, tmp_db, tmp_path):
    """texte extractor returns the input text as-is."""
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            source = ingest("texte", "Hello world test content", ctx, title="Test")

    assert source.source_type == "texte"
    assert source.status == "rag_ready"
    assert source.transcript == "Hello world test content"


def test_html_extractor_calls_parse_html(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    from core.schemas import ParseHtmlResult

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    mock_result = ParseHtmlResult(text="Extracted text", title="Page Title",
                                  author=None, date_published=None, word_count=2)

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("tools.text.parse_html.parse_html", return_value=mock_result) as mock_ph:
                source = ingest("html", "<p>Extracted text</p>", ctx, title="HTML Test")

    mock_ph.assert_called_once_with("<p>Extracted text</p>")
    assert source.status == "rag_ready"


def test_youtube_extractor(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    mock_subtitle = SubtitleResult(text="Video transcript here", language="fr", source="subtitles")

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("tools.media.fetch_subtitles.fetch_subtitles", return_value=mock_subtitle):
                source = ingest("youtube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ctx)

    assert source.source_type == "youtube"
    assert source.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert source.status == "rag_ready"


def test_pdf_extractor(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF page content"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                source = ingest("pdf", "/fake/doc.pdf", ctx, title="My PDF")

    assert source.source_type == "pdf"
    assert source.status == "rag_ready"


def test_audio_extractor(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    from core.schemas import CompressResult, TranscriptResult
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    mock_compress = CompressResult(output_path="/tmp/compressed.mp3")
    mock_transcript = TranscriptResult(text="Audio transcript here", language="fr")

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("tools.media.compress.compress_audio", return_value=mock_compress):
                with patch("tools.media.transcribe.transcribe", return_value=mock_transcript):
                    source = ingest("audio", "/fake/audio.mp3", ctx)

    assert source.source_type == "audio"
    assert source.status == "rag_ready"


# -- Common pipeline --

def test_status_transitions(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    statuses = []
    original_update = ctx.db.update_source_status

    def track_status(uid, status):
        statuses.append(status)
        return original_update(uid, status)

    ctx.db.update_source_status = track_status

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            ingest("texte", "Some text content here", ctx, title="Status Test")

    assert statuses == ["transcribing", "text_ready", "embedding", "rag_ready"]


def test_empty_content_raises(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    with pytest.raises(EmptyContentError):
        ingest("texte", "", ctx, title="Empty")


def test_whitespace_only_raises(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    with pytest.raises(EmptyContentError):
        ingest("texte", "   \n\t  ", ctx, title="Whitespace")


def test_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    # Threshold is 50000 tokens by default
    long_text = "word " * 60000

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with pytest.raises(LargeFormatError) as exc_info:
                ingest("texte", long_text, ctx, title="Large")

    assert exc_info.value.token_count == 60000
    # Source should still reach rag_ready
    source = ctx.db.get_source(exc_info.value.source_uid)
    assert source.status == "rag_ready"


# -- Note generation --

def test_auto_generate_true_calls_generate(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest

    mock_gen = MagicMock()
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path, generate=mock_gen)

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("workflows.ingest.generate_note_from_source") as mock_gnfs:
                ingest("texte", "Some content here", ctx, title="Gen",
                       auto_generate_note=True)

    mock_gnfs.assert_called_once()


def test_auto_generate_false_skips(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest

    mock_gen = MagicMock()
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path, generate=mock_gen)

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("workflows.ingest.generate_note_from_source") as mock_gnfs:
                ingest("texte", "Some content here", ctx, title="NoGen",
                       auto_generate_note=False)

    mock_gnfs.assert_not_called()


def test_no_llm_configured_skips_note(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path, generate=None)

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("workflows.ingest.generate_note_from_source") as mock_gnfs:
                ingest("texte", "Some content here", ctx, title="NoLLM",
                       auto_generate_note=True)

    mock_gnfs.assert_not_called()


# -- Slug generation --

def test_youtube_slug_uses_video_id(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    mock_subtitle = SubtitleResult(text="Transcript text here", language="fr", source="subtitles")

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            with patch("tools.media.fetch_subtitles.fetch_subtitles", return_value=mock_subtitle):
                source = ingest("youtube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ctx)

    assert "dqw4w9wgxcq" in source.slug


def test_title_used_for_slug_when_provided(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest import ingest
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)

    with patch("workflows.ingest.chunk_text", return_value=[_make_chunk()]):
        with patch("workflows.ingest.embed_text", return_value=make_embedding(0.0)):
            source = ingest("texte", "Content here", ctx, title="Ma Super Note")

    assert source.slug == "ma-super-note"
