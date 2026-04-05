"""
Fetch a web page and extract its text content.

Validates URL safety (SSRF), respects size/timeout/rate limits,
then delegates to parse_html or trafilatura for text extraction.
"""

import logging
import time
from urllib.parse import urlparse

import httpx

from core.context import VaultContext
from core.errors import IngestError
from core.schemas import FetchWebResult
from core.security import resolve_and_validate_host

logger = logging.getLogger(__name__)

_last_fetch_time: float = 0.0


def _enforce_rate_limit(min_interval: int) -> None:
    global _last_fetch_time
    now = time.monotonic()
    elapsed = now - _last_fetch_time
    if _last_fetch_time > 0 and elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_fetch_time = time.monotonic()


def _extract_content(html: str, url: str, tier: int) -> dict:
    """Extract text from HTML using the configured tier."""
    if tier >= 1:
        try:
            from trafilatura import extract
            text = extract(html, url=url, include_comments=False)
            if text:
                return {"text": text, "word_count": len(text.split())}
        except ImportError:
            logger.debug("trafilatura not installed, falling back to parse_html")

    from tools.text.parse_html import parse_html
    result = parse_html(html, base_url=url)
    return {
        "text": result.text,
        "title": result.title,
        "author": result.author,
        "date_published": result.date_published,
        "word_count": result.word_count,
    }


def fetch_web(url: str, ctx: VaultContext) -> FetchWebResult:
    """Fetch a web page and extract its text content."""
    from core.security import validate_web_url

    validate_web_url(url)

    web_cfg = ctx.settings.system.web
    _enforce_rate_limit(web_cfg.min_fetch_interval_seconds)

    max_bytes = web_cfg.max_response_mb * 1024 * 1024

    with httpx.Client(
        timeout=web_cfg.timeout_seconds,
        max_redirects=web_cfg.max_redirects,
        follow_redirects=True,
        headers={"User-Agent": "EgoVault/1.0"},
    ) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                raise ValueError(f"URL does not point to an HTML page (got {content_type})")

            # Stream and enforce size limit
            chunks = []
            total = 0
            for chunk in response.iter_bytes(chunk_size=8192):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Page too large (exceeds {web_cfg.max_response_mb} MB)")
                chunks.append(chunk)

            final_url = str(response.url)

    # Post-redirect DNS rebinding check
    final_hostname = urlparse(final_url).hostname
    original_hostname = urlparse(url).hostname
    if final_hostname and final_hostname != original_hostname:
        resolve_and_validate_host(final_hostname)

    html = b"".join(chunks).decode("utf-8", errors="replace")

    extracted = _extract_content(html, final_url, web_cfg.extraction_tier)

    if not extracted["text"] or extracted.get("word_count", 0) < 10:
        raise IngestError(
            "Could not extract meaningful text from this page",
            error_code="empty_web_content",
        )

    return FetchWebResult(
        text=extracted["text"],
        title=extracted.get("title"),
        author=extracted.get("author"),
        date_published=extracted.get("date_published"),
        word_count=extracted.get("word_count", len(extracted["text"].split())),
        final_url=final_url,
        content_type=content_type,
    )
