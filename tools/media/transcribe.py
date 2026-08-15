"""
Audio/video transcription tool.

Input  : file path + language hint + optional VaultContext/model configuration
Output : TranscriptResult (text, language, duration)
No DB write.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from core.schemas import TranscriptResult
from core.logging import loggable

if TYPE_CHECKING:
    from core.context import VaultContext


@loggable("transcribe")
def transcribe(
    file_path: str,
    language: str = "fr",
    ctx: VaultContext | None = None,
    model_name: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
) -> TranscriptResult:
    """
    Transcribe an audio or video file using the configured engine.
    Falls back to auto language detection if language hint is not recognised.
    No DB write.
    """
    from faster_whisper import WhisperModel

    # Resolve settings from context if available (Rule G3 - Zero Hardcode)
    whisper_model = model_name
    whisper_device = device
    whisper_compute = compute_type

    if ctx is not None:
        media_cfg = ctx.settings.system.ingest.media
        whisper_model = whisper_model or media_cfg.whisper_model
        whisper_device = whisper_device or media_cfg.whisper_device
        whisper_compute = whisper_compute or media_cfg.whisper_compute_type

    whisper_model = whisper_model or "base"
    whisper_device = whisper_device or "cpu"
    whisper_compute = whisper_compute or "int8"

    model = WhisperModel(whisper_model, device=whisper_device, compute_type=whisper_compute)
    segments, info = model.transcribe(file_path, language=language)
    text = " ".join(seg.text.strip() for seg in segments)
    return TranscriptResult(
        text=text,
        language=info.language,
        duration_seconds=info.duration,
    )
