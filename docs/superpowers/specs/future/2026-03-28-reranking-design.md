# Spec: Reranking

**Date:** 2026-03-28
**Status:** Validated, ready to implement
**Dependencies:** architecture spec, API spec (`2026-03-27-api-design.md`), monitoring spec (`2026-03-28-monitoring-design.md`)

---

## Context and motivation

The current search returns the k closest results by cosine distance. Cosine distance measures geometric proximity in the vector space — it does not always capture fine semantic relevance. A reranker reads each `(query, candidate)` pair together and assigns a more precise relevance score.

Current pipeline:
```
query → embed → cosine distance → top k results
```

Pipeline with reranking:
```
query → embed → cosine distance → top k×N candidates
                                        ↓
                               reranker(query, candidate) → score
                                        ↓
                               top k reranked
```

---

## Architectural decisions and their rationale

### D1 — Local cross-encoder via `sentence-transformers`

**Decision:** model `cross-encoder/ms-marco-MiniLM-L-6-v2` (~80MB, CPU-compatible).

**Why not LLM-as-reranker:** slow, expensive, external. Incompatible with the project's 100% local philosophy.

**Why not hybrid BM25:** less precise than the cross-encoder. The cross-encoder sees query and document together — it understands nuance, not just word frequency.

**Complexity:** model downloaded once, ~50-100ms for 20 candidates on CPU. Acceptable.

---

### D2 — `infrastructure/reranker_provider.py`

**Decision:** the reranker lives in `infrastructure/`, not in `tools/` nor directly in `search.py`.

**Why not in `search.py`:** `search.py` grows and does two things. Single responsibility violation.

**Why not `tools/text/rerank.py`:** reranking is not an independent atomic tool — it only makes sense after a search. Exposing this as a tool would force workflows to know an implementation detail of search.

**Why `infrastructure/`:** same pattern as `embedding_provider.py`. The tool does not know which reranker is running, it just calls the interface. Swappable without touching the tools.

---

### D3 — Optional at two levels

**Decision:** globally configurable in `system.yaml` AND overridable per request in the API/MCP.

**Why:** some requests prioritize speed (auto-complete, preview), others precision (deep search, MCP context). The caller must be able to choose.

**Automatic fallback:** if `sentence-transformers` is not installed, `NoopReranker` is used silently. No error, no breaking change.

---

### D4 — Singleton for the model

**Decision:** the cross-encoder is loaded once into memory (singleton in `reranker_provider.py`), not on each call.

**Why:** cold start ~500ms on every request if the model is reloaded. Unacceptable in production. Same pattern as `embedding_provider.py`.

---

### D5 — Full backward compatibility

**Decision:** `rerank_score: float | None = None` in `SearchResult`. Parameter `rerank: bool | None = None` in `search()` (None = value from settings).

**Why:** all existing consumers (workflows, MCP, tests) continue to work without modification.

---

## Structure

No new files in `tools/` or `workflows/`. Two files modified, one created:

```
infrastructure/
└── reranker_provider.py     ← NEW

tools/vault/
└── search.py                ← MODIFIED (rerank parameter + provider call)

core/
└── schemas.py               ← MODIFIED (rerank_score in SearchResult)
```

---

## `infrastructure/reranker_provider.py`

```python
"""
Reranker provider — local cross-encoder via sentence-transformers.

Interface: RerankProvider (Protocol)
Implementations: CrossEncoderReranker, NoopReranker
Singleton: get_reranker(settings) — model loaded once into memory
"""

from typing import Protocol
from core.schemas import SearchResult
from core.config import Settings

_reranker_instance: "RerankProvider | None" = None


class RerankProvider(Protocol):
    def rerank(self, query: str, candidates: list[SearchResult]) -> list[SearchResult]: ...


class NoopReranker:
    """Pass-through — returns candidates unchanged."""
    def rerank(self, query: str, candidates: list[SearchResult]) -> list[SearchResult]:
        return candidates


class CrossEncoderReranker:
    """Local cross-encoder via sentence-transformers."""
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: list[SearchResult]) -> list[SearchResult]:
        if not candidates:
            return candidates
        pairs = [(query, c.content) for c in candidates]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        for result, score in ranked:
            result.rerank_score = score
        return [r for r, _ in ranked]


def get_reranker(settings: Settings) -> RerankProvider:
    """Returns the reranker singleton. Loads the model only once."""
    global _reranker_instance
    if _reranker_instance is not None:
        return _reranker_instance
    if not settings.reranking.enabled:
        _reranker_instance = NoopReranker()
        return _reranker_instance
    try:
        _reranker_instance = CrossEncoderReranker(settings.reranking.model)
    except ImportError:
        # sentence-transformers not installed → silent fallback
        _reranker_instance = NoopReranker()
    return _reranker_instance
```

---

## `tools/vault/search.py` — modifications

```python
@loggable("search")
def search(
    query: str,
    settings: Settings,
    filters: SearchFilters | None = None,
    mode: str = "chunks",
    limit: int = 5,
    rerank: bool | None = None,   # None = value from settings.reranking.enabled
) -> list[SearchResult]:
    from infrastructure.reranker_provider import get_reranker

    use_rerank = settings.reranking.enabled if rerank is None else rerank
    fetch_limit = limit * settings.reranking.rerank_factor if use_rerank else limit

    query_embedding = embed_text(query, settings)

    if mode == "notes":
        candidates = search_notes(settings.db_path, query_embedding, filters, fetch_limit)
        if use_rerank and settings.reranking.apply_to_notes:
            candidates = get_reranker(settings).rerank(query, candidates)
    else:
        candidates = search_chunks(settings.db_path, query_embedding, filters, fetch_limit)
        if use_rerank and settings.reranking.apply_to_chunks:
            candidates = get_reranker(settings).rerank(query, candidates)

    return candidates[:limit]
```

---

## `core/schemas.py` — `SearchResult` modification

```python
class SearchResult(BaseModel):
    note_uid: str | None = None
    source_uid: str | None = None
    chunk_uid: str | None = None
    content: str
    title: str
    distance: float
    rerank_score: float | None = None   # NEW — None if reranking disabled
```

---

## Config

**`config/system.yaml`:**
```yaml
search:
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_factor: 4          # candidates fetched = limit × rerank_factor
    apply_to_chunks: true
    apply_to_notes: true
```

**`config/install.yaml`:**
```yaml
reranker:
  model_cache_dir: "~/.cache/egovault/reranker"
```

---

## `pyproject.toml` — optional dependency

```toml
[project.optional-dependencies]
reranker = ["sentence-transformers>=3.0"]
```

Installation with reranker: `uv sync --extra reranker`
Installation without: `uv sync` (NoopReranker active automatically)

`init_user_dir.py` displays a warning if `reranking.enabled: true` and `sentence-transformers` is absent.

---

## API — additional parameter

```
POST /api/search
  body: {
    query: str,
    mode: "chunks" | "notes",
    limit: int,
    rerank: bool          ← NEW, optional (default: settings.reranking.enabled)
  }
  → list[SearchResult]   (with rerank_score if reranking active)
```

---

## MCP tool — additional parameter

```
tool: search_vault
  args: {
    query: str,
    mode: "chunks" | "notes",
    limit: int,
    rerank: bool?         ← NEW, optional
  }
  → results with rerank_score if active
```

The LLM can choose `rerank=false` for a fast request or `rerank=true` for a deep search.

---

## Compatibility with other specs

- **Monitoring**: `@loggable` captures `rerank` in `input_json` automatically. `token_count = NULL` (local model, no tokens). Transparent.
- **Evaluation**: the golden dataset can measure `precision@k` with and without reranking — quantifies the gain. Complementary.
- **Frontend**: `rerank` toggle = natural UI element (speed vs precision). Specified in the upcoming frontend spec.
- **Existing**: zero breaking change — `rerank=None` by default, `rerank_score=None` by default.

---

## What is NOT in this spec

- Hybrid BM25 → not retained (cross-encoder more precise, similar complexity)
- LLM-as-reranker → outside 100% local philosophy
- Cross-mode reranking (chunks + notes together) → out of scope
- Fine-tuning the cross-encoder on the user vault → future extension
