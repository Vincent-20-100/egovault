import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from core.errors import PathTraversalError


def test_get_media_security_confinement(ctx):
    from tools.media.get_media import get_media

    # Path traversal attempt outside media directory
    with pytest.raises(PathTraversalError, match="outside allowed directories"):
        get_media("../../etc/passwd", ctx)


def test_get_media_valid_file(ctx):
    from tools.media.get_media import get_media

    media_dir = ctx.media_path
    media_dir.mkdir(parents=True, exist_ok=True)
    test_img = media_dir / "test_fig.png"

    # Create a 1x1 PNG file
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xafA\x04\x00\x00\x00\x00IEND\xaeB`\x82"
    test_img.write_bytes(png_bytes)

    result = get_media("test_fig.png", ctx)
    assert result.file_path == str(test_img.resolve())
    assert result.mime_type == "image/png"
    assert result.content_base64 is not None
    assert result.size_bytes == len(png_bytes)

