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


from core.config import NoteGenerationConfig


def test_detect_strategy_returns_direct_below_threshold():
    from tools.text.synthesize import _detect_strategy
    cfg = NoteGenerationConfig(strategy="auto")
    assert _detect_strategy("short text", context_window=100_000, threshold_ratio=0.6, cfg=cfg) == "direct"


def test_detect_strategy_returns_toc_when_headings_present():
    from tools.text.synthesize import _detect_strategy
    cfg = NoteGenerationConfig(strategy="auto")
    big = "# H1\n" + " ".join(["w"] * 200_000)
    assert _detect_strategy(big, context_window=10_000, threshold_ratio=0.6, cfg=cfg) == "toc"


def test_detect_strategy_returns_map_reduce_when_no_headings():
    from tools.text.synthesize import _detect_strategy
    cfg = NoteGenerationConfig(strategy="auto")
    big = " ".join(["w"] * 200_000)
    assert _detect_strategy(big, context_window=10_000, threshold_ratio=0.6, cfg=cfg) == "map-reduce"


def test_detect_strategy_honors_explicit_override():
    from tools.text.synthesize import _detect_strategy
    cfg = NoteGenerationConfig(strategy="map-reduce")
    big = "# H1\n" + " ".join(["w"] * 200_000)
    assert _detect_strategy(big, context_window=10_000, threshold_ratio=0.6, cfg=cfg) == "map-reduce"


def test_format_sub_notes_for_merge_produces_concatenated_text():
    from tools.text.synthesize import _format_sub_notes_for_merge
    from core.schemas import NoteContentInput
    notes = [
        NoteContentInput(
            title="Chapter 1: Origins",
            docstring="Short summary.",
            body="Body of chapter 1 with enough length.",
            tags=["origins"],
        ),
        NoteContentInput(
            title="Chapter 2: Growth",
            docstring="Another summary.",
            body="Body of chapter 2 with enough length.",
            tags=["growth", "expansion"],
        ),
    ]
    result = _format_sub_notes_for_merge(notes)
    assert "Chapter 1: Origins" in result
    assert "Chapter 2: Growth" in result
    assert "origins" in result
    assert "growth" in result
    assert "Body of chapter 1" in result


def test_synthesize_large_source_runs_toc_strategy_and_merges():
    from unittest.mock import MagicMock
    from tools.text.synthesize import synthesize_large_source
    from core.config import NoteGenerationConfig
    from core.schemas import NoteContentInput

    transcript = (
        "# Chapter 1\n" + " ".join(["w"] * 5000) + "\n"
        "# Chapter 2\n" + " ".join(["w"] * 5000) + "\n"
        "# Chapter 3\n" + " ".join(["w"] * 5000) + "\n"
    )
    source = MagicMock()
    source.transcript = transcript
    source.title = "Big Book"
    source.url = None
    source.author = "Anon"
    source.date_source = None
    source.source_type = "book"

    sub_call_count = {"n": 0}

    def fake_generate(content, metadata, template_name, system_prompt_extra=None):
        if template_name == "merge":
            return NoteContentInput(
                title="Big Book — synthesis",
                docstring="Final thesis here.",
                body="## Merged body\n\ncontent here long enough.",
                tags=["merged"],
            )
        sub_call_count["n"] += 1
        return NoteContentInput(
            title=f"Sub note {sub_call_count['n']}",
            docstring="sub doc text.",
            body="sub body content long enough.",
            tags=[f"sub-{sub_call_count['n']}"],
        )

    ctx = MagicMock()
    ctx.generate = fake_generate
    ctx.settings.system.note_generation = NoteGenerationConfig()
    ctx.settings.system.llm.direct_threshold_ratio = 0.6

    result = synthesize_large_source(
        source=source,
        ctx=ctx,
        template="standard",
        context_window=1000,  # forces multi-pass
    )

    assert result.title == "Big Book — synthesis"
    assert "merged" in result.tags
    assert sub_call_count["n"] == 3   # one per chapter


def test_synthesize_large_source_respects_max_sub_notes_cap():
    from unittest.mock import MagicMock
    from tools.text.synthesize import synthesize_large_source
    from core.config import NoteGenerationConfig
    from core.schemas import NoteContentInput

    # 100 chapters
    transcript = "".join(f"# Chapter {i}\n" + " ".join(["w"] * 100) + "\n" for i in range(100))
    source = MagicMock()
    source.transcript = transcript
    source.title = "Huge Book"
    source.url = None
    source.author = None
    source.date_source = None
    source.source_type = "book"

    def fake_generate(content, metadata, template_name, system_prompt_extra=None):
        return NoteContentInput(
            title="sub title ok",
            docstring="docstring ok.",
            body="body content long enough here.",
            tags=["t"],
        )

    ctx = MagicMock()
    ctx.generate = fake_generate
    ctx.settings.system.note_generation = NoteGenerationConfig(max_sub_notes=5)
    ctx.settings.system.llm.direct_threshold_ratio = 0.6

    with pytest.raises(ValueError, match="exceeds max_sub_notes"):
        synthesize_large_source(source=source, ctx=ctx, template="standard", context_window=1000)
