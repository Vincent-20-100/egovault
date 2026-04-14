"""Multi-pass synthesis for sources that exceed the LLM context window.

Cascade:
  1. If source <= threshold -> caller uses direct generation (this module not invoked).
  2. If TOC present (H1/H2 headings) -> split by chapter.
  3. Else -> split by token budget (map-reduce).
  4. Sub-generate one note per section via the user's template + chapter context.
  5. Merge all sub-notes into a final note via merge.yaml template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from core.config import NoteGenerationConfig
from core.context import VaultContext
from core.schemas import NoteContentInput, Source
from core.tokens import estimate_tokens

Strategy = Literal["direct", "toc", "map-reduce"]


@dataclass
class Section:
    title: str
    content: str
    index: int   # 0-based position in the section list
    total: int   # total number of sections


_H1 = re.compile(r"^# +(.+?)$", re.MULTILINE)
_H2 = re.compile(r"^## +(.+?)$", re.MULTILINE)


def _split_by_toc(markdown: str) -> list[Section]:
    """Split markdown by top-level headings. Tries H1 first, falls back to H2."""
    for pattern in (_H1, _H2):
        matches = list(pattern.finditer(markdown))
        if not matches:
            continue
        sections: list[Section] = []
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            sections.append(Section(
                title=match.group(1).strip(),
                content=markdown[start:end].strip(),
                index=i,
                total=len(matches),
            ))
        return sections
    return []


def _split_by_tokens(text: str, chunk_size: int) -> list[Section]:
    """Split text into roughly chunk_size-token sections by word count.

    Pure word-window split, no overlap (overlap belongs to RAG chunking, not
    synthesis where each sub-note must stand alone).
    """
    from core.tokens import WORDS_PER_TOKEN

    words = text.split()
    if not words:
        return [Section(title="Section 1 / 1", content=text, index=0, total=1)]

    words_per_chunk = max(1, int(chunk_size * WORDS_PER_TOKEN))
    chunks = [words[i:i + words_per_chunk] for i in range(0, len(words), words_per_chunk)]
    total = len(chunks)
    return [
        Section(
            title=f"Section {i + 1} / {total}",
            content=" ".join(chunk),
            index=i,
            total=total,
        )
        for i, chunk in enumerate(chunks)
    ]


def _detect_strategy(
    text: str,
    context_window: int,
    threshold_ratio: float,
    cfg: NoteGenerationConfig,
) -> Strategy:
    """Decide which synthesis path to take."""
    if cfg.strategy != "auto":
        # Explicit override wins, except web-search which is not handled here
        if cfg.strategy in ("direct", "toc", "map-reduce"):
            return cfg.strategy
        return "map-reduce"

    if estimate_tokens(text) <= context_window * threshold_ratio:
        return "direct"

    if _split_by_toc(text):
        return "toc"
    return "map-reduce"


def _format_sub_notes_for_merge(sub_notes: list[NoteContentInput]) -> str:
    """Render sub-notes as a single text block for the merge LLM call."""
    parts = []
    for i, note in enumerate(sub_notes, start=1):
        parts.append(
            f"=== SUB-NOTE {i} / {len(sub_notes)} ===\n"
            f"Title: {note.title}\n"
            f"Docstring: {note.docstring}\n"
            f"Tags: {', '.join(note.tags)}\n\n"
            f"{note.body}"
        )
    return "\n\n---\n\n".join(parts)
