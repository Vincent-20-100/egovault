"""
Plateau-aware topic segmentation using consecutive cosine TextTiling.

Partitions a sequential stream of N chunks into M cohesive candidate segments (1 Source -> N Notes).
Adheres to Zero-Hardcode (Rule G3) and Cognitive Memory Architecture.
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from core.schemas import ChunkResult, CandidateSegment

if TYPE_CHECKING:
    from core.config import Settings, SystemConfig


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    val = dot / (norm1 * norm2)
    return max(-1.0, min(1.0, val))


def _extract_label(chunks: list[ChunkResult]) -> str:
    """Extract a candidate label from the first Markdown heading or opening text."""
    for chunk in chunks:
        # Match markdown headers (# Title, ## Section)
        match = re.search(r"^(?:#{1,6})\s+(.+)$", chunk.content, re.MULTILINE)
        if match:
            return match.group(1).strip()

    # Fallback to first non-empty line or first words
    for chunk in chunks:
        lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
        if lines:
            words = lines[0].split()
            return " ".join(words[:8])

    return f"Section (chunks {chunks[0].position}-{chunks[-1].position})"


def _extract_locator(chunks: list[ChunkResult]) -> str:
    """Extract passage locator span across the chunk sequence."""
    if not chunks:
        return ""
    start_pos = chunks[0].position
    end_pos = chunks[-1].position
    return f"chunk {start_pos}-{end_pos}"


def _build_candidate(seq_idx: int, chunks: list[ChunkResult]) -> CandidateSegment:
    """Build a CandidateSegment object from a list of chunks."""
    return CandidateSegment(
        sequence_index=seq_idx,
        chunk_uids=[c.uid for c in chunks],
        label=_extract_label(chunks),
        locator=_extract_locator(chunks),
        chunks=chunks,
    )


def segment_chunks(
    chunks: list[ChunkResult],
    embeddings: list[list[float]],
    settings: Settings | SystemConfig,
) -> list[CandidateSegment]:
    """
    Segment sequential chunks into cohesive conceptual candidates using cosine TextTiling.

    Parameters:
      chunks: Sequential chunk results from DB.
      embeddings: Corresponding float embedding vectors.
      settings: 3-tier Settings or SystemConfig containing note_segmentation configuration.
    """
    if not chunks:
        return []

    sys_cfg = getattr(settings, "system", settings)
    seg_cfg = sys_cfg.note_segmentation

    min_chunks = seg_cfg.min_chunks_per_note
    max_notes = seg_cfg.max_notes_per_source
    max_chunks_cand = seg_cfg.max_chunks_per_candidate
    k_sens = seg_cfg.sensitivity_k
    s_min = seg_cfg.min_similarity_floor

    n = len(chunks)

    # Step 0: Bypass if input is too short for multiple valid segments
    if n < 2 * min_chunks or len(embeddings) < 2:
        return [_build_candidate(0, chunks)]

    # Step 1: Compute consecutive cosine similarities
    # s[i] is the similarity between chunks[i] and chunks[i+1] (length n-1)
    s = [_cosine_similarity(embeddings[i], embeddings[i + 1]) for i in range(n - 1)]

    # Step 2 & 3: Compute Valley Depth Scores with peak detection
    depths: list[float] = []
    for i in range(len(s)):
        # Left peak: max similarity seen to the left up to i (or boundary 0)
        max_left = max(s[: i + 1])
        # Right peak: max similarity seen to the right from i (or boundary n-2)
        max_right = max(s[i:])
        peak_avg = (max_left + max_right) / 2.0
        depths.append(peak_avg - s[i])

    # Step 4: Statistical thresholding
    mean_d = sum(depths) / len(depths)
    variance_d = sum((d - mean_d) ** 2 for d in depths) / len(depths)
    std_d = math.sqrt(variance_d)

    threshold_d = mean_d + k_sens * std_d if std_d > 1e-6 else mean_d + 0.05

    # Step 5: Identify raw boundary split points
    # A boundary at index i means splitting between chunk i and chunk i+1
    candidate_splits: list[int] = []
    i = 0
    while i < len(s):
        if depths[i] >= threshold_d or s[i] < s_min:
            # Check for plateau / contiguous qualifying valleys
            plateau_start = i
            while i + 1 < len(s) and (depths[i + 1] >= threshold_d or s[i + 1] < s_min):
                i += 1
            plateau_end = i
            # Choose deepest valley or plateau midpoint
            sub_depths = depths[plateau_start : plateau_end + 1]
            max_val = max(sub_depths)
            deepest_offsets = [
                idx for idx, val in enumerate(sub_depths) if abs(val - max_val) < 1e-6
            ]
            chosen_offset = deepest_offsets[len(deepest_offsets) // 2]
            candidate_splits.append(plateau_start + chosen_offset)
        i += 1

    # Form initial segment chunk slices
    raw_segments: list[list[ChunkResult]] = []
    last_idx = 0
    for split_point in candidate_splits:
        split_end = split_point + 1
        if split_end > last_idx:
            raw_segments.append(chunks[last_idx:split_end])
            last_idx = split_end
    if last_idx < n:
        raw_segments.append(chunks[last_idx:])

    if not raw_segments:
        raw_segments = [chunks]

    # Step 6: Budgeted Merging of sub-floor segments (< min_chunks)
    # Strict Precedence: Combined length MUST NEVER exceed max_chunks_cand (12)
    changed = True
    trapped_indices: set[int] = set()

    while changed:
        changed = False
        for idx in range(len(raw_segments)):
            if idx in trapped_indices:
                continue
            seg = raw_segments[idx]
            if len(seg) < min_chunks:
                can_merge_left = (
                    idx > 0 and (len(raw_segments[idx - 1]) + len(seg)) <= max_chunks_cand
                )
                can_merge_right = (
                    idx < len(raw_segments) - 1
                    and (len(raw_segments[idx + 1]) + len(seg)) <= max_chunks_cand
                )

                if can_merge_left and can_merge_right:
                    # Choose neighbor with higher boundary cosine similarity
                    split_left = raw_segments[idx - 1][-1].position
                    split_right = seg[-1].position
                    sim_left = s[split_left] if split_left < len(s) else 0.0
                    sim_right = s[split_right] if split_right < len(s) else 0.0
                    if sim_left >= sim_right:
                        raw_segments[idx - 1].extend(seg)
                        raw_segments.pop(idx)
                    else:
                        seg.extend(raw_segments[idx + 1])
                        raw_segments.pop(idx + 1)
                    changed = True
                    break
                elif can_merge_left:
                    raw_segments[idx - 1].extend(seg)
                    raw_segments.pop(idx)
                    changed = True
                    break
                elif can_merge_right:
                    seg.extend(raw_segments[idx + 1])
                    raw_segments.pop(idx + 1)
                    changed = True
                    break
                else:
                    # Trapped: cannot merge in either direction due to 12-chunk ceiling
                    trapped_indices.add(idx)

    # Step 7: Enforce max_notes_per_source limit if exceeded
    while len(raw_segments) > max_notes:
        best_merge_idx = -1
        highest_sim = -2.0
        for idx in range(len(raw_segments) - 1):
            if len(raw_segments[idx]) + len(raw_segments[idx + 1]) <= max_chunks_cand:
                split_p = raw_segments[idx][-1].position
                sim = s[split_p] if split_p < len(s) else 0.0
                if sim > highest_sim:
                    highest_sim = sim
                    best_merge_idx = idx

        if best_merge_idx != -1:
            raw_segments[best_merge_idx].extend(raw_segments[best_merge_idx + 1])
            raw_segments.pop(best_merge_idx + 1)
        else:
            break  # Cannot merge any further without violating chunk budget

    # Step 8: Build CandidateSegment instances
    return [
        _build_candidate(seq_idx, segment)
        for seq_idx, segment in enumerate(raw_segments)
    ]
