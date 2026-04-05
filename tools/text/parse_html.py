"""
Pure HTML article extractor.

Strips noise elements, extracts article content and metadata from an HTML string.
No network access — operates on already-fetched HTML.
"""

from bs4 import BeautifulSoup

from core.schemas import ParseHtmlResult

_NOISE_TAGS = {"script", "style", "nav", "footer", "header", "aside"}
_CONTENT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre"}


def parse_html(html: str, base_url: str | None = None) -> ParseHtmlResult:
    """Extract article content from an HTML string."""
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup)
    author = _extract_meta(soup, "author")
    date_published = (
        _extract_meta(soup, "article:published_time")
        or _extract_meta(soup, "datePublished")
    )

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    container = soup.find("article") or soup.find("main") or soup.find("body")

    if container is None:
        return ParseHtmlResult(text="", title=title, author=author,
                               date_published=date_published, word_count=0)

    blocks = [
        el.get_text(separator=" ", strip=True)
        for el in container.find_all(_CONTENT_TAGS)
        if el.get_text(strip=True)
    ]
    text = "\n\n".join(blocks).strip()
    word_count = len(text.split()) if text else 0

    return ParseHtmlResult(
        text=text,
        title=title,
        author=author,
        date_published=date_published,
        word_count=word_count,
    )


def _extract_title(soup: BeautifulSoup) -> str | None:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    tag = soup.find("title")
    if tag:
        return tag.get_text(strip=True) or None
    return None


def _extract_meta(soup: BeautifulSoup, name: str) -> str | None:
    tag = (
        soup.find("meta", attrs={"name": name})
        or soup.find("meta", attrs={"property": name})
        or soup.find("meta", attrs={"itemprop": name})
    )
    if tag and tag.get("content"):
        return tag["content"].strip() or None
    return None
