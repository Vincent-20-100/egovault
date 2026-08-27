import math
from core.schemas import ChunkResult
from tools.text.segment import segment_chunks


def _unit_vector(dim: int, index: int) -> list[float]:
    """Create a unit basis vector with 1.0 at given index."""
    v = [0.0] * dim
    v[index] = 1.0
    return v


def _blend_vector(v1: list[float], v2: list[float], weight: float) -> list[float]:
    """Blend two vectors and normalize to unit length."""
    raw = [w1 * (1 - weight) + w2 * weight for w1, w2 in zip(v1, v2)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


def test_segment_chunks_empty():
    assert segment_chunks([], [], None) == []


def test_segment_chunks_short_input_returns_single_segment(tmp_settings):
    """Sources with < 2 * min_chunks_per_note bypass segmentation."""
    chunks = [
        ChunkResult(uid=f"c{i}", position=i, content=f"Sentence {i}", token_count=10)
        for i in range(4)
    ]
    embeddings = [_unit_vector(64, 0) for _ in range(4)]

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    assert len(segments) == 1
    assert segments[0].sequence_index == 0
    assert segments[0].chunk_uids == ["c0", "c1", "c2", "c3"]


def test_segment_chunks_uniform_content_returns_single_segment(tmp_settings):
    """Uniform embedding trajectory has no drops and produces 1 segment."""
    chunks = [
        ChunkResult(uid=f"c{i}", position=i, content=f"Chunk {i}", token_count=10)
        for i in range(8)
    ]
    embeddings = [_unit_vector(64, 0) for _ in range(8)]

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    assert len(segments) == 1
    assert len(segments[0].chunk_uids) == 8


def test_segment_chunks_detects_topic_shift(tmp_settings):
    """Clear shift between two topics (chunks 0-3 in cluster A, chunks 4-7 in cluster B)."""
    dim = 64
    vec_a = _unit_vector(dim, 0)
    vec_b = _unit_vector(dim, 1)

    chunks = [
        ChunkResult(uid=f"c{i}", position=i, content=f"Topic A chunk {i}" if i < 4 else f"Topic B chunk {i}", token_count=10)
        for i in range(8)
    ]
    embeddings = [vec_a] * 4 + [vec_b] * 4

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    assert len(segments) == 2
    assert segments[0].chunk_uids == ["c0", "c1", "c2", "c3"]
    assert segments[1].chunk_uids == ["c4", "c5", "c6", "c7"]
    assert segments[0].sequence_index == 0
    assert segments[1].sequence_index == 1


def test_segment_chunks_respects_hard_ceiling(tmp_settings):
    """Segments never merge beyond max_chunks_per_candidate (12)."""
    dim = 64
    # Create 14 chunks: 11 topic A, 3 topic B
    chunks = [
        ChunkResult(uid=f"c{i}", position=i, content=f"Content {i}", token_count=10)
        for i in range(14)
    ]
    embeddings = [_unit_vector(dim, 0)] * 11 + [_unit_vector(dim, 1)] * 3

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    for seg in segments:
        assert len(seg.chunk_uids) <= tmp_settings.system.note_segmentation.max_chunks_per_candidate


def test_segment_chunks_extracts_labels_and_locators(tmp_settings):
    """Label is extracted from first heading in segment or fallback."""
    dim = 64
    chunks = [
        ChunkResult(uid="c0", position=0, content="# Introduction to System\nOverview here.", token_count=10),
        ChunkResult(uid="c1", position=1, content="More details 1.", token_count=10),
        ChunkResult(uid="c2", position=2, content="More details 2.", token_count=10),
        ChunkResult(uid="c3", position=3, content="More details 3.", token_count=10),
        ChunkResult(uid="c4", position=4, content="## Advanced Architecture\nDeep dive.", token_count=10),
        ChunkResult(uid="c5", position=5, content="Architecture component 1.", token_count=10),
        ChunkResult(uid="c6", position=6, content="Architecture component 2.", token_count=10),
        ChunkResult(uid="c7", position=7, content="Architecture component 3.", token_count=10),
    ]
    embeddings = [_unit_vector(dim, 0)] * 4 + [_unit_vector(dim, 1)] * 4

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    assert len(segments) == 2
    assert "Introduction to System" in segments[0].label
    assert "Advanced Architecture" in segments[1].label


def test_segment_chunks_plateau_midpoint(tmp_settings):
    """Contiguous cosine valley plateau selects the central split point."""
    dim = 64
    vec_a = _unit_vector(dim, 0)
    vec_b = _unit_vector(dim, 1)

    # 10 chunks: 3 topic A, 4 intermediate transitioning, 3 topic B
    chunks = [
        ChunkResult(uid=f"c{i}", position=i, content=f"Chunk {i}", token_count=10)
        for i in range(10)
    ]
    embeddings = (
        [vec_a] * 3
        + [_blend_vector(vec_a, vec_b, 0.5)] * 4
        + [vec_b] * 3
    )

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    assert len(segments) >= 2
    # Verify all chunks are accounted for in sequential order
    all_uids = [uid for seg in segments for uid in seg.chunk_uids]
    assert all_uids == [f"c{i}" for i in range(10)]


def test_segment_chunks_min_similarity_floor_trigger(tmp_settings):
    """Absolute similarity floor S_min forces a boundary split."""
    dim = 64
    vec_a = _unit_vector(dim, 0)
    vec_orthogonal = _unit_vector(dim, 1)

    chunks = [
        ChunkResult(uid=f"c{i}", position=i, content=f"Chunk {i}", token_count=10)
        for i in range(8)
    ]
    # Orthogonal vectors have cosine similarity = 0.0, well below S_min (0.35)
    embeddings = [vec_a] * 4 + [vec_orthogonal] * 4

    segments = segment_chunks(chunks, embeddings, tmp_settings)
    assert len(segments) == 2
    assert len(segments[0].chunk_uids) == 4
    assert len(segments[1].chunk_uids) == 4
