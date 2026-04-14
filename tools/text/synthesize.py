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


def _source_metadata(source: Source) -> dict:
    return {
        "title": source.title,
        "url": source.url,
        "author": source.author,
        "date_source": source.date_source,
        "source_type": source.source_type,
    }


def synthesize_large_source(
    source: Source,
    ctx: VaultContext,
    template: str,
    context_window: int,
) -> NoteContentInput:
    """Generate a NoteContentInput from a source that exceeds the context window.

    Caller is responsible for the threshold check. This function ALWAYS performs
    the multi-pass cascade — call it only when direct generation is not viable.
    """
    if ctx.generate is None:
        raise ValueError("No LLM provider configured. Cannot synthesize note content.")

    transcript = source.transcript or ""
    cfg = ctx.settings.system.note_generation
    threshold_ratio = ctx.settings.system.llm.direct_threshold_ratio

    strategy = _detect_strategy(transcript, context_window, threshold_ratio, cfg)

    if strategy == "direct":
        # Caller should have routed direct itself; defensive fall-through.
        return ctx.generate(
            transcript,
            _source_metadata(source),
            template,
        )

    if strategy == "toc":
        sections = _split_by_toc(transcript)
    else:
        sections = _split_by_tokens(transcript, cfg.merge_chunk_size)

    if len(sections) > cfg.max_sub_notes:
        raise ValueError(
            f"Source split into {len(sections)} sections, exceeds max_sub_notes={cfg.max_sub_notes}. "
            "Raise max_sub_notes in system.yaml or increase merge_chunk_size."
        )

    sub_notes: list[NoteContentInput] = []
    for section in sections:
        chapter_context = (
            f"You are synthesizing section {section.index + 1} of {section.total} "
            f"from the source titled '{source.title}'.\n"
            f"Section title: {section.title}\n"
            f"Focus only on this section. The final note will fuse all sections."
        )
        sub_note = ctx.generate(
            section.content,
            _source_metadata(source),
            template,
            system_prompt_extra=chapter_context,
        )
        sub_notes.append(sub_note)

    merge_input = _format_sub_notes_for_merge(sub_notes)
    return ctx.generate(
        merge_input,
        _source_metadata(source),
        "merge",
    )
