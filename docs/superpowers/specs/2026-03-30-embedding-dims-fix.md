# B1 — Configurable `embedding.dims` Fix

**Date:** 2026-03-30
**Status:** Approved
**Roadmap item:** B1 — `embedding.dims` fix
**Extracted from:** `2026-03-28-semantic-cache-design.md` (cross-cutting fix section)

---

## 1. Problem

`768` is hardcoded in 3 places in `infrastructure/db.py` and 49 occurrences across 11 test files. If the embedding model changes (e.g., OpenAI `text-embedding-3-small` = 1536 dims, or a future Ollama model with different dimensions), the entire codebase breaks.

**Hardcoded locations in `infrastructure/db.py`:**
- Line 89: `chunks_vec` schema → `embedding FLOAT[768]`
- Line 94: `notes_vec` schema → `embedding FLOAT[768]`
- Line 130: `db_metadata` insert → `('embedding_dim', '768')`

**Hardcoded in tests (49 occurrences across 11 files):**
All test files use `[0.1] * 768` or similar patterns to create mock embeddings.

This violates G3 (config-driven, not code-driven).

---

## 2. Fix

### 2.1 Config: add `embedding` section to `system.yaml`

```yaml
# config/system.yaml
embedding:
  dims: 768              # single source of truth for all vec tables
  provider: ollama        # ollama | openai (moved from existing config if applicable)
  model: nomic-embed-text # moved from db_metadata
```

Add corresponding Pydantic model in `core/config.py`:
```python
class EmbeddingConfig(BaseModel):
    dims: int = 768
    provider: str = "ollama"
    model: str = "nomic-embed-text"
```

Wire into `SystemConfig` so `settings.system.embedding.dims` is accessible everywhere.

### 2.2 Infrastructure: dynamic schema in `db.py`

Replace the hardcoded schema SQL with a function:

```python
def _build_vault_schema_sql(dims: int) -> str:
    return f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
        chunk_uid    TEXT,
        embedding    FLOAT[{dims}]
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS notes_vec USING vec0(
        note_uid     TEXT,
        embedding    FLOAT[{dims}]
    );
    """
```

`init_db(settings)` now passes `settings.system.embedding.dims` to the schema builder.

### 2.3 Metadata: derive from config

Replace the hardcoded `db_metadata` insert:
```python
# Before
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_dim', '768');

# After — generated from settings
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_dim', '{dims}');
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_model', '{model}');
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_provider', '{provider}');
```

### 2.4 Startup validation

On `init_db`, compare `db_metadata.embedding_dim` with `settings.system.embedding.dims`. If they differ:
- Log a clear warning: "Config embedding.dims ({config}) does not match database ({db}). Run re-embedding script to fix."
- Do NOT silently proceed — dimension mismatch causes silent search failures.
- Do NOT auto-migrate — re-embedding is destructive and must be user-initiated (see `docs/FUTURE-WORK.md: Re-embedding on model change`).

### 2.5 Tests: centralized constant

Add to `tests/conftest.py`:
```python
EMBEDDING_DIMS = 768

def make_embedding(value: float = 0.1) -> list[float]:
    """Create a mock embedding vector with the configured dimension."""
    return [value] * EMBEDDING_DIMS
```

Replace all `[0.1] * 768` with `make_embedding()` or `make_embedding(0.2)` across all 11 test files.

---

## 3. Files to modify

| File | Change |
|------|--------|
| `config/system.yaml` | Add `embedding:` section |
| `core/config.py` | Add `EmbeddingConfig` model, wire into `SystemConfig` |
| `infrastructure/db.py` | Replace hardcoded `768` with `dims` parameter, dynamic schema |
| `tests/conftest.py` | Add `EMBEDDING_DIMS` constant and `make_embedding()` helper |
| `tests/**/*.py` (11 files) | Replace `[0.1] * 768` with `make_embedding()` |

---

## 4. What this does NOT include

- Re-embedding script (`scripts/maintenance/reembed_all.py`) — see `docs/FUTURE-WORK.md`
- Semantic cache vec table — that comes with D2 (semantic cache spec)
- Changing the actual embedding model — this just makes the dimension configurable

---

## 5. Tests

```
tests/infrastructure/test_db.py
    - init_db creates vec tables with dims from settings
    - startup validation warns on dim mismatch
    - db_metadata reflects config values

tests/core/test_config.py
    - EmbeddingConfig validates dims as positive integer
    - system.yaml parsed correctly with embedding section
```

---

## 6. Guardrails checklist

- [x] No library names in user-facing strings (G1)
- [x] Docstrings describe what, not how (G2)
- [x] Dimension is config-driven — single source of truth in system.yaml (G3)
- [x] No architecture boundary changes (G4)
- [x] No new abstractions — just a config section and a function parameter (G5)
- [x] Clear warning on mismatch, not silent failure (G6)
- [x] English in code (G7)
- [x] Tests updated to use centralized constant (G8)
- [x] Pydantic model for config (G9)
- [x] No security concerns (G10)
- [x] No routing layer changes (G11)
- [x] db_metadata derives from config — no duplication (G12)
