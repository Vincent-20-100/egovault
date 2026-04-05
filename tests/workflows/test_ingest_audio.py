import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
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
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

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
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

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
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

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
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

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
         patch("workflows.ingest_audio.embed_text", return_value=[0.1] * 768):

        result = ingest_audio(str(audio_file), settings, source_type="audio")

    assert result.source_type == "audio"
