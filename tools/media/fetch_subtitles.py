"""
YouTube subtitle fetcher.

Input  : YouTube URL + language
Output : SubtitleResult (text, language, source indicator)
No DB write. Falls back to audio download + transcribe if subtitles unavailable.
"""

import tempfile
from pathlib import Path

from core.schemas import SubtitleResult
from core.logging import loggable
from tools.media.transcribe import transcribe


def _extract_video_id(url: str) -> str:
    from core.security import validate_youtube_url
    video_id = validate_youtube_url(url)
    if video_id is None:
        raise ValueError(f"Cannot extract video ID from URL: {url}")
    return video_id


def _download_audio(youtube_url: str, output_dir: str) -> str:
    import yt_dlp
    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_dir}/audio.%(ext)s",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([youtube_url])
    audio_files = list(Path(output_dir).glob("audio.*"))
    if not audio_files:
        raise RuntimeError(f"yt-dlp did not produce any audio file in {output_dir}")
    return str(audio_files[0])


@loggable("fetch_subtitles")
def fetch_subtitles(youtube_url: str, language: str = "fr") -> SubtitleResult:
    """
    Fetch YouTube subtitles if available, fall back to transcription.
    SubtitleResult.source indicates 'subtitles' or 'transcription'.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    video_id = _extract_video_id(youtube_url)
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=[language, "en"])
        text = " ".join(snippet.text for snippet in transcript)
        return SubtitleResult(text=text, language=language, source="subtitles")
    except Exception:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = _download_audio(youtube_url, tmpdir)
            result = transcribe(audio_path, language=language)
        return SubtitleResult(
            text=result.text, language=result.language, source="transcription"
        )
