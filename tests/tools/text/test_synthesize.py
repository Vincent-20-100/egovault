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


from tools.text.synthesize import _split_by_tokens


def test_split_by_tokens_returns_single_section_when_under_budget():
    text = "short text"
    sections = _split_by_tokens(text, chunk_size=1000)
    assert len(sections) == 1
    assert sections[0].content == text


def test_split_by_tokens_creates_multiple_sections_above_budget():
    # 120 words, budget ~30 tokens -> words_per_chunk = 30*0.75 = 22 -> ~6 sections
    text = " ".join(["word"] * 120)
    sections = _split_by_tokens(text, chunk_size=30)
    assert len(sections) >= 3
    assert all(s.total == len(sections) for s in sections)
    assert [s.index for s in sections] == list(range(len(sections)))


def test_split_by_tokens_section_titles_are_indexed():
    text = " ".join(["word"] * 200)
    sections = _split_by_tokens(text, chunk_size=50)
    assert sections[0].title.startswith("Section 1")
    assert sections[-1].title.startswith(f"Section {len(sections)}")
