# tests/core/test_security.py
"""Tests for core.security — input validation utilities."""

import sys
import os
import stat

import pytest

from core.security import validate_youtube_url, validate_file_path, set_restrictive_permissions


class TestValidateYoutubeUrl:
    def test_standard_url(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42") == "dQw4w9WgXcQ"

    def test_url_with_playlist(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest") == "dQw4w9WgXcQ"

    def test_rejects_crafted_url(self):
        # This is the attack vector: evil domain with youtube in query string
        assert validate_youtube_url("http://evil.com?youtube.com/watch?v=dQw4w9WgXcQ") is None

    def test_rejects_no_video_id(self):
        assert validate_youtube_url("https://www.youtube.com/") is None

    def test_rejects_short_video_id(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=short") is None

    def test_rejects_empty(self):
        assert validate_youtube_url("") is None

    def test_rejects_non_youtube(self):
        assert validate_youtube_url("https://vimeo.com/123456") is None

    def test_mobile_url(self):
        assert validate_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


class TestValidateFilePath:
    def test_valid_path_under_media(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        target = media / "test.mp3"
        target.touch()
        assert validate_file_path(str(target), [media]) == target

    def test_rejects_path_outside_allowed(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        outside = tmp_path / "outside.txt"
        outside.touch()
        assert validate_file_path(str(outside), [media]) is None

    def test_rejects_traversal(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        assert validate_file_path(str(media / ".." / "etc" / "passwd"), [media]) is None

    def test_rejects_nonexistent(self, tmp_path):
        media = tmp_path / "media"
        media.mkdir()
        assert validate_file_path(str(media / "ghost.mp3"), [media]) is None

    def test_multiple_allowed_dirs(self, tmp_path):
        media = tmp_path / "media"
        vault = tmp_path / "vault"
        media.mkdir()
        vault.mkdir()
        target = vault / "note.md"
        target.touch()
        assert validate_file_path(str(target), [media, vault]) == target


class TestSetRestrictivePermissions:
    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not effective on Windows")
    def test_sets_0600_on_file(self, tmp_path):
        f = tmp_path / "test.db"
        f.touch()
        set_restrictive_permissions(f)
        mode = stat.S_IMODE(os.stat(f).st_mode)
        assert mode == 0o600

    def test_does_not_crash_on_windows(self, tmp_path):
        """On Windows, the function should be a no-op (no crash)."""
        f = tmp_path / "test.db"
        f.touch()
        set_restrictive_permissions(f)  # Should not raise
