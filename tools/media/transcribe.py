"""
Audio/video transcription tool.

Input  : file path + language hint
Output : TranscriptResult (text, language, duration)
No DB write.
"""

from core.schemas import TranscriptResult
from core.logging import loggable


@loggable("transcribe")
def transcribe(file_path: str, language: str = "fr") -> TranscriptResult:
    """
    Transcribe an audio or video file using the configured engine.
    Falls back to auto language detection if language hint is not recognised.
    No DB write.
    """
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path, language=language)
    text = " ".join(seg.text.strip() for seg in segments)
    return TranscriptResult(
        text=text,
        language=info.language,
        duration_seconds=info.duration,
    )
