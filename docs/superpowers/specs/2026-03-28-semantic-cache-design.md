# Spec: Semantic Cache

**Date:** 2026-03-28
**Status:** Validated, ready to implement
**Dependencies:** architecture spec, API spec (`2026-03-27-api-design.md`), monitoring spec (`2026-03-28-monitoring-design.md`), reranking spec (`2026-03-28-reranking-design.md`)

---

## Context and motivation

Every search request embeds the query and performs a vector search — even if the same question (or a very similar one) has already been asked. For a personal knowledge tool, repetitive questions are frequent (LLM sessions, thematic explorations). The semantic cache avoids a full RAG on already-processed queries.

Current pipeline:
```
query → embed → vector search → rerank → results
```

Pipeline with cache:
```
query → embed → cache lookup → hit  → direct results (< 5ms)
                             → miss → vector search → rerank → store → results
```

---

## Cross-cutting fix included: configurable `embedding.dims`

**Identified problem:** `768` is hardcoded in `infrastructure/db.py` (L.74, L.79, L.115) and ~20 test files. All vec tables (`chunks_vec`, `notes_vec`, `semantic_cache_vec`) must use the same dimension.

**Fix:** `embedding.dims` defined once in `config/system.yaml`, read everywhere.

```yaml
# config/system.yaml
embedding:
  dims: 768        # single source of truth for all vec tables
  model: "nomic-embed-text"
```

```python
# infrastructure/db.py — schema generated dynamically
def _build_schema_sql(dims: int) -> str:
    return f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
        chunk_uid TEXT PRIMARY KEY,
        embedding FLOAT[{dims}]
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS notes_vec USING vec0(
        note_uid TEXT PRIMARY KEY,
        embedding FLOAT[{dims}]
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS semantic_cache_vec USING vec0(
        cache_uid TEXT PRIMARY KEY,
        embedding FLOAT[{dims}]
    );
    """
```

**Tests:** `EMBEDDING_DIMS` constant in `tests/conftest.py` replaces all `[0.1] * 768`.

---

## Architectural decisions and their rationale

### D1 — Cache in `.system.db`

**Decision:** the cache lives in `.system.db`, not in a separate file nor in memory.

**Why not memory:** lost on every MCP server restart — useless for a long-term knowledge tool.

**Why not a separate file:** `.system.db` already centralizes `tool_logs`, `workflow_runs`, `benchmark_runs`. The cache is operational data — same bucket, same backup.

**Benefit:** naturally shared between MCP and API. Queryable via the monitoring API.

---

### D2 — Double lookup: exact then semantic

**Decision:** MD5 hash first (O(1), zero embedding call), then sqlite-vec if miss.

**Why:** word-for-word identical queries are frequent in LLM sessions. The hash avoids a useless vector search for exact hits. The semantic lookup captures paraphrases.

---

### D3 — TTL + event-based invalidation

**Decision:** configurable TTL (default 7 days) + automatic purge on note/chunk modification.

**Why TTL alone is insufficient:** a note modified today can be returned by the cache until expiration — stale results.

**Why events alone are insufficient:** orphaned entries (deleted chunks, deleted sources) do not always trigger an explicit event. TTL is the safety net.

---

### D4 — `infrastructure/semantic_cache.py`

**Decision:** dedicated component in `infrastructure/`, called by `search.py` internally.

**Why not in `mcp/server.py`:** the API would not benefit from the cache. Duplicates the logic.

**Why not in `search.py`:** search.py is an orchestrator, not an implementer. The cache is a separate responsibility.

**Benefit:** same pattern as `embedding_provider.py` and `reranker_provider.py`. Independently testable.

---

### D5 — `use_cache` overridable per request

**Decision:** `use_cache: bool` parameter in the API and MCP, overriding the config default.

**Why:** some requests must force a fresh RAG (after a massive ingest, for debugging). The LLM can explicitly choose `use_cache=false`.

---

## `.system.db` schema

```sql
CREATE TABLE semantic_cache (
    cache_uid     TEXT PRIMARY KEY,
    query_text    TEXT NOT NULL,
    query_hash    TEXT NOT NULL,        -- MD5 hex for O(1) exact lookup
    mode          TEXT NOT NULL,        -- "chunks" | "notes"
    filters_json  TEXT,                 -- SearchFilters JSON (NULL if none)
    result_ids    TEXT NOT NULL,        -- JSON list of chunk_uid or note_uid
    rerank        INTEGER NOT NULL,     -- 0 | 1 — cache specific to rerank mode
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,        -- created_at + TTL
    hit_count     INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE semantic_cache_vec USING vec0(
    cache_uid TEXT PRIMARY KEY,
    embedding FLOAT[{dims}]             -- dims from system.yaml:embedding.dims
);

CREATE INDEX idx_cache_hash ON semantic_cache(query_hash);
CREATE INDEX idx_cache_expires ON semantic_cache(expires_at);
CREATE INDEX idx_cache_mode ON semantic_cache(mode);
```

---

## `infrastructure/semantic_cache.py`

```python
"""
Semantic cache — semantic lookup before each RAG.

Double lookup: exact (MD5 hash) then semantic (sqlite-vec).
Invalidation: TTL + event (note/chunk modified).
"""

import hashlib
import json
from pathlib import Path
from core.schemas import SearchResult, SearchFilters
from core.config import Settings


class SemanticCache:
    def __init__(self, system_db_path: Path, settings: Settings): ...

    def lookup(
        self,
        query: str,
        query_embedding: list[float],
        mode: str,
        filters: SearchFilters | None,
        rerank: bool,
    ) -> list[SearchResult] | None:
        """
        1. Exact MD5 hash → returns if hit and not expired
        2. sqlite-vec similarity → returns if distance < threshold and not expired
        3. None if miss
        Updates hit_count on hit.
        """

    def store(
        self,
        query: str,
        query_embedding: list[float],
        mode: str,
        filters: SearchFilters | None,
        rerank: bool,
        results: list[SearchResult],
    ) -> None:
        """Stores query + embedding + result_ids. Purges if max_entries exceeded (FIFO)."""

    def invalidate(self, result_ids: list[str]) -> int:
        """
        Removes entries whose result_ids contain at least one of the provided IDs.
        Returns the number of purged entries.
        """

    def purge_expired(self) -> int:
        """Removes expired entries. Returns the number purged."""

    def stats(self) -> dict:
        """{ total_entries, hit_rate, avg_ttl_remaining_days, expired_count }"""

    @staticmethod
    def _hash_query(query: str, mode: str, filters_json: str, rerank: bool) -> str:
        key = f"{query}|{mode}|{filters_json}|{rerank}"
        return hashlib.md5(key.encode()).hexdigest()
```

---

## `tools/vault/search.py` — complete pipeline

```python
@loggable("search")
def search(
    query: str,
    settings: Settings,
    filters: SearchFilters | None = None,
    mode: str = "chunks",
    limit: int = 5,
    rerank: bool | None = None,
    use_cache: bool | None = None,      # None = settings.semantic_cache.enabled
) -> list[SearchResult]:
    from infrastructure.reranker_provider import get_reranker
    from infrastructure.semantic_cache import SemanticCache

    use_rerank = settings.reranking.enabled if rerank is None else rerank
    cache_enabled = settings.semantic_cache.enabled if use_cache is None else use_cache
    cache = SemanticCache(settings.system_db_path, settings)

    # 1. Embed (necessary even for the semantic lookup)
    query_embedding = embed_text(query, settings)

    # 2. Cache lookup
    if cache_enabled:
        cached = cache.lookup(query, query_embedding, mode, filters, use_rerank)
        if cached is not None:
            return cached[:limit]

    # 3. Vector search
    fetch_limit = limit * settings.reranking.rerank_factor if use_rerank else limit
    if mode == "notes":
        candidates = search_notes(settings.db_path, query_embedding, filters, fetch_limit)
    else:
        candidates = search_chunks(settings.db_path, query_embedding, filters, fetch_limit)

    # 4. Reranking
    if use_rerank:
        candidates = get_reranker(settings).rerank(query, candidates)

    results = candidates[:limit]

    # 5. Store in cache
    if cache_enabled:
        cache.store(query, query_embedding, mode, filters, use_rerank, results)

    return results
```

---

## Config

**`config/system.yaml`:**
```yaml
embedding:
  dims: 768
  model: "nomic-embed-text"

search:
  semantic_cache:
    enabled: true
    similarity_threshold: 0.05   # max cosine distance for a semantic hit
    ttl_days: 7
    max_entries: 1000             # FIFO purge (oldest first) if exceeded
```

---

## API

```
POST /api/search
  body: { query, mode, limit, rerank?, use_cache: bool }
  → use_cache=false: bypasses the cache, forces fresh RAG
  → default: settings.semantic_cache.enabled

GET /api/monitoring/cache
  → { total_entries, hit_rate, avg_ttl_remaining_days, expired_count }

DELETE /api/monitoring/cache
  → manual full purge (debug / reset)
  → returns { purged_count }
```

---

## MCP tools

```
tool: search_vault(query, mode, limit, rerank?, use_cache?)
  → use_cache parameter added (optional)

tool: clear_cache()
  → calls DELETE /api/monitoring/cache
  → useful after a massive ingest to force a fresh RAG
```

---

## Invalidation — 3 triggers

**1. Automatic TTL**
`purge_expired()` called at MCP server and FastAPI startup (`lifespan`).

**2. Note/chunk modification**
`cache.invalidate(result_ids)` called in:
- `tools/vault/update_note.py` — after a note update
- `infrastructure/db.py:delete_chunks()` — after chunk deletion (e.g. re-ingest)

**3. Manual**
`DELETE /api/monitoring/cache` or MCP tool `clear_cache()`.

---

## Compatibility with other specs

- **Monitoring**: `@loggable` captures `use_cache` in `input_json`. Cache hit = very short `duration_ms` → visible in stats. Transparent.
- **Reranking**: the cache is specific to the `(query, rerank)` pair — a hit with `rerank=true` does not serve a `rerank=false` request. Consistent.
- **Benchmark**: benchmark tests call `search()` with `use_cache=false` — the golden dataset always tests real RAG, never the cache.
- **Existing**: `use_cache=None` by default — all existing callers continue to work without modification.

---

## What is NOT in this spec

- Distributed cache (Redis, Memcached) → outside 100% local philosophy
- Cache on LLM results (generated responses) → out of scope
- Cache pre-warming → future extension
- Advanced query pattern analytics → out of scope
