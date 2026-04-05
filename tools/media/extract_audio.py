"""
Audio extraction from video files.

Input  : video file path
Output : AudioFileResult (path to extracted audio file)
No DB write.
"""

from core.schemas import AudioFileResult
from core.logging import loggable


@loggable("extract_audio")
def extract_audio(file_path: str) -> AudioFileResult:
    """
    Extract audio track from a video file via ffmpeg.
    Output: .wav file alongside the source video.
    No DB write.
    """
    ...
