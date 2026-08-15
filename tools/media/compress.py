"""
Audio/video compression tool.

Input  : file path + optional target bitrate / VaultContext
Output : CompressResult (output path, size before/after)
No DB write.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from core.schemas import CompressResult
from core.logging import loggable

if TYPE_CHECKING:
    from core.context import VaultContext


@loggable("compress_audio")
def compress_audio(
    file_path: str,
    bitrate_kbps: int | None = None,
    ctx: VaultContext | None = None,
) -> CompressResult:
    """
    Compress audio to a low-bitrate mono format.
    Output file written alongside source with .opus extension.
    No DB write.
    """
    if bitrate_kbps is None:
        if ctx is not None:
            bitrate_kbps = ctx.settings.system.ingest.media.audio_compression_bitrate_kbps
        else:
            bitrate_kbps = 12

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
    Compress video to a compact format.
    No DB write.
    """
    raise NotImplementedError("compress_video not implemented in v1")
