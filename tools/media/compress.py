"""
Audio/video compression tool.

Input  : file path + target bitrate
Output : CompressResult (output path, size before/after)
No DB write.
"""

import os
import subprocess
from pathlib import Path

from core.schemas import CompressResult
from core.logging import loggable


@loggable("compress_audio")
def compress_audio(file_path: str, bitrate_kbps: int = 12) -> CompressResult:
    """
    Compress audio to Opus mono via ffmpeg.
    Default: 12kbps mono 16kHz (~5MB/hour).
    Output file written alongside source with .opus extension.
    No DB write.
    """
    input_path = Path(file_path)
    output_path = input_path.with_suffix(".opus")
    original_size = os.path.getsize(str(input_path))

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-c:a", "libopus",
            "-b:a", f"{bitrate_kbps}k",
            "-ac", "1",
            "-ar", "16000",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )

    compressed_size = os.path.getsize(str(output_path))
    return CompressResult(
        output_path=str(output_path),
        original_size_bytes=original_size,
        compressed_size_bytes=compressed_size,
    )


@loggable("compress_video")
def compress_video(file_path: str) -> CompressResult:
    """
    Compress video to AV1 via ffmpeg.
    No DB write.
    """
    raise NotImplementedError("compress_video not implemented in v1")
