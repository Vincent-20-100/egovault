"""Tests for tools.web.fetch_web — web page fetching with SSRF protection."""

from unittest.mock import patch, MagicMock
import socket

import pytest

from core.errors import IngestError


SAMPLE_HTML = """
<html>
<head><title>Test Article</title>
<meta name="author" content="Jane Doe">
</head>
<body>
<article>
<p>This is a test article with enough words to pass the minimum word count threshold for extraction validation.</p>
<p>It contains multiple paragraphs of content that would be found on a typical web page article.</p>
</article>
</body>
</html>
"""


def _make_ctx(extraction_tier=0, max_response_mb=10, timeout_seconds=30,
              min_fetch_interval_seconds=0, max_redirects=5):
    """Build a minimal mock VaultContext with web config."""
    ctx = MagicMock()
    ctx.settings.system.web.extraction_tier = extraction_tier
    ctx.settings.system.web.max_response_mb = max_response_mb
    ctx.settings.system.web.timeout_seconds = timeout_seconds
    ctx.settings.system.web.min_fetch_interval_seconds = min_fetch_interval_seconds
    ctx.settings.system.web.max_redirects = max_redirects
    return ctx


def _mock_dns_public(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]


def _mock_dns_private(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]


class FakeResponse:
    """Minimal mock for httpx streaming response."""

    def __init__(self, html=SAMPLE_HTML, content_type="text/html; charset=utf-8",
                 url="https://example.com/article", status_code=200):
        self._html = html.encode("utf-8")
        self.headers = {"content-type": content_type}
        self.url = url
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def iter_bytes(self, chunk_size=8192):
        for i in range(0, len(self._html), chunk_size):
            yield self._html[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeClient:
    def __init__(self, response=None, **kwargs):
        self._response = response or FakeResponse()
        self._kwargs = kwargs

    def stream(self, method, url):
        return self._response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_valid_page(mock_client_cls, mock_dns):
    from tools.web.fetch_web import fetch_web
    mock_client_cls.return_value = FakeClient()
    ctx = _make_ctx()
    result = fetch_web("https://example.com/article", ctx)
    assert result.final_url == "https://example.com/article"
    assert result.word_count >= 10
    assert len(result.text) > 0
    assert "text/html" in result.content_type


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_rejects_non_html(mock_client_cls, mock_dns):
    from tools.web.fetch_web import fetch_web
    mock_client_cls.return_value = FakeClient(response=FakeResponse(content_type="application/pdf"))
    ctx = _make_ctx()
    with pytest.raises(ValueError, match="HTML page"):
        fetch_web("https://example.com/file.pdf", ctx)


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_rejects_oversized(mock_client_cls, mock_dns):
    from tools.web.fetch_web import fetch_web
    huge_html = "<html><body>" + "x" * (2 * 1024 * 1024) + "</body></html>"
    mock_client_cls.return_value = FakeClient(response=FakeResponse(html=huge_html))
    ctx = _make_ctx(max_response_mb=1)
    with pytest.raises(ValueError, match="too large"):
        fetch_web("https://example.com/huge", ctx)


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_private)
def test_fetch_rejects_private_ip(mock_dns):
    from tools.web.fetch_web import fetch_web
    ctx = _make_ctx()
    with pytest.raises(ValueError, match="private or reserved"):
        fetch_web("http://localhost/admin", ctx)


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_post_redirect_validation(mock_client_cls, mock_dns):
    """If redirect lands on a different host, re-validate its IP."""
    from tools.web.fetch_web import fetch_web
    response = FakeResponse(url="https://evil.internal/page")
    mock_client_cls.return_value = FakeClient(response=response)
    ctx = _make_ctx()
    # The redirect target resolves to public (mocked), but the hostname differs
    # from original, so resolve_and_validate_host is called for the new host.
    # Since our mock returns public IP, this should succeed.
    result = fetch_web("https://example.com/article", ctx)
    assert result.final_url == "https://evil.internal/page"


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_empty_extraction(mock_client_cls, mock_dns):
    from tools.web.fetch_web import fetch_web
    empty_html = "<html><body><nav>Menu</nav></body></html>"
    mock_client_cls.return_value = FakeClient(response=FakeResponse(html=empty_html))
    ctx = _make_ctx()
    with pytest.raises(IngestError, match="meaningful text"):
        fetch_web("https://example.com/empty", ctx)


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_tier0_extraction(mock_client_cls, mock_dns):
    from tools.web.fetch_web import fetch_web
    mock_client_cls.return_value = FakeClient()
    ctx = _make_ctx(extraction_tier=0)
    result = fetch_web("https://example.com/article", ctx)
    assert result.title == "Test Article"


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_tier1_fallback(mock_client_cls, mock_dns):
    """When trafilatura is not installed, falls back to parse_html."""
    from tools.web.fetch_web import fetch_web
    mock_client_cls.return_value = FakeClient()
    ctx = _make_ctx(extraction_tier=1)
    # trafilatura not installed in test env → fallback to parse_html
    result = fetch_web("https://example.com/article", ctx)
    assert result.word_count >= 10


@patch("core.security.socket.getaddrinfo", side_effect=_mock_dns_public)
@patch("tools.web.fetch_web.httpx.Client")
def test_fetch_rate_limit(mock_client_cls, mock_dns):
    """Two rapid calls with interval=0 should both succeed (no sleep)."""
    import tools.web.fetch_web as mod
    mod._last_fetch_time = 0.0  # reset state
    mock_client_cls.return_value = FakeClient()
    ctx = _make_ctx(min_fetch_interval_seconds=0)
    r1 = mod.fetch_web("https://example.com/page1", ctx)
    r2 = mod.fetch_web("https://example.com/page2", ctx)
    assert r1.text and r2.text
