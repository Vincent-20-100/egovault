# tests/core/test_security.py
"""Tests for core.security — input validation utilities."""

import sys
import os
import stat

import pytest

from unittest.mock import patch

from core.security import (
    validate_youtube_url, validate_file_path, validate_web_url,
    set_restrictive_permissions, _is_private_ip,
)


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


import socket


def _mock_resolve_public(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]


def _mock_resolve_private(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]


def _mock_resolve_link_local(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))]


class TestValidateWebUrl:
    @patch("core.security.socket.getaddrinfo", side_effect=_mock_resolve_public)
    def test_accepts_https_url(self, mock_dns):
        assert validate_web_url("https://example.com/page") == "https://example.com/page"

    @patch("core.security.socket.getaddrinfo", side_effect=_mock_resolve_public)
    def test_accepts_http_url(self, mock_dns):
        assert validate_web_url("http://example.com/page") == "http://example.com/page"

    @patch("core.security.socket.getaddrinfo", side_effect=_mock_resolve_private)
    def test_rejects_private_ip_127(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://localhost/admin")

    @patch("core.security.socket.getaddrinfo",
           side_effect=lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))])
    def test_rejects_private_ip_10(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://internal.corp/secret")

    @patch("core.security.socket.getaddrinfo",
           side_effect=lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("172.16.5.1", 0))])
    def test_rejects_private_ip_172_16(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://internal.corp/secret")

    @patch("core.security.socket.getaddrinfo",
           side_effect=lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))])
    def test_rejects_private_ip_192_168(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://router.local/config")

    @patch("core.security.socket.getaddrinfo", side_effect=_mock_resolve_link_local)
    def test_rejects_link_local_169_254(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_cloud_metadata(self):
        with pytest.raises(ValueError, match="blocked metadata"):
            validate_web_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_rejects_file_scheme(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_web_url("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_web_url("ftp://ftp.example.com/file.txt")

    def test_rejects_data_scheme(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_web_url("data:text/html,<h1>hello</h1>")

    def test_rejects_no_hostname(self):
        with pytest.raises(ValueError):
            validate_web_url("http://")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            validate_web_url("")

    @patch("core.security.socket.getaddrinfo",
           side_effect=lambda *a, **k: [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0))])
    def test_rejects_ipv6_loopback(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://[::1]/admin")

    @patch("core.security.socket.getaddrinfo",
           side_effect=lambda *a, **k: [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("fc00::1", 0, 0, 0))])
    def test_rejects_ipv6_private(self, mock_dns):
        with pytest.raises(ValueError, match="private or reserved"):
            validate_web_url("http://[fc00::1]/admin")


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
