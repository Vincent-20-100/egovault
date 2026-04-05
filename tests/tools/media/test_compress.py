import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.schemas import CompressResult


def test_compress_audio_returns_compress_result(tmp_path):
    from tools.media.compress import compress_audio

    input_file = tmp_path / "audio.mp3"
    input_file.write_bytes(b"x" * 1000)
    output_file = tmp_path / "audio.opus"
    output_file.write_bytes(b"x" * 100)

    with patch("subprocess.run") as mock_run, \
         patch("os.path.getsize", side_effect=lambda p: 100 if str(p).endswith(".opus") else 1000):
        mock_run.return_value = MagicMock(returncode=0)
        result = compress_audio(str(input_file), bitrate_kbps=12)

    assert isinstance(result, CompressResult)
    assert result.output_path.endswith(".opus")
    assert result.original_size_bytes == 1000
    assert result.compressed_size_bytes == 100


def test_compress_audio_calls_ffmpeg(tmp_path):
    from tools.media.compress import compress_audio

    input_file = tmp_path / "audio.mp3"
    input_file.write_bytes(b"x" * 500)
    output_file = tmp_path / "audio.opus"
    output_file.write_bytes(b"x" * 50)

    with patch("subprocess.run") as mock_run, \
         patch("os.path.getsize", side_effect=lambda p: 50 if str(p).endswith(".opus") else 500):
        mock_run.return_value = MagicMock(returncode=0)
        compress_audio(str(input_file))

    cmd = mock_run.call_args[0][0]
    assert "ffmpeg" in cmd
    assert "libopus" in cmd


def test_compress_audio_default_bitrate(tmp_path):
    from tools.media.compress import compress_audio

    input_file = tmp_path / "audio.mp3"
    input_file.write_bytes(b"x" * 500)

    with patch("subprocess.run") as mock_run, \
         patch("os.path.getsize", return_value=100):
        mock_run.return_value = MagicMock(returncode=0)
        compress_audio(str(input_file))

    cmd = mock_run.call_args[0][0]
    assert "12k" in cmd
