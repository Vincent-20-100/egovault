import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from tests.conftest import make_embedding

from core.schemas import TranscriptResult, CompressResult, ChunkResult, Source
from core.errors import LargeFormatError


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


def test_ingest_audio_returns_rag_ready_source(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), settings, title="Test Audio")

    assert isinstance(result, Source)
    assert result.status == "rag_ready"
    assert result.source_type == "audio"


def test_ingest_audio_stores_transcript(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio
    from infrastructure.db import get_source

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), settings)

    stored = get_source(tmp_db, result.uid)
    assert stored.transcript == "Audio transcript text here."


def test_ingest_audio_uses_title_for_slug(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), settings, title="Mon Podcast Génial")

    assert "mon-podcast-genial" in result.slug


def test_ingest_audio_raises_large_format_error(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
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
            ingest_audio(str(audio_file), settings)


def test_ingest_audio_detects_video_source_type(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "recording.mp3"
    audio_file.write_bytes(b"fake mp3")

    with patch("workflows.ingest_audio.compress_audio", return_value=_compress_result(tmp_path)), \
         patch("workflows.ingest_audio.transcribe", return_value=_transcript()), \
         patch("workflows.ingest_audio.chunk_text", return_value=[_chunk()]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()):

        result = ingest_audio(str(audio_file), settings, source_type="audio")

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

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake audio")

    with patch("workflows.ingest_audio.compress_audio",
               return_value=MagicMock(output_path=str(audio_file))), \
         patch("workflows.ingest_audio.transcribe",
               return_value=MagicMock(text="audio transcript here")), \
         patch("workflows.ingest_audio.chunk_text", return_value=[MagicMock(
             uid="c1", position=0, content="chunk", token_count=3)]), \
         patch("workflows.ingest_audio.embed_text", return_value=make_embedding()), \
         patch("workflows.ingest_audio._llm_is_configured", return_value=True), \
         patch("workflows.ingest_audio.generate_note_from_source",
               return_value=_make_audio_note_result()) as mock_gen:

        result = ingest_audio(str(audio_file), settings, auto_generate_note=True)

    assert result.status == "rag_ready"
    mock_gen.assert_called_once()


def test_ingest_audio_auto_generate_false_skips_note(tmp_settings, tmp_db, tmp_path):
    from workflows.ingest_audio import ingest_audio

    settings = tmp_settings.model_copy(
        update={"install": tmp_settings.install.model_copy(
            update={"paths": tmp_settings.install.paths.model_copy(
                update={"db_file": str(tmp_db)}
            )}
        )}
    )
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

        result = ingest_audio(str(audio_file), settings, auto_generate_note=False)

    assert result.status == "rag_ready"
    mock_gen.assert_not_called()
