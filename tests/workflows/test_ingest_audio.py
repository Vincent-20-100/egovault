import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from tests.conftest import make_embedding

from core.schemas import TranscriptResult, CompressResult, ChunkResult, Source
from core.errors import LargeFormatError


# -- Helpers --

def _compress_result(tmp_path):
    out = tmp_path / "compressed.opus"
    out.write_bytes(b"fake opus data")
    return CompressResult(
        output_path=str(out),
        original_size_bytes=1000,
        compressed_size_bytes=200,
    )


def _transcript():
    return TranscriptResult(text="Audio transcript text here.", language="fr", duration_seconds=60.0)


def _chunk(uid="c1", pos=0):
    return ChunkResult(uid=uid, position=pos, content="chunk content here", token_count=3)


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

def test_ingest_audio_returns_rag_ready_source(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), ctx, title="Test Audio")

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "audio"


def test_ingest_audio_stores_transcript(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio
    from infrastructure.db import get_source

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), ctx)

    stored = get_source(tmp_db, result.uid)
    assert stored.transcript == "Audio transcript text here."


def test_ingest_audio_uses_title_for_slug(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), ctx, title="Mon Podcast Génial")

    assert "mon-podcast-genial" in result.slug


def test_ingest_audio_raises_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")
    big_transcript = TranscriptResult(
        text=" ".join(["word"] * 50001), language="fr", duration_seconds=3600.0
    )

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=big_transcript), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        with pytest.raises(LargeFormatError):
            ingest_audio(str(audio_file), ctx)


def test_ingest_audio_detects_video_source_type(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    audio_file = tmp_path / "recording.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), ctx, source_type="audio")

    assert result.source_type == "audio"


def test_ingest_audio_auto_generate_true_creates_draft(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio
    from core.schemas import NoteResult, Note
    from datetime import date

    def _make_audio_note_result():
        note = Note(
            uid="note-audio", source_uid="audio-src", slug="audio-note",
            note_type=None, source_type=None, generation_template="standard",
            rating=None, sync_status="synced", title="Audio Note",
            docstring="Audio note desc.", body="Audio note body content.",
            url=None, status="draft",
            date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
            tags=["test-tag"],
        )
        return NoteResult(note=note, markdown_path="/vault/audio-note.md")

    # Non-None generate so _llm_is_configured returns True
    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path, generate=lambda *a: None)
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake audio")

    with patch("workflows.ingest_audio.compress_audio",
               return_value=MagicMock(output_path=str(audio_file))), \
         patch("workflows.ingest_audio.transcribe",
               return_value=MagicMock(text="audio transcript here")), \
         patch("workflows.ingest_audio.chunk_text", return_value=[MagicMock(
             uid="c1", position=0, content="chunk", token_count=3)]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_audio.generate_note_from_source",
               return_value=_make_audio_note_result()) as mock_gen:

        result = ingest_audio(str(audio_file), ctx, auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_audio_auto_generate_false_skips_note(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    ctx = _make_ctx(tmp_settings, tmp_db, tmp_path)
    audio_file = tmp_path / "test2.mp3"
    audio_file.write_bytes(b"fake audio")

    with patch("workflows.ingest_audio.compress_audio",
               return_value=MagicMock(output_path=str(audio_file))), \
         patch("workflows.ingest_audio.transcribe",
               return_value=MagicMock(text="audio transcript here")), \
         patch("workflows.ingest_audio.chunk_text", return_value=[MagicMock(
             uid="c2", position=0, content="chunk", token_count=3)]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_audio.generate_note_from_source") as mock_gen:

        result = ingest_audio(str(audio_file), ctx, auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
