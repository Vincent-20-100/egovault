"""Tests for fetch_subtitles tool — mocks external APIs at module level."""

import sys
from unittest.mock import patch, MagicMock

import pytest

from core.schemas import SubtitleResult

# Inject fake modules so late imports succeed without the real packages
if "youtube_transcript_api" not in sys.modules:
    sys.modules["youtube_transcript_api"] = MagicMock()
if "faster_whisper" not in sys.modules:
    sys.modules["faster_whisper"] = MagicMock()


YT_URL = "https://youtube.com/watch?v=dQw4w9WgXcQ"


def _make_mock_transcript(entries):
    """Build a mock FetchedTranscript from a list of dicts with 'text' keys."""
    snippets = []
    for entry in entries:
        snippet = MagicMock()
        snippet.text = entry["text"]
        snippets.append(snippet)
    mock_transcript = MagicMock()
    mock_transcript.__iter__ = MagicMock(return_value=iter(snippets))
    mock_transcript.language_code = "fr"
    return mock_transcript


def test_fetch_subtitles_returns_subtitle_result():
    from tools.media.fetch_subtitles import fetch_subtitles

    mock_transcript = _make_mock_transcript([
        {"text": "Hello world"},
        {"text": "Foo bar"},
    ])
    # Patch the class so that instances return the mock transcript on .fetch()
    mock_api = MagicMock()
    mock_api.fetch.return_value = mock_transcript
    with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api):
        result = fetch_subtitles(YT_URL, language="fr")

    assert isinstance(result, SubtitleResult)
    assert result.source == "subtitles"
    assert "Hello world" in result.text
    assert "Foo bar" in result.text


def test_fetch_subtitles_joins_entries():
    from tools.media.fetch_subtitles import fetch_subtitles

    mock_transcript = _make_mock_transcript([{"text": "A"}, {"text": "B"}, {"text": "C"}])
    mock_api = MagicMock()
    mock_api.fetch.return_value = mock_transcript
    with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api):
        result = fetch_subtitles(YT_URL)

    assert "A" in result.text and "B" in result.text and "C" in result.text


def test_fetch_subtitles_fallback_to_transcription(tmp_path):
    from tools.media.fetch_subtitles import fetch_subtitles
    from core.schemas import TranscriptResult

    # Make the API instance raise so the fallback path triggers
    mock_api = MagicMock()
    mock_api.fetch.side_effect = Exception("No subtitles")
    with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api), \
         patch("tools.media.fetch_subtitles._download_audio",
               return_value=str(tmp_path / "audio.mp3")), \
         patch("tools.media.fetch_subtitles.transcribe",
               return_value=TranscriptResult(text="Transcribed text", language="fr",
                                             duration_seconds=60.0)):
        result = fetch_subtitles(YT_URL)

    assert result.source == "transcription"
    assert result.text == "Transcribed text"


def test_fetch_subtitles_extracts_video_id():
    from tools.media.fetch_subtitles import _extract_video_id

    assert _extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ&t=30") == "dQw4w9WgXcQ"
