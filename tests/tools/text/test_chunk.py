import pytest
from core.config import SystemConfig, ChunkingConfig, LLMSystemConfig, TaxonomyConfig
from core.schemas import ChunkResult


def _config(size=10, overlap=2):
    return SystemConfig(
        chunking=ChunkingConfig(size=size, overlap=overlap),
        llm=LLMSystemConfig(max_retries=2, large_format_threshold_tokens=50000),
        taxonomy=TaxonomyConfig(
            note_types=["synthese"], source_types=["youtube"],
            generation_templates=["standard"]
        ),
    )


def test_chunk_text_basic():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(25)])
    chunks = chunk_text(text, _config(size=10, overlap=2))
    assert len(chunks) > 1
    assert all(isinstance(c, ChunkResult) for c in chunks)


def test_chunk_text_positions_sequential():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(30)])
    chunks = chunk_text(text, _config(size=10, overlap=2))
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_chunk_text_each_has_uid():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(20)])
    chunks = chunk_text(text, _config(size=10, overlap=2))
    uids = [c.uid for c in chunks]
    assert len(uids) == len(set(uids))  # all unique


def test_chunk_text_respects_size():
    from tools.text.chunk import chunk_text
    text = " ".join([f"word{i}" for i in range(50)])
    chunks = chunk_text(text, _config(size=10, overlap=0))
    for c in chunks[:-1]:  # last chunk may be smaller
        assert c.token_count == 10


def test_chunk_text_overlap_content():
    from tools.text.chunk import chunk_text
    # With overlap=3, last 3 words of chunk N appear at start of chunk N+1
    text = " ".join([f"w{i}" for i in range(20)])
    chunks = chunk_text(text, _config(size=8, overlap=3))
    if len(chunks) >= 2:
        end_of_first = chunks[0].content.split()[-3:]
        start_of_second = chunks[1].content.split()[:3]
        assert end_of_first == start_of_second


def test_chunk_text_short_input_single_chunk():
    from tools.text.chunk import chunk_text
    text = "hello world"
    chunks = chunk_text(text, _config(size=10, overlap=2))
    assert len(chunks) == 1
    assert chunks[0].position == 0


def test_chunk_text_empty_returns_empty():
    from tools.text.chunk import chunk_text
    chunks = chunk_text("", _config())
    assert chunks == []
