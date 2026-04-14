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
