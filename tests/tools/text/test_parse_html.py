from core.schemas import ParseHtmlResult
from tools.text.parse_html import parse_html


def test_basic_paragraph_extraction():
    html = "<html><body><p>Hello world.</p><p>Second paragraph.</p></body></html>"
    result = parse_html(html)
    assert isinstance(result, ParseHtmlResult)
    assert "Hello world." in result.text
    assert "Second paragraph." in result.text
    assert result.word_count > 0


def test_script_and_style_removed():
    html = (
        "<html><body>"
        "<script>var x = 1;</script>"
        "<style>.foo { color: red; }</style>"
        "<p>Clean content.</p>"
        "</body></html>"
    )
    result = parse_html(html)
    assert "var x" not in result.text
    assert ".foo" not in result.text
    assert "Clean content." in result.text


def test_article_container_preferred():
    html = (
        "<html><body>"
        "<p>Outside article.</p>"
        "<article><p>Inside article.</p></article>"
        "</body></html>"
    )
    result = parse_html(html)
    # When <article> is found, content comes from within it
    assert "Inside article." in result.text


def test_metadata_extracted():
    html = (
        "<html><head>"
        "<title>My Title</title>"
        "<meta name='author' content='Jane Doe'>"
        "<meta property='article:published_time' content='2026-01-15'>"
        "</head><body><p>Body text.</p></body></html>"
    )
    result = parse_html(html)
    assert result.title == "My Title"
    assert result.author == "Jane Doe"
    assert result.date_published == "2026-01-15"


def test_og_title_takes_precedence_over_title_tag():
    html = (
        "<html><head>"
        "<title>Plain Title</title>"
        "<meta property='og:title' content='OG Title'>"
        "</head><body><p>Text.</p></body></html>"
    )
    result = parse_html(html)
    assert result.title == "OG Title"


def test_empty_html_returns_empty():
    result = parse_html("")
    assert result.text == ""
    assert result.word_count == 0


def test_only_noise_elements_returns_empty():
    html = (
        "<html><body>"
        "<nav><p>Nav link</p></nav>"
        "<footer><p>Footer text</p></footer>"
        "<header><p>Header text</p></header>"
        "</body></html>"
    )
    result = parse_html(html)
    assert result.text == ""
    assert result.word_count == 0


def test_word_count_matches_text():
    html = "<html><body><p>one two three four five</p></body></html>"
    result = parse_html(html)
    assert result.word_count == len(result.text.split())


def test_headings_extracted():
    html = "<html><body><h1>Main Heading</h1><h2>Sub Heading</h2><p>Body.</p></body></html>"
    result = parse_html(html)
    assert "Main Heading" in result.text
    assert "Sub Heading" in result.text


def test_no_metadata_fields_are_none():
    html = "<html><body><p>Just text.</p></body></html>"
    result = parse_html(html)
    assert result.title is None
    assert result.author is None
    assert result.date_published is None
