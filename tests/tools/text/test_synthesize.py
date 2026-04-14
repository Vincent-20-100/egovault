import pytest
from tools.text.synthesize import _split_by_toc, Section


def test_split_by_toc_returns_empty_when_no_headings():
    sections = _split_by_toc("just some text\nwith no headings\n")
    assert sections == []


def test_split_by_toc_groups_content_under_h1():
    md = (
        "# Chapter 1\nfirst chapter content\nmore content\n"
        "# Chapter 2\nsecond chapter content\n"
    )
    sections = _split_by_toc(md)
    assert len(sections) == 2
    assert sections[0].title == "Chapter 1"
    assert "first chapter content" in sections[0].content
    assert sections[1].title == "Chapter 2"
    assert "second chapter content" in sections[1].content


def test_split_by_toc_falls_back_to_h2_when_no_h1():
    md = "## Section A\ncontent A\n## Section B\ncontent B\n"
    sections = _split_by_toc(md)
    assert len(sections) == 2
    assert sections[0].title == "Section A"


def test_split_by_toc_skips_preface_before_first_heading():
    md = "intro paragraph\n# Chapter 1\nbody\n"
    sections = _split_by_toc(md)
    assert len(sections) == 1
    assert sections[0].title == "Chapter 1"
