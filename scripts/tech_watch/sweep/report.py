from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class SourceResult:
    source_name: str
    fetched: int
    new: int
    known: int
    failed: bool = False
    error: str = ""


@dataclass
class RunReport:
    run_date: str = field(default_factory=lambda: date.today().isoformat())
    mode: str = "normal"  # "normal" | "deep"
    top_items_per_theme: dict[str, list[dict]] = field(default_factory=dict)
    sources: list[SourceResult] = field(default_factory=list)
    promotion_candidates: list[str] = field(default_factory=list)  # card paths
    discarded_count: int = 0

    def to_json(self) -> str:
        data = asdict(self)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> RunReport:
        data = json.loads(text)
        sources = [SourceResult(**s) for s in data.pop("sources", [])]
        return cls(**data, sources=sources)
