"""
Media Retrieval & Inspection Tool.

Reads image/media assets from the confined user media directory for LLM inspection.
"""
from __future__ import annotations

import base64
import mimetypes
from typing import TYPE_CHECKING

from core.errors import NotFoundError, PathTraversalError
from core.logging import loggable
from core.schemas import MediaAssetResult

if TYPE_CHECKING:
    from core.context import VaultContext


@loggable("get_media")
def get_media(
    file_path: str,
    ctx: VaultContext,
) -> MediaAssetResult:
    """
    Safely retrieve a media asset from media_path for LLM visual inspection.
    """
    media_dir = ctx.media_path
    target_path = media_dir / file_path

    # Check path containment before checking file existence
    try:
        resolved = target_path.resolve()
        resolved.relative_to(media_dir.resolve())
    except ValueError:
        raise PathTraversalError(file_path)

    if not resolved.exists() or not resolved.is_file():
        raise NotFoundError(
            error_code="media_not_found",
            user_message=f"Media asset not found: {file_path}",
            actionable_hint="Verify that the image/figure file exists under media_dir.",
        )

    raw_bytes = resolved.read_bytes()
    mime_type, _ = mimetypes.guess_type(str(resolved))

    return MediaAssetResult(
        file_path=str(resolved),
        mime_type=mime_type or "application/octet-stream",
        size_bytes=len(raw_bytes),
        content_base64=base64.b64encode(raw_bytes).decode("ascii"),
    )
