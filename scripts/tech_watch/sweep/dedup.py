from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse


def canonicalize(url: str, source_name: str) -> str:
    """Return a canonical URL for dedup purposes.

    Rules by source:
    - github: strip /tree/*, /blob/*, trailing slashes, normalize to https
    - hf: keep only https://huggingface.co/<owner>/<model>
    - reddit: keep the link as-is (feed provides canonical link)
    - rss: keep the link as-is
    - web: strip ?utm_* and other tracking parameters
    """
    url = url.strip()
    if not url:
        return url

    parsed = urlparse(url)

    if source_name == "github":
        # Strip /tree/<ref>/... and /blob/<ref>/... path segments
        path = re.sub(r"/(tree|blob)/[^/]+.*$", "", parsed.path)
        path = path.rstrip("/")
        return urlunparse(("https", "github.com", path, "", "", ""))

    if source_name == "hf":
        # Canonical: https://huggingface.co/<owner>/<model>
        # Strip /resolve/*, /blob/*, /discussions/*, etc.
        parts = parsed.path.strip("/").split("/")
        canonical_path = "/" + "/".join(parts[:2]) if len(parts) >= 2 else parsed.path
        return urlunparse(("https", "huggingface.co", canonical_path, "", "", ""))

    if source_name == "web":
        # Strip UTM and other common tracking params
        tracking_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "ref",
            "source",
            "fbclid",
            "gclid",
        }
        query = parse_qs(parsed.query, keep_blank_values=True)
        clean_query = {k: v for k, v in query.items() if k not in tracking_params}
        # Rebuild query string preserving order
        clean_qs = "&".join(f"{k}={v[0]}" for k, v in sorted(clean_query.items()))
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_qs,
                "",
            )
        )

    # reddit, rss — keep as-is
    return url


def is_known(canonical_url: str, index_path: Path) -> bool:
    """Check if a canonical URL is already tracked in INDEX.md.

    Reads the INDEX.md file and looks for the URL in source_url fields.
    Returns False if the index file doesn't exist yet.
    """
    if not index_path.exists():
        return False

    content = index_path.read_text(encoding="utf-8")
    return canonical_url in content
