# core/security.py
"""
Security utilities for EgoVault.

validate_youtube_url() — strict YouTube URL validation.
validate_file_path() — path containment check (added in Task 10).
set_restrictive_permissions() — set 0600 on files (Unix only, added in Task 15).
"""

import os
import re
import sys
from pathlib import Path

# YouTube URL must have youtube.com or youtu.be as the actual host
_YOUTUBE_HOST_RE = re.compile(
    r"^https?://(?:www\.|m\.)?(?:youtube\.com/watch\?.*v=|youtu\.be/)"
)
_VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def validate_youtube_url(url: str) -> str | None:
    """
    Extract YouTube video ID from a URL using strict host validation.
    Returns the 11-char video ID, or None if the URL is invalid.
    """
    if not url or not _YOUTUBE_HOST_RE.match(url):
        return None

    # Extract video ID
    if "youtu.be/" in url:
        # Short URL: https://youtu.be/VIDEO_ID
        path_part = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    else:
        # Long URL: https://www.youtube.com/watch?v=VIDEO_ID
        match = re.search(r"[?&]v=([^&]+)", url)
        if not match:
            return None
        path_part = match.group(1)

    # Validate video ID format (exactly 11 alphanumeric + _-)
    if _VIDEO_ID_RE.fullmatch(path_part):
        return path_part
    return None


def validate_file_path(file_path: str, allowed_dirs: list[Path]) -> Path | None:
    """
    Validate that a file path resolves to a location under one of the allowed directories.
    Returns the resolved Path if valid, None otherwise.
    """
    try:
        resolved = Path(file_path).resolve()
    except (OSError, ValueError):
        return None

    if not resolved.exists():
        return None

    for allowed in allowed_dirs:
        try:
            resolved.relative_to(allowed.resolve())
            return resolved
        except ValueError:
            continue
    return None


def set_restrictive_permissions(path: Path) -> None:
    """
    Set file permissions to owner-only read/write (0600) on Unix.
    No-op on Windows (relies on user profile directory placement).
    """
    if sys.platform == "win32":
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # Best effort — don't crash if permissions can't be set
