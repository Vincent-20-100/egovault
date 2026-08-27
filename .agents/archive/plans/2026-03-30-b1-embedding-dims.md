# B1 — Configurable `embedding.dims` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the 3 hardcoded `768` values in `infrastructure/db.py` and 44 occurrences across 11 test files, replacing them with a single configurable source of truth in `system.yaml`.

**Architecture:** Add an `EmbeddingConfig` section to `SystemConfig` with `dims: int = 768`. Make `init_db` accept `dims` (with default 768 for backward compatibility). Replace the static `_SCHEMA_SQL` vec table definitions with a `_build_vault_schema_sql(dims)` helper. Add startup validation: warn if `db_metadata.embedding_dim` disagrees with the passed `dims`. Centralize mock embeddings in `tests/conftest.py` via `make_embedding()` helper.

**Tech Stack:** `core/config.py`, `infrastructure/db.py`, `config/system.yaml`, 11 test files, `api/main.py`, `tests/conftest.py`.

---

## File Map

**Modify:**
- `config/system.yaml` — add `embedding:` section
- `core/config.py` — add `EmbeddingConfig`, wire into `SystemConfig`
- `infrastructure/db.py` — dynamic schema builder, `init_db` dims param, startup validation
- `api/main.py` — pass `dims` from settings to `init_db`
- `tests/conftest.py` — add `EMBEDDING_DIMS = 768` + `make_embedding()` helper
- `tests/api/conftest.py` — pass `dims` from settings to `init_db`
- `tests/core/test_config.py` — add `EmbeddingConfig` tests
- `tests/infrastructure/test_db.py` — add dims-aware + validation tests
- 11 test files — replace `[0.1] * 768` with `make_embedding()`

**Test files to bulk-update (replace `[0.1] * 768` → `make_embedding()`):**
1. `tests/infrastructure/test_db.py`
2. `tests/infrastructure/test_embedding_provider.py`
3. `tests/mcp/test_server.py`
4. `tests/tools/text/test_embed.py`
5. `tests/tools/text/test_embed_note.py`
6. `tests/tools/vault/test_create_note.py`
7. `tests/tools/vault/test_search.py`
8. `tests/tools/vault/test_update_note.py`
9. `tests/workflows/test_ingest_audio.py`
10. `tests/workflows/test_ingest_pdf.py`
11. `tests/workflows/test_ingest_youtube.py`

---

## Task 1: Config — `embedding` section + `EmbeddingConfig`

**Files:**
- Modify: `config/system.yaml`
- Modify: `core/config.py`
- Modify: `tests/core/test_config.py`

- [ ] **Step 1: Add `embedding` section to `config/system.yaml`**

In `config/system.yaml`, add after the `llm:` section:

```yaml
embedding:
  dims: 768              # dimension of embedding vectors — single source of truth
  provider: ollama       # embedding provider (ollama | openai)
  model: nomic-embed-text
```

- [ ] **Step 2: Add `EmbeddingConfig` to `core/config.py`**

In `core/config.py`, add after the `ChunkingConfig` class:

```python
class EmbeddingConfig(BaseModel):
    dims: int = 768
    provider: str = "ollama"
    model: str = "nomic-embed-text"
```

Update `SystemConfig` to include it:

```python
class SystemConfig(BaseModel):
    chunking: ChunkingConfig
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMSystemConfig
    upload: UploadConfig = UploadConfig()
    taxonomy: TaxonomyConfig
```

(The `EmbeddingConfig()` default means old `system.yaml` files without `embedding:` still work.)

- [ ] **Step 3: Write tests for `EmbeddingConfig`**

Add to `tests/core/test_config.py`:

```python
def test_embedding_config_loads_from_system_yaml(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)
    # Add embedding section to system.yaml
    import yaml
    sys_yaml = yaml.safe_load((config_dir / "system.yaml").read_text())
    sys_yaml["embedding"] = {"dims": 512, "provider": "openai", "model": "text-embedding-3-small"}
    (config_dir / "system.yaml").write_text(yaml.dump(sys_yaml))

    from core.config import load_settings
    settings = load_settings(config_dir)

    assert settings.system.embedding.dims == 512
    assert settings.system.embedding.provider == "openai"
    assert settings.system.embedding.model == "text-embedding-3-small"


def test_embedding_config_defaults_to_768_if_missing(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)
    # system.yaml WITHOUT embedding section (backward compat)

    from core.config import load_settings
    settings = load_settings(config_dir)

    assert settings.system.embedding.dims == 768
    assert settings.system.embedding.provider == "ollama"
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Vincent/GitHub/Vincent-20-100/egovault
.venv/Scripts/python -m pytest tests/core/test_config.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add config/system.yaml core/config.py tests/core/test_config.py
git commit -m "feat: add EmbeddingConfig to SystemConfig with dims as single source of truth"
```

---

## Task 2: Infrastructure — dynamic schema + startup validation

**Files:**
- Modify: `infrastructure/db.py`
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Write new failing tests**

Add to `tests/infrastructure/test_db.py`:

```python
def test_init_db_creates_vec_tables_with_custom_dims(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "custom_dims.db"
    init_db(db_file, dims=512)
    conn = get_vault_connection(db_file)
    # sqlite-vec reports dims via vec_dims on an INSERT; verify through metadata
    meta = dict(conn.execute("SELECT key, value FROM db_metadata").fetchall())
    conn.close()
    assert meta["embedding_dim"] == "512"


def test_init_db_metadata_reflects_params(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "params.db"
    init_db(db_file, dims=1536, provider="openai", model="text-embedding-3-small")
    conn = get_vault_connection(db_file)
    meta = dict(conn.execute("SELECT key, value FROM db_metadata").fetchall())
    conn.close()
    assert meta["embedding_dim"] == "1536"
    assert meta["embedding_provider"] == "openai"
    assert meta["embedding_model"] == "text-embedding-3-small"


def test_init_db_warns_on_dim_mismatch(tmp_path, caplog):
    import logging
    from infrastructure.db import init_db
    db_file = tmp_path / "mismatch.db"
    # First init: dims=768 (stored in metadata)
    init_db(db_file, dims=768)
    # Second init: dims=1536 (mismatch)
    with caplog.at_level(logging.WARNING, logger="infrastructure.db"):
        init_db(db_file, dims=1536)
    assert any("does not match" in r.message for r in caplog.records)


def test_init_db_no_warning_when_dims_match(tmp_path, caplog):
    import logging
    from infrastructure.db import init_db
    db_file = tmp_path / "match.db"
    init_db(db_file, dims=768)
    with caplog.at_level(logging.WARNING, logger="infrastructure.db"):
        init_db(db_file, dims=768)
    assert not any("does not match" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v \
  -k "custom_dims or metadata_reflects or dim_mismatch or no_warning"
```
Expected: FAIL — `init_db` doesn't accept `dims` parameter yet.

- [ ] **Step 3: Update `infrastructure/db.py`**

Replace the static `_SCHEMA_SQL` vector table definitions and `_METADATA_SQL` with dynamic builders.

**3a.** Remove the vec table lines from `_SCHEMA_SQL` (keep the rest). The section to remove (lines 87-95):
```python
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
    chunk_uid    TEXT,
    embedding    FLOAT[768]
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_vec USING vec0(
    note_uid     TEXT,
    embedding    FLOAT[768]
);
```

**3b.** Replace `_METADATA_SQL` entirely:

```python
def _build_vec_schema_sql(dims: int) -> str:
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


def _build_metadata_sql(dims: int, provider: str, model: str) -> str:
    return f"""
    INSERT OR IGNORE INTO db_metadata VALUES ('embedding_provider', '{provider}');
    INSERT OR IGNORE INTO db_metadata VALUES ('embedding_model', '{model}');
    INSERT OR IGNORE INTO db_metadata VALUES ('embedding_dim', '{dims}');
    """
```

**3c.** Update `init_db` signature and body:

```python
import logging

_logger = logging.getLogger(__name__)


def init_db(
    db_path: Path,
    dims: int = 768,
    provider: str = "ollama",
    model: str = "nomic-embed-text",
) -> None:
    """
    Create all tables and virtual tables if they do not exist.
    Inserts initial db_metadata (embedding_provider, embedding_model, embedding_dim).
    Safe to call on an existing DB (idempotent).
    Warns if the stored embedding_dim differs from the configured dims.
    """
    conn = get_vault_connection(db_path)
    conn.executescript(_SCHEMA_SQL)
    conn.executescript(_build_vec_schema_sql(dims))
    conn.executescript(_build_metadata_sql(dims, provider, model))

    # Startup validation — warn on dim mismatch (re-embedding is user-initiated)
    row = conn.execute(
        "SELECT value FROM db_metadata WHERE key = 'embedding_dim'"
    ).fetchone()
    if row is not None:
        stored_dim = int(row[0])
        if stored_dim != dims:
            _logger.warning(
                f"Config embedding.dims ({dims}) does not match database ({stored_dim}). "
                "Run re-embedding to fix silent search failures."
            )

    conn.commit()
    conn.close()
    from core.security import set_restrictive_permissions
    set_restrictive_permissions(db_path)
```

Note: `_build_metadata_sql` uses `INSERT OR IGNORE`, so on an existing DB the values remain unchanged. The mismatch check reads the value already stored (before the OR IGNORE no-op) and compares it.

- [ ] **Step 4: Run new tests**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```
Expected: all PASS.

- [ ] **Step 5: Verify existing tests still pass**

```bash
.venv/Scripts/python -m pytest tests/ -q --tb=short
```
Expected: all PASS — default `dims=768` matches all existing test expectations.

- [ ] **Step 6: Commit**

```bash
git add infrastructure/db.py tests/infrastructure/test_db.py
git commit -m "feat: make init_db dims-configurable with startup mismatch validation"
```

---

## Task 3: Centralize test embeddings — `make_embedding()` helper

**Files:**
- Modify: `tests/conftest.py`
- Modify: all 11 test files listed in the File Map

- [ ] **Step 1: Add `EMBEDDING_DIMS` and `make_embedding()` to `tests/conftest.py`**

Add after the existing imports in `tests/conftest.py`:

```python
# ============================================================
# EMBEDDING TEST HELPERS
# ============================================================

EMBEDDING_DIMS: int = 768
"""Dimension of mock embeddings — mirrors system.yaml:embedding.dims."""


def make_embedding(value: float = 0.1) -> list[float]:
    """Create a mock embedding vector with the configured dimension."""
    return [value] * EMBEDDING_DIMS
```

- [ ] **Step 2: Verify the helper is importable from tests**

```bash
.venv/Scripts/python -c "
import sys; sys.path.insert(0, '.')
from tests.conftest import make_embedding, EMBEDDING_DIMS
print('DIMS:', EMBEDDING_DIMS)
print('LEN:', len(make_embedding()))
print('OK')
"
```
Expected: `DIMS: 768`, `LEN: 768`, `OK`.

- [ ] **Step 3: Bulk-replace `[0.1] * 768` with `make_embedding()` across test files**

First, verify the scope:
```bash
grep -rn "\[0\.1\] \* 768\|\[0\.2\] \* 768" tests/ --include="*.py"
```

Then apply replacements. For each file listed in the File Map, the pattern is:

**In test files that import via pytest fixtures** — add the import at the top:
```python
from tests.conftest import make_embedding
```
Then replace all occurrences of `[0.1] * 768` with `make_embedding()` and `[0.2] * 768` with `make_embedding(0.2)`.

Run this sed command to do the bulk replacement (adjust if any files use different values):
```bash
cd /c/Users/Vincent/GitHub/Vincent-20-100/egovault

# Replace [0.1] * 768 with make_embedding()
for f in \
  tests/infrastructure/test_db.py \
  tests/infrastructure/test_embedding_provider.py \
  tests/mcp/test_server.py \
  tests/tools/text/test_embed.py \
  tests/tools/text/test_embed_note.py \
  tests/tools/vault/test_create_note.py \
  tests/tools/vault/test_search.py \
  tests/tools/vault/test_update_note.py \
  tests/workflows/test_ingest_audio.py \
  tests/workflows/test_ingest_pdf.py \
  tests/workflows/test_ingest_youtube.py; do
  sed -i 's/\[0\.1\] \* 768/make_embedding()/g' "$f"
  sed -i 's/\[0\.2\] \* 768/make_embedding(0.2)/g' "$f"
done
```

- [ ] **Step 4: Add `make_embedding` import to each updated test file**

For each test file that now uses `make_embedding()`, verify there's no import already (conftest fixtures are available automatically in pytest, but `make_embedding` is a function, not a fixture — it needs an explicit import).

**Option A (simpler):** Make `make_embedding` available as a pytest fixture:

In `tests/conftest.py`, add:
```python
@pytest.fixture
def embedding_dims() -> int:
    return EMBEDDING_DIMS
```

And expose `make_embedding` at module level (already done above). Then test files import it directly.

**Option B:** Add to each test file at the top:
```python
from tests.conftest import make_embedding
```

Use Option B (explicit import). The sed commands above replace the values but not the imports — add the import line to each affected file manually or via:
```bash
for f in \
  tests/infrastructure/test_db.py \
  tests/infrastructure/test_embedding_provider.py \
  tests/mcp/test_server.py \
  tests/tools/text/test_embed.py \
  tests/tools/text/test_embed_note.py \
  tests/tools/vault/test_create_note.py \
  tests/tools/vault/test_search.py \
  tests/tools/vault/test_update_note.py \
  tests/workflows/test_ingest_audio.py \
  tests/workflows/test_ingest_pdf.py \
  tests/workflows/test_ingest_youtube.py; do
  # Only add if not already imported
  grep -q "make_embedding" "$f" && \
    sed -i '1s/^/from tests.conftest import make_embedding\n/' "$f"
done
```

- [ ] **Step 5: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short
```
Expected: all PASS — `make_embedding()` produces identical output to `[0.1] * 768`.

- [ ] **Step 6: Verify no `768` literals remain in test files (except the constant itself)**

```bash
grep -rn "\* 768\|768\]" tests/ --include="*.py" | grep -v "EMBEDDING_DIMS\|# " | grep -v conftest.py
```
Expected: no output (all occurrences replaced).

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py \
        tests/infrastructure/test_db.py \
        tests/infrastructure/test_embedding_provider.py \
        tests/mcp/test_server.py \
        tests/tools/text/test_embed.py \
        tests/tools/text/test_embed_note.py \
        tests/tools/vault/test_create_note.py \
        tests/tools/vault/test_search.py \
        tests/tools/vault/test_update_note.py \
        tests/workflows/test_ingest_audio.py \
        tests/workflows/test_ingest_pdf.py \
        tests/workflows/test_ingest_youtube.py
git commit -m "refactor: centralize mock embeddings via make_embedding() — remove hardcoded 768 from tests"
```

---

## Task 4: Update production callers to pass dims from settings

**Files:**
- Modify: `api/main.py`
- Modify: `tests/api/conftest.py`

- [ ] **Step 1: Update `api/main.py`**

In `api/main.py`, in the `lifespan` context manager, replace:
```python
        init_db(settings.vault_db_path)
```
With:
```python
        init_db(
            settings.vault_db_path,
            dims=settings.system.embedding.dims,
            provider=settings.system.embedding.provider,
            model=settings.system.embedding.model,
        )
```

- [ ] **Step 2: Update `tests/api/conftest.py`**

In `tests/api/conftest.py`, replace:
```python
    init_db(settings.vault_db_path)
```
With:
```python
    init_db(
        settings.vault_db_path,
        dims=settings.system.embedding.dims,
        provider=settings.system.embedding.provider,
        model=settings.system.embedding.model,
    )
```

(The test system.yaml now has an `embedding:` section from Task 1, so `settings.system.embedding.dims` is available. However, the API conftest writes its own system.yaml without the embedding section — add it now.)

Also update the `_write_configs` function in `tests/api/conftest.py` to include the embedding section:
```python
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "embedding": {"dims": 768, "provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese", "reflexion"],
            "source_types": ["youtube", "audio", "pdf"],
            "generation_templates": ["standard"],
        },
    }))
```

- [ ] **Step 3: Update `tests/conftest.py` `tmp_settings` fixture similarly**

The root `tests/conftest.py` `tmp_settings` fixture also writes a system.yaml. Add the embedding section there too:
```python
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "embedding": {"dims": 768, "provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese", "concept", "reflexion"],
            "source_types": ["youtube", "audio", "pdf"],
            "generation_templates": ["standard"],
        },
    }))
```

- [ ] **Step 4: Run the full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -q --tb=short
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add api/main.py tests/api/conftest.py tests/conftest.py
git commit -m "feat: pass embedding dims from settings to init_db in API startup and test fixtures"
```

---

## Task 5: Final verification

- [ ] **Step 1: Verify no hardcoded `768` remain in production code**

```bash
grep -rn "768" infrastructure/db.py core/config.py api/main.py workflows/ tools/ mcp/ --include="*.py"
```
Expected: no results (or only comments). Any remaining occurrence is a bug.

- [ ] **Step 2: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short
```
Expected: all PASS.

- [ ] **Step 3: Manual verification — check startup validation fires correctly**

```python
# Verify warning logic manually
.venv/Scripts/python -c "
import tempfile, pathlib, logging
logging.basicConfig(level=logging.WARNING)
from infrastructure.db import init_db
with tempfile.TemporaryDirectory() as d:
    db = pathlib.Path(d) / 'test.db'
    init_db(db, dims=768)     # create with 768
    init_db(db, dims=1536)    # should warn
"
```
Expected: warning message containing "does not match" printed.

- [ ] **Step 4: Final commit if any fixups needed**

```bash
git add -p
git commit -m "chore: B1 embedding.dims — fixups"
```

---

## What this does NOT include

Per spec §4:
- Re-embedding script (`scripts/maintenance/reembed_all.py`) — see `docs/FUTURE-WORK.md`
- Semantic cache vec table — comes with D2 (semantic cache spec)
- Changing the actual embedding model — this just makes the dimension configurable
