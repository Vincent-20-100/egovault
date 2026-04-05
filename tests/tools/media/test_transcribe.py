import pytest
from unittest.mock import patch, MagicMock
from core.schemas import TranscriptResult


def _mock_whisper(segments_text="Hello world.", language="fr", duration=10.0):
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = segments_text
    mock_info = MagicMock()
    mock_info.language = language
    mock_info.duration = duration
    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    return mock_model


def test_transcribe_returns_transcript_result():
    from tools.media.transcribe import transcribe

    with patch("faster_whisper.WhisperModel", return_value=_mock_whisper()):
        result = transcribe("audio.mp3", language="fr")

    assert isinstance(result, TranscriptResult)
    assert result.text == "Hello world."
    assert result.language == "fr"
    assert result.duration_seconds == 10.0


def test_transcribe_joins_multiple_segments():
    from tools.media.transcribe import transcribe

    mock_model = MagicMock()
    seg1, seg2 = MagicMock(), MagicMock()
    seg1.text = "  First segment.  "
    seg2.text = "  Second segment.  "
    mock_info = MagicMock()
    mock_info.language = "fr"
    mock_info.duration = 20.0
    mock_model.transcribe.return_value = ([seg1, seg2], mock_info)

    with patch("faster_whisper.WhisperModel", return_value=mock_model):
        result = transcribe("audio.mp3")

    assert "First segment." in result.text
    assert "Second segment." in result.text


def test_transcribe_passes_language_hint():
    from tools.media.transcribe import transcribe

    mock_model = _mock_whisper()
    with patch("faster_whisper.WhisperModel", return_value=mock_model):
        transcribe("audio.mp3", language="en")

    call_kwargs = mock_model.transcribe.call_args
    assert call_kwargs[1].get("language") == "en" or "en" in str(call_kwargs)
