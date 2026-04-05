# Spec: Benchmark — Golden Dataset & Benchmark Framework

**Date:** 2026-03-28
**Status:** Validated, ready to implement
**Note:** spec originally written under the name "evaluation" — renamed "benchmark" during the 2026-03-28 consolidation.
**Dependencies:** API spec (`2026-03-27-api-design.md`), architecture spec

---

## Context and motivation

Current tests verify that search *works* (returns results) but not that it returns the *right* results. There is no mechanism to measure RAG quality, detect a relevance regression, or evaluate the quality of generated notes.

This spec introduces a modular evaluation framework that:
- measures search quality (precision@k, recall@k, MRR) against a static golden dataset
- integrates naturally into pytest (CI) and the API (on-demand)
- plans for LLM-as-judge and human rating extensions without implementing them

---

## Architectural decisions and their rationale

### D1 — Hybrid approach: pytest + runner

**Decision:** a central `runner.py` contains all the evaluation logic. Pytest calls it for CI (without DB). The API calls it for on-demand runs (results persisted in `.system.db`).

**Why not pytest-only:** cannot be exposed via API/MCP, results not persisted, LLM-as-judge extension is difficult.

**Why not runner-only:** breaks the project's existing pytest pattern, CI becomes dependent on the API.

**Benefit:** a single logic location, two entry points. Consistent with the existing hexagonal architecture.

---

### D2 — Golden dataset as versioned static JSON files

**Decision:** golden test cases live in `benchmark/datasets/golden/*.json`, versioned in the repo.

**Why not in DB:** a golden dataset that can drift in prod is no longer a golden dataset. Test cases are code — they must be reviewable in PRs and identical across all environments.

**Planned extension (not implemented):** a `benchmark_golden` table in `.system.db` + an `export_golden.py` script will eventually allow promoting a perfect response from the UI to the golden set. Users will thus be able to steer the system to their liking. This feature is documented (DB schema reserved, endpoints stubbed) but YAGNI applies: no implementation now.

---

### D3 — YAGNI on rating and promote

**Decision:** the `JudgeVerdict`, `LLMJudge`, `HumanJudge` interfaces are defined. The `/api/benchmark/rate` and `/api/benchmark/promote` endpoints are documented. DB tables are reserved in the schema. Nothing is implemented.

**Why:** rating touches DB, API, MCP, and frontend simultaneously. It is a full feature in its own right, not a minor addition. Implementing it now would be premature.

**Benefit:** when we want to add it, the spec will say exactly where to plug in. No architectural debt.

---

### D4 — A single shared rating contract for LLM + human

**Decision:** `JudgeVerdict` is the unique contract. The LLM calls it via MCP tool, the human via `POST /api/benchmark/rate` from the frontend.

**Why:** a single endpoint, two consumers. Consistent with the project's "determinism" philosophy — the system does not distinguish the source of the rating at the contract level.

---

## Structure

```
benchmark/
├── runner.py                        ← central orchestrator
├── components/
│   ├── search_benchmark.py               ← search chunks + notes (implemented)
│   ├── chunk_benchmark.py                ← size, overlap, consistency (implemented)
│   ├── note_benchmark.py                 ← LLM-as-judge stub (empty interface)
│   └── pipeline_benchmark.py             ← end-to-end stub (empty interface)
├── metrics.py                       ← precision@k, recall@k, MRR
├── export_golden.py                 ← future extension: DB → JSON
└── datasets/
    └── golden/
        ├── search_chunks.json       ← search test cases mode=chunks
        ├── search_notes.json        ← search test cases mode=notes
        └── chunk_consistency.json   ← chunking test cases

tests/benchmark/
├── __init__.py
├── test_search_benchmark.py              ← pytest → runner (without DB)
└── test_chunk_benchmark.py
```

---

## Golden dataset — JSON format

### `search_chunks.json`
```json
[
  {
    "query": "antifragilité et robustesse",
    "tags_filter": ["epistemologie"],
    "expected_chunk_uids": ["c-uuid-1", "c-uuid-2"],
    "k": 5
  }
]
```

### `search_notes.json`
```json
[
  {
    "query": "distinction robustesse antifragilité",
    "expected_note_uids": ["n-uuid-1"],
    "k": 3
  }
]
```

### `chunk_consistency.json`
```json
[
  {
    "source_uid": "s-uuid-1",
    "expected_chunk_count": 12,
    "max_tokens_per_chunk": 800
  }
]
```

The `*_uids` point to test fixtures in `conftest.py` (same pattern as existing tests).

---

## Metrics (`metrics.py`)

```python
def precision_at_k(expected: list[str], retrieved: list[str], k: int) -> float:
    """Proportion of expected results in the top k."""

def recall_at_k(expected: list[str], retrieved: list[str], k: int) -> float:
    """Proportion of expected results found in the top k."""

def mrr(expected: list[str], retrieved: list[str]) -> float:
    """Mean Reciprocal Rank — average inverse rank of the first correct result."""
```

Configurable thresholds in `config/system.yaml`:
```yaml
eval:
  search:
    min_precision_at_5: 0.8
    min_recall_at_5: 0.7
    min_mrr: 0.6
  chunk:
    max_tokens_per_chunk: 800
```

---

## Pydantic schemas

```python
class BenchmarkResult(BaseModel):
    component: str                          # "search" | "chunk" | "note" | "pipeline"
    passed: bool
    precision_at_k: float | None = None
    recall_at_k: float | None = None
    mrr: float | None = None
    failures: list[str] = []               # descriptions of failed cases

# Future extension — not implemented
class JudgeVerdict(BaseModel):
    rating: int                             # 1-5
    judge_type: Literal["llm", "human"]
    comment: str | None = None
    result_ids: list[str]
```

---

## Runner (`benchmark/runner.py`)

```python
def run(component: str, db_path: str | None = None) -> BenchmarkResult:
    """
    component : "search" | "chunk" | "all"
    db_path   : if provided, persists the result in benchmark_runs (.system.db)
                if None (CI / pytest), returns the result without persisting
    """
```

Called by pytest without `db_path`. Called by the API with `db_path`.

---

## Stubs (empty interfaces, not implemented)

```python
class NoteBenchmarker(Protocol):
    def run(self, note: Note, source: Source) -> BenchmarkResult: ...

class JudgeRunner(Protocol):
    def run(self, query: str, results: list[SearchResult]) -> JudgeVerdict: ...

# Future implementations:
class LLMJudge:  ...   # calls LLM via MCP tool
class HumanJudge: ...  # receives rating via POST /api/benchmark/rate
```

---

## API

### Implemented endpoints

```
POST /api/benchmark/run
  body : { "component": "search" | "chunk" | "all" }
  → launches runner.py with db_path → persists in benchmark_runs
  → returns BenchmarkResult

GET  /api/benchmark/results
  → lists runs from benchmark_runs (.system.db)

GET  /api/benchmark/results/{run_id}
  → full detail of a run
```

### Stubbed endpoints (documented, not implemented)

```
POST /api/benchmark/rate
  body : { run_id, rating: int, judge_type: "human"|"llm", comment? }
  → stores in benchmark_ratings (.system.db)

POST /api/benchmark/promote
  body : { run_id, query, result_ids }
  → stores in benchmark_golden (.system.db)
  → triggers export_golden.py (regenerates JSON files)
```

---

## MCP tool

```
tool: run_benchmark
  args: { component: "search" | "chunk" | "all" }
  → calls POST /api/benchmark/run
  → returns a human-readable summary of metrics
```

Future extension: `rate_benchmark` tool → calls `POST /api/benchmark/rate` with `judge_type: "llm"`.

---

## `.system.db` schema

### Implemented table

```sql
CREATE TABLE benchmark_runs (
    run_id    TEXT PRIMARY KEY,
    component TEXT NOT NULL,
    metrics   TEXT NOT NULL,   -- serialized JSON of BenchmarkResult
    passed    INTEGER NOT NULL,
    timestamp TEXT NOT NULL
);
```

### Reserved tables (future extension, not created now)

```sql
-- benchmark_ratings: human or LLM feedback on a run
CREATE TABLE benchmark_ratings (
    rating_id  TEXT PRIMARY KEY,
    run_id     TEXT NOT NULL,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    judge_type TEXT NOT NULL CHECK (judge_type IN ('human', 'llm')),
    comment    TEXT,
    timestamp  TEXT NOT NULL
);

-- benchmark_golden: cases promoted from the UI as "perfect response"
CREATE TABLE benchmark_golden (
    golden_id   TEXT PRIMARY KEY,
    query       TEXT NOT NULL,
    result_ids  TEXT NOT NULL,  -- JSON list
    judge_type  TEXT NOT NULL,
    promoted_at TEXT NOT NULL
);
```

---

## pytest integration

```python
# tests/benchmark/test_search_benchmark.py
from benchmark.runner import run

def test_search_benchmark_passes():
    result = run(component="search")   # no db_path → no persistence
    assert result.passed, f"Search eval failed: {result.failures}"
    assert result.precision_at_k >= 0.8
```

CI command: `uv run python -m pytest tests/benchmark/`

---

## What is NOT in this spec

- Production monitoring / observability → dedicated spec `2026-03-28-monitoring-design.md`
- Reranking → dedicated spec
- Semantic cache → dedicated spec
- LLM-as-judge implementation → future extension
- "Promote to gold" feature → future extension
