# EgoVault — Plan 1: Foundation (core/ + infrastructure/)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full foundation layer — uid/slug generation, Pydantic validators, config loading, structured logging, SQLite+sqlite-vec DB layer, embedding provider, and vault markdown writer.

**Architecture:** Bottom-up. `core/` has no external deps beyond pydantic + stdlib. `infrastructure/` adds sqlite-vec, requests. No business logic — just typed plumbing everything else depends on. Dependency direction: `infrastructure/` → `core/` → stdlib. `@loggable` uses lazy import to write to DB without `core/` depending on `infrastructure/` at module level.

**Tech Stack:** Python 3.10+, pydantic>=2.0, PyYAML>=6.0, sqlite-vec>=0.1.0, requests>=2.31, pytest>=9.0

**Spec:** `docs/specs/2026-03-25-egovault-v2-architecture-design.md`

---

## Part 0 — Scope of this plan

This plan covers:
- `core/uid.py` — slug derivation + collision resolution
- `core/schemas.py` — Pydantic validators (tags, taxonomy)
- `core/config.py` — load_settings(), path properties
- `core/logging.py` — @loggable decorator + configure()
- `infrastructure/db.py` — full SQLite+sqlite-vec layer
- `infrastructure/embedding_provider.py` — embed() via Ollama
- `infrastructure/vault_writer.py` — Markdown + frontmatter generation

**Not in this plan** (separate plans):
- `tools/` (Plan 2)
- `workflows/` + `mcp/server.py` (Plan 3)
- `api/` + `frontend/` (future)

---

## Task 1: Project setup — deps + test directories + conftest

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/core/__init__.py`
- Create: `tests/infrastructure/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Update pyproject.toml**

Replace the full file with:

```toml
[project]
name = "egovault"
version = "2.0.0"
description = "EgoVault — personal memory infrastructure"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "PyYAML>=6.0",
    "sqlite-vec>=0.1.0",
    "requests>=2.31",
    "faster-whisper>=1.2.0",
    "yt-dlp>=2026.3.0",
    "youtube-transcript-api>=1.2",
]

[dependency-groups]
dev = [
    "pytest>=9.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Install dependencies**

```bash
.venv/Scripts/pip install -e ".[dev]"
```

Expected: installs pydantic, sqlite-vec, requests (among others). No errors.

- [ ] **Step 3: Create test directories**

```bash
mkdir tests/core tests/infrastructure
touch tests/core/__init__.py tests/infrastructure/__init__.py
```

- [ ] **Step 4: Create tests/conftest.py**

```python
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def tmp_settings(tmp_path):
    """Minimal Settings built from test config files. Uses tmp_path as user_dir."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese", "concept", "reflexion"],
            "source_types": ["youtube", "audio", "pdf"],
            "generation_templates": ["standard"],
        },
    }))

    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {
            "content_language": "fr",
            "obsidian_sync": True,
            "default_generation_template": "standard",
        },
    }))

    user_dir = tmp_path / "egovault-user"
    (user_dir / "data").mkdir(parents=True)
    (user_dir / "vault" / "notes").mkdir(parents=True)

    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))

    from core.config import load_settings
    return load_settings(config_dir)


@pytest.fixture
def tmp_db(tmp_path):
    """Initialized test database (all tables created)."""
    from infrastructure.db import init_db
    db_file = tmp_path / "test.db"
    init_db(db_file)
    return db_file
```

- [ ] **Step 5: Verify import chain**

```bash
.venv/Scripts/python -m pytest tests/ --collect-only
```

Expected: 0 test collection errors (0 tests found — stubs have none yet).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/core/__init__.py tests/infrastructure/__init__.py tests/conftest.py
git commit -m "chore: pyproject.toml v2 + test directories + conftest fixtures"
```

---

## Task 2: core/uid.py — make_slug + make_unique_slug

**Files:**
- Modify: `core/uid.py`
- Create: `tests/core/test_uid.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_uid.py`:

```python
from core.uid import generate_uid, make_slug, make_unique_slug


def test_generate_uid_is_uuid4_format():
    uid = generate_uid()
    assert len(uid) == 36
    parts = uid.split("-")
    assert len(parts) == 5
    assert parts[2].startswith("4")  # version 4


def test_make_slug_basic():
    assert make_slug("Hello World") == "hello-world"


def test_make_slug_accents():
    assert make_slug("Élasticité des Prix") == "elasticite-des-prix"


def test_make_slug_special_chars():
    # non-alphanum → hyphen, then collapsed
    assert make_slug("C++ & Python!") == "c-python"


def test_make_slug_already_clean():
    assert make_slug("bitcoin") == "bitcoin"


def test_make_slug_leading_trailing_hyphens():
    assert make_slug("  --hello--  ") == "hello"


def test_make_slug_consecutive_hyphens_collapsed():
    assert make_slug("hello   world") == "hello-world"


def test_make_slug_within_80_chars():
    # 15-char words separated by spaces → slug <= 80 chars
    title = "un " + "a" * 78
    result = make_slug(title)
    assert len(result) <= 80


def test_make_slug_truncate_at_last_hyphen():
    # "un-" + 78 a's = 81 chars → cuts at hyphen → "un"
    title = "un " + "a" * 78
    result = make_slug(title)
    assert result == "un"


def test_make_slug_truncate_no_hyphen_case():
    # single word longer than 80 chars → hard truncate at 80
    title = "a" * 100
    result = make_slug(title)
    assert result == "a" * 80


def test_make_unique_slug_no_collision():
    assert make_unique_slug("Test Title", set()) == "test-title"


def test_make_unique_slug_first_collision():
    existing = {"test-title"}
    assert make_unique_slug("Test Title", existing) == "test-title-2"


def test_make_unique_slug_multiple_collisions():
    existing = {"test-title", "test-title-2", "test-title-3"}
    assert make_unique_slug("Test Title", existing) == "test-title-4"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_uid.py -v
```

Expected: FAIL — `make_slug` and `make_unique_slug` raise `TypeError` (return None).

- [ ] **Step 3: Implement make_slug and make_unique_slug**

Replace the `...` stubs in `core/uid.py`:

```python
def make_slug(title: str) -> str:
    import unicodedata
    import re
    # 1. Lowercase
    slug = title.lower()
    # 2. Strip accents (NFD → ASCII)
    slug = unicodedata.normalize("NFD", slug)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    # 3. Replace non-[a-z0-9] with hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # 4. Collapse consecutive hyphens (already done by step 3 with +)
    # 5. Strip leading/trailing hyphens
    slug = slug.strip("-")
    # 6. Truncate to 80 chars, cut at last hyphen if mid-word
    if len(slug) > 80:
        slug = slug[:80]
        last_hyphen = slug.rfind("-")
        if last_hyphen > 0:
            slug = slug[:last_hyphen]
    return slug


def make_unique_slug(title: str, existing_slugs: set[str]) -> str:
    base = make_slug(title)
    if base not in existing_slugs:
        return base
    counter = 2
    while f"{base}-{counter}" in existing_slugs:
        counter += 1
    return f"{base}-{counter}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_uid.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/uid.py tests/core/test_uid.py
git commit -m "feat: core/uid.py — make_slug + make_unique_slug"
```

---

## Task 3: core/schemas.py — tags_must_be_kebab validator

**Files:**
- Modify: `core/schemas.py`
- Create: `tests/core/test_schemas.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from core.schemas import NoteContentInput


# Helper: minimal valid NoteContentInput data (no taxonomy context needed for tag tests)
def _base():
    return {
        "title": "Test Note",
        "docstring": "A test note.",
        "body": "Some body content here.",
        "tags": ["valid-tag"],
    }


def test_tags_valid():
    data = {**_base(), "tags": ["decentralisation", "bitcoin", "monnaie-numerique"]}
    note = NoteContentInput(**data)
    assert note.tags == ["decentralisation", "bitcoin", "monnaie-numerique"]


def test_tags_empty_string_rejected():
    with pytest.raises(ValidationError, match="empty"):
        NoteContentInput(**{**_base(), "tags": [""]})


def test_tags_uppercase_rejected():
    with pytest.raises(ValidationError, match="lowercase"):
        NoteContentInput(**{**_base(), "tags": ["Bitcoin"]})


def test_tags_accent_rejected():
    with pytest.raises(ValidationError, match="ASCII"):
        NoteContentInput(**{**_base(), "tags": ["décentralisation"]})


def test_tags_spaces_rejected():
    with pytest.raises(ValidationError, match="kebab"):
        NoteContentInput(**{**_base(), "tags": ["tag avec espaces"]})


def test_tags_underscore_rejected():
    with pytest.raises(ValidationError, match="kebab"):
        NoteContentInput(**{**_base(), "tags": ["tag_underscore"]})


def test_tags_too_long_rejected():
    with pytest.raises(ValidationError, match="80"):
        NoteContentInput(**{**_base(), "tags": ["a" * 81]})


def test_tags_duplicates_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        NoteContentInput(**{**_base(), "tags": ["bitcoin", "bitcoin"]})


def test_tags_min_one_required():
    with pytest.raises(ValidationError):
        NoteContentInput(**{**_base(), "tags": []})


def test_tags_max_ten():
    # 10 tags is fine
    tags = [f"tag-{i}" for i in range(10)]
    note = NoteContentInput(**{**_base(), "tags": tags})
    assert len(note.tags) == 10

    # 11 tags fails
    with pytest.raises(ValidationError):
        NoteContentInput(**{**_base(), "tags": [f"tag-{i}" for i in range(11)]})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_schemas.py -v
```

Expected: FAIL — `tags_must_be_kebab` raises `...` (not implemented).

- [ ] **Step 3: Implement tags_must_be_kebab in core/schemas.py**

Replace the `...` in the `tags_must_be_kebab` method:

```python
@field_validator("tags")
@classmethod
def tags_must_be_kebab(cls, v: list[str]) -> list[str]:
    import re
    for tag in v:
        if not tag:
            raise ValueError("tags must not contain empty strings")
        if len(tag) > 80:
            raise ValueError(f"tag '{tag}' exceeds 80 characters")
        if tag != tag.lower():
            raise ValueError(f"tag '{tag}' must be lowercase")
        # Check ASCII only (no accents)
        try:
            tag.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError(f"tag '{tag}' must contain only ASCII characters (no accents)")
        # Check kebab-case: only [a-z0-9-]
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", tag):
            raise ValueError(
                f"tag '{tag}' must be kebab-case: only [a-z0-9] and hyphens, "
                "no leading/trailing hyphens, no spaces or underscores"
            )
    if len(v) != len(set(v)):
        raise ValueError("tags must not contain duplicates")
    return v
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_schemas.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/schemas.py tests/core/test_schemas.py
git commit -m "feat: NoteContentInput.tags_must_be_kebab validator"
```

---

## Task 4: core/schemas.py — validate_taxonomy validator

**Files:**
- Modify: `core/schemas.py`
- Modify: `tests/core/test_schemas.py`

- [ ] **Step 1: Add taxonomy tests to tests/core/test_schemas.py**

Append to the file:

```python
# ---- Taxonomy validation tests ----

def _taxonomy_ctx():
    """Minimal taxonomy context for model_validate."""
    return {
        "taxonomy": type("T", (), {
            "note_types": ["synthese", "concept"],
            "source_types": ["youtube", "audio"],
            "generation_templates": ["standard"],
        })()
    }


def test_taxonomy_valid_note_type():
    data = {**_base(), "note_type": "synthese"}
    note = NoteContentInput.model_validate(data, context=_taxonomy_ctx())
    assert note.note_type == "synthese"


def test_taxonomy_invalid_note_type():
    data = {**_base(), "note_type": "unknown-type"}
    with pytest.raises(ValidationError, match="note_type"):
        NoteContentInput.model_validate(data, context=_taxonomy_ctx())


def test_taxonomy_valid_source_type():
    data = {**_base(), "source_type": "youtube"}
    note = NoteContentInput.model_validate(data, context=_taxonomy_ctx())
    assert note.source_type == "youtube"


def test_taxonomy_invalid_source_type():
    data = {**_base(), "source_type": "telegram"}
    with pytest.raises(ValidationError, match="source_type"):
        NoteContentInput.model_validate(data, context=_taxonomy_ctx())


def test_taxonomy_none_values_skipped():
    # note_type=None and source_type=None should not be validated
    data = {**_base(), "note_type": None, "source_type": None}
    note = NoteContentInput.model_validate(data, context=_taxonomy_ctx())
    assert note.note_type is None
    assert note.source_type is None


def test_taxonomy_skipped_without_context():
    # When no context is provided, taxonomy validation is skipped
    data = {**_base(), "note_type": "totally-unknown"}
    note = NoteContentInput(**data)  # no model_validate, no context
    assert note.note_type == "totally-unknown"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_schemas.py::test_taxonomy_invalid_note_type -v
```

Expected: FAIL — `validate_taxonomy` does nothing (stub).

- [ ] **Step 3: Implement validate_taxonomy in core/schemas.py**

Replace the `...` in the `validate_taxonomy` method:

```python
@model_validator(mode="before")
@classmethod
def validate_taxonomy(cls, values: dict, info) -> dict:
    if not info or not info.context:
        return values
    taxonomy = info.context.get("taxonomy")
    if taxonomy is None:
        return values
    note_type = values.get("note_type")
    if note_type is not None and note_type not in taxonomy.note_types:
        raise ValueError(
            f"note_type '{note_type}' is not in taxonomy.note_types: {taxonomy.note_types}"
        )
    source_type = values.get("source_type")
    if source_type is not None and source_type not in taxonomy.source_types:
        raise ValueError(
            f"source_type '{source_type}' is not in taxonomy.source_types: {taxonomy.source_types}"
        )
    return values
```

- [ ] **Step 4: Run all schema tests**

```bash
.venv/Scripts/python -m pytest tests/core/test_schemas.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/schemas.py tests/core/test_schemas.py
git commit -m "feat: NoteContentInput.validate_taxonomy — runtime taxonomy check"
```

---

## Task 5: core/config.py — load_settings + path properties

**Files:**
- Modify: `core/config.py`
- Create: `tests/core/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_config.py`:

```python
import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError


def _write_configs(config_dir: Path, user_dir: Path):
    (config_dir / "system.yaml").write_text(yaml.dump({
        "chunking": {"size": 800, "overlap": 80},
        "llm": {"max_retries": 2, "large_format_threshold_tokens": 50000},
        "taxonomy": {
            "note_types": ["synthese"],
            "source_types": ["youtube"],
            "generation_templates": ["standard"],
        },
    }))
    (config_dir / "user.yaml").write_text(yaml.dump({
        "embedding": {"provider": "ollama", "model": "nomic-embed-text"},
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vault": {"content_language": "fr", "obsidian_sync": True,
                  "default_generation_template": "standard"},
    }))
    (config_dir / "install.yaml").write_text(yaml.dump({
        "paths": {"user_dir": str(user_dir)},
        "providers": {"ollama_base_url": "http://localhost:11434"},
    }))


def test_load_settings_success(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)

    assert settings.system.chunking.size == 800
    assert settings.user.embedding.provider == "ollama"
    assert settings.install.providers.ollama_base_url == "http://localhost:11434"
    assert settings.taxonomy.note_types == ["synthese"]


def test_load_settings_missing_user_yaml(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)
    (config_dir / "user.yaml").unlink()

    from core.config import load_settings
    with pytest.raises((FileNotFoundError, ValueError)):
        load_settings(config_dir)


def test_db_path_default(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    (user_dir / "data").mkdir(parents=True)
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.db_path == user_dir / "data" / "egovault.db"


def test_vault_path_default(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    (user_dir / "vault" / "notes").mkdir(parents=True)
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.vault_path == user_dir / "vault" / "notes"


def test_media_path_default(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.media_path == user_dir / "data" / "media"


def test_taxonomy_shortcut(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    _write_configs(config_dir, user_dir)

    from core.config import load_settings
    settings = load_settings(config_dir)
    assert settings.taxonomy is settings.system.taxonomy
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_config.py -v
```

Expected: FAIL — `load_settings` returns None (stub).

- [ ] **Step 3: Implement load_settings and path properties in core/config.py**

Replace the `...` stubs:

```python
# In Settings class, replace the three property stubs:

@property
def db_path(self) -> Path:
    if self.install.paths.db_file:
        return Path(self.install.paths.db_file)
    data_dir = self._data_dir()
    return data_dir / "egovault.db"

@property
def vault_path(self) -> Path:
    if self.install.paths.vault_dir:
        return Path(self.install.paths.vault_dir)
    return Path(self.install.paths.user_dir) / "vault" / "notes"

@property
def media_path(self) -> Path:
    if self.install.paths.media_dir:
        return Path(self.install.paths.media_dir)
    return self._data_dir() / "media"

def _data_dir(self) -> Path:
    if self.install.paths.data_dir:
        return Path(self.install.paths.data_dir)
    return Path(self.install.paths.user_dir) / "data"


# After the Settings class, implement load_settings:

def load_settings(config_dir: Path | None = None) -> Settings:
    import yaml

    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config"

    def _load(filename: str) -> dict:
        path = config_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Required config file not found: {path}\n"
                f"Copy {filename.replace('.yaml', '.yaml.example')} and fill in your values."
            )
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    system_data = _load("system.yaml")
    user_data = _load("user.yaml")
    install_data = _load("install.yaml")

    return Settings(
        system=SystemConfig(**system_data),
        user=UserConfig(**user_data),
        install=InstallConfig(**install_data),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_config.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run all core tests**

```bash
.venv/Scripts/python -m pytest tests/core/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add core/config.py tests/core/test_config.py
git commit -m "feat: core/config.py — load_settings() + path properties"
```

---

## Task 6: core/logging.py — @loggable decorator + configure()

**Files:**
- Modify: `core/logging.py`
- Create: `tests/core/test_logging.py`

Design note: `_write_log` imports `infrastructure.db.insert_tool_log` lazily (inside the function body) so `core/` never imports `infrastructure/` at module level. The module-level `_db_path` is set by calling `configure(db_path)` at application startup.

- [ ] **Step 1: Write the failing tests**

Create `tests/core/test_logging.py`:

```python
import pytest
from unittest.mock import patch, call
from core import logging as ev_logging


def test_serialize_pydantic_model():
    from core.schemas import TranscriptResult
    result = TranscriptResult(text="hello", language="fr", duration_seconds=10.5)
    serialized = ev_logging._serialize(result)
    assert '"text": "hello"' in serialized
    assert '"language": "fr"' in serialized


def test_serialize_plain_dict():
    assert ev_logging._serialize({"key": "value"}) == '{"key": "value"}'


def test_serialize_non_serializable_fallback():
    class Unserializable:
        def __str__(self): return "custom-repr"
    result = ev_logging._serialize(Unserializable())
    assert result == "custom-repr"


def test_loggable_calls_function():
    @ev_logging.loggable("test_tool")
    def my_tool(x: int) -> int:
        return x * 2

    assert my_tool(3) == 6


def test_loggable_captures_exception():
    @ev_logging.loggable("failing_tool")
    def broken_tool(x: int) -> int:
        raise ValueError("oops")

    with pytest.raises(ValueError, match="oops"):
        broken_tool(1)


def test_loggable_writes_to_db_when_configured(tmp_path):
    from infrastructure.db import init_db, get_connection
    db_file = tmp_path / "log_test.db"
    init_db(db_file)
    ev_logging.configure(db_file)

    @ev_logging.loggable("my_logged_tool")
    def add(a: int, b: int) -> int:
        return a + b

    add(1, 2)

    conn = get_connection(db_file)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'my_logged_tool'").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    assert rows[0]["duration_ms"] >= 0

    # cleanup: reset _db_path to avoid polluting other tests
    ev_logging.configure(None)


def test_loggable_writes_failed_status_to_db(tmp_path):
    from infrastructure.db import init_db, get_connection
    db_file = tmp_path / "log_test2.db"
    init_db(db_file)
    ev_logging.configure(db_file)

    @ev_logging.loggable("bad_tool")
    def always_fails(x: int) -> int:
        raise RuntimeError("bad")

    with pytest.raises(RuntimeError):
        always_fails(5)

    conn = get_connection(db_file)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'bad_tool'").fetchall()
    conn.close()

    assert rows[0]["status"] == "failed"
    assert "bad" in rows[0]["error"]
    ev_logging.configure(None)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/core/test_logging.py -v
```

Expected: most FAIL — `_write_log` stub does nothing, `configure` doesn't exist.

- [ ] **Step 3: Implement configure() and _write_log() in core/logging.py**

Add `configure()` and implement `_write_log()`. Replace the `...` stub in `_write_log`:

```python
from pathlib import Path

_db_path: Path | None = None


def configure(db_path: Path | None) -> None:
    """Call at app startup with the resolved DB path. Pass None to disable."""
    global _db_path
    _db_path = db_path


def _write_log(
    tool_name: str,
    input_json: str | None,
    output_json: str | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
) -> None:
    if _db_path is None:
        return
    try:
        from infrastructure.db import insert_tool_log  # lazy — avoids circular import
        insert_tool_log(_db_path, tool_name, input_json, output_json, duration_ms, status, error)
    except Exception:
        pass  # logging must never crash the tool
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/core/test_logging.py -v
```

Expected: tests pass (note: `test_loggable_writes_to_db_when_configured` requires Task 7 to be complete first — skip with `-k "not db"` until then, then run all after Task 12).

- [ ] **Step 5: Commit**

```bash
git add core/logging.py tests/core/test_logging.py
git commit -m "feat: core/logging.py — @loggable decorator + configure()"
```

---

## Task 7: infrastructure/db.py — init_db + get_connection

**Files:**
- Modify: `infrastructure/db.py`
- Create: `tests/infrastructure/test_db.py`

Note: `sqlite-vec` requires `conn.enable_load_extension(True)` before loading. On some systems Python may need to be built with `--enable-shared`. If `enable_load_extension` raises `AttributeError`, the Python build doesn't support extensions — reinstall Python from python.org.

- [ ] **Step 1: Write the failing tests**

Create `tests/infrastructure/test_db.py`:

```python
import pytest
from pathlib import Path


def test_get_connection_loads_sqlite_vec(tmp_path):
    from infrastructure.db import init_db, get_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_connection(db_file)
    # sqlite-vec provides vec_f32 SQL function
    result = conn.execute("SELECT vec_length(vec_f32('[1.0, 2.0, 3.0]'))").fetchone()
    assert result[0] == 3
    conn.close()


def test_init_db_creates_all_tables(tmp_path):
    from infrastructure.db import init_db, get_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_connection(db_file)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'shadow')"
        ).fetchall()
    }
    conn.close()
    for expected in ["sources", "notes", "chunks", "tags", "note_tags", "tool_logs", "db_metadata"]:
        assert expected in tables, f"Table '{expected}' not found. Found: {tables}"


def test_init_db_creates_vec_virtual_tables(tmp_path):
    from infrastructure.db import init_db, get_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_connection(db_file)
    # Virtual tables show up in sqlite_master with type='table'
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master").fetchall()}
    assert "chunks_vec" in tables
    assert "notes_vec" in tables
    conn.close()


def test_init_db_inserts_metadata(tmp_path):
    from infrastructure.db import init_db, get_connection
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_connection(db_file)
    meta = dict(conn.execute("SELECT key, value FROM db_metadata").fetchall())
    conn.close()
    assert meta["embedding_provider"] == "ollama"
    assert meta["embedding_model"] == "nomic-embed-text"
    assert meta["embedding_dim"] == "768"


def test_init_db_idempotent(tmp_path):
    from infrastructure.db import init_db
    db_file = tmp_path / "test.db"
    init_db(db_file)
    init_db(db_file)  # second call must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```

Expected: FAIL — `init_db` and `get_connection` are stubs.

- [ ] **Step 3: Implement get_connection and init_db**

Replace the `...` stubs in `infrastructure/db.py`:

```python
import sqlite3
import sqlite_vec
from pathlib import Path
from core.schemas import Note, Source, ChunkResult, SearchResult, SearchFilters


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    uid          TEXT PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    source_type  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'raw',
    url          TEXT,
    title        TEXT,
    author       TEXT,
    date_added   DATE NOT NULL,
    date_source  DATE,
    media_path   TEXT,
    transcript   TEXT,
    raw_metadata TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    uid                 TEXT PRIMARY KEY,
    source_uid          TEXT REFERENCES sources(uid),
    slug                TEXT UNIQUE NOT NULL,
    note_type           TEXT,
    source_type         TEXT,
    generation_template TEXT,
    rating              INTEGER CHECK(rating BETWEEN 1 AND 5),
    sync_status         TEXT NOT NULL DEFAULT 'synced',
    title               TEXT NOT NULL,
    docstring           TEXT,
    body                TEXT NOT NULL,
    url                 TEXT,
    date_created        DATE NOT NULL,
    date_modified       DATE NOT NULL,
    language            TEXT DEFAULT 'fr'
);

CREATE TABLE IF NOT EXISTS chunks (
    uid          TEXT PRIMARY KEY,
    source_uid   TEXT NOT NULL REFERENCES sources(uid) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    content      TEXT NOT NULL,
    token_count  INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
    chunk_uid    TEXT,
    embedding    FLOAT[768]
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_vec USING vec0(
    note_uid     TEXT,
    embedding    FLOAT[768]
);

CREATE TABLE IF NOT EXISTS db_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    uid          TEXT PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,
    language     TEXT DEFAULT 'fr',
    date_created DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_uid TEXT REFERENCES notes(uid) ON DELETE CASCADE,
    tag_uid  TEXT REFERENCES tags(uid) ON DELETE CASCADE,
    PRIMARY KEY (note_uid, tag_uid)
);

CREATE TABLE IF NOT EXISTS tool_logs (
    uid         TEXT PRIMARY KEY,
    tool_name   TEXT NOT NULL,
    input_json  TEXT,
    output_json TEXT,
    duration_ms INTEGER,
    status      TEXT NOT NULL,
    error       TEXT,
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_METADATA_SQL = """
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_provider', 'ollama');
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_model', 'nomic-embed-text');
INSERT OR IGNORE INTO db_metadata VALUES ('embedding_dim', '768');
"""


def init_db(db_path: Path) -> None:
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA_SQL)
    conn.executescript(_METADATA_SQL)
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/db.py tests/infrastructure/test_db.py
git commit -m "feat: infrastructure/db.py — init_db() + get_connection() with sqlite-vec"
```

---

## Task 8: infrastructure/db.py — sources CRUD

**Files:**
- Modify: `infrastructure/db.py`
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Add source CRUD tests to tests/infrastructure/test_db.py**

Append to the file:

```python
# ---- Sources CRUD ----

def _make_source():
    from core.schemas import Source
    return Source(
        uid="src-uid-1",
        slug="test-source",
        source_type="youtube",
        status="raw",
        url="https://youtube.com/watch?v=test",
        title="Test Source",
        author=None,
        date_added="2026-03-26",
        date_source=None,
        media_path=None,
        transcript=None,
        raw_metadata=None,
    )


def test_insert_and_get_source(tmp_db):
    from infrastructure.db import insert_source, get_source
    source = _make_source()
    insert_source(tmp_db, source)
    retrieved = get_source(tmp_db, "src-uid-1")
    assert retrieved is not None
    assert retrieved.slug == "test-source"
    assert retrieved.source_type == "youtube"


def test_get_source_not_found(tmp_db):
    from infrastructure.db import get_source
    assert get_source(tmp_db, "nonexistent") is None


def test_update_source_status(tmp_db):
    from infrastructure.db import insert_source, update_source_status, get_source
    source = _make_source()
    insert_source(tmp_db, source)
    update_source_status(tmp_db, "src-uid-1", "rag_ready")
    assert get_source(tmp_db, "src-uid-1").status == "rag_ready"


def test_list_sources_by_status(tmp_db):
    from infrastructure.db import insert_source, update_source_status, list_sources_by_status
    from core.schemas import Source
    s1 = _make_source()
    s2 = Source(**{**s1.model_dump(), "uid": "src-uid-2", "slug": "test-source-2"})
    s3 = Source(**{**s1.model_dump(), "uid": "src-uid-3", "slug": "test-source-3", "status": "rag_ready"})
    insert_source(tmp_db, s1)
    insert_source(tmp_db, s2)
    insert_source(tmp_db, s3)
    raw_sources = list_sources_by_status(tmp_db, "raw")
    assert len(raw_sources) == 2
    assert all(s.status == "raw" for s in raw_sources)
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -k "source" -v
```

Expected: FAIL — CRUD functions are stubs.

- [ ] **Step 3: Implement sources CRUD in infrastructure/db.py**

```python
def insert_source(db_path: Path, source: Source) -> None:
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO sources
           (uid, slug, source_type, status, url, title, author,
            date_added, date_source, media_path, transcript, raw_metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source.uid, source.slug, source.source_type, source.status,
         source.url, source.title, source.author, source.date_added,
         source.date_source, source.media_path, source.transcript,
         source.raw_metadata),
    )
    conn.commit()
    conn.close()


def get_source(db_path: Path, uid: str) -> Source | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM sources WHERE uid = ?", (uid,)).fetchone()
    conn.close()
    if row is None:
        return None
    return Source(**dict(row))


def update_source_status(db_path: Path, uid: str, status: str) -> None:
    conn = get_connection(db_path)
    conn.execute("UPDATE sources SET status = ? WHERE uid = ?", (status, uid))
    conn.commit()
    conn.close()


def list_sources_by_status(db_path: Path, status: str) -> list[Source]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM sources WHERE status = ?", (status,)).fetchall()
    conn.close()
    return [Source(**dict(row)) for row in rows]
```

Also add `model_config` to `Source` in `core/schemas.py` so DB extra columns don't break it:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Source(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # ... rest unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/db.py core/schemas.py tests/infrastructure/test_db.py
git commit -m "feat: db sources CRUD — insert, get, update_status, list_by_status"
```

---

## Task 9: infrastructure/db.py — notes CRUD

**Files:**
- Modify: `infrastructure/db.py`
- Modify: `core/schemas.py` (add `extra="ignore"` to Note)
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Add note CRUD tests**

Append to `tests/infrastructure/test_db.py`:

```python
# ---- Notes CRUD ----

def _make_note():
    from core.schemas import Note
    return Note(
        uid="note-uid-1",
        source_uid=None,
        slug="test-note",
        note_type="reflexion",
        source_type=None,
        generation_template=None,
        rating=None,
        sync_status="synced",
        title="Test Note",
        docstring="A test note for testing.",
        body="This is the body of the test note.",
        url=None,
        date_created="2026-03-26",
        date_modified="2026-03-26",
        tags=["test-tag"],
    )


def test_insert_and_get_note(tmp_db):
    from infrastructure.db import insert_note, get_note
    note = _make_note()
    insert_note(tmp_db, note)
    retrieved = get_note(tmp_db, "note-uid-1")
    assert retrieved is not None
    assert retrieved.title == "Test Note"
    assert retrieved.slug == "test-note"


def test_get_note_not_found(tmp_db):
    from infrastructure.db import get_note
    assert get_note(tmp_db, "nonexistent") is None


def test_update_note_fields(tmp_db):
    from infrastructure.db import insert_note, update_note, get_note
    note = _make_note()
    insert_note(tmp_db, note)
    update_note(tmp_db, "note-uid-1", {"rating": 4, "sync_status": "needs_re_embedding"})
    updated = get_note(tmp_db, "note-uid-1")
    assert updated.rating == 4
    assert updated.sync_status == "needs_re_embedding"


def test_get_note_by_source(tmp_db):
    from infrastructure.db import insert_source, insert_note, get_note_by_source
    from core.schemas import Note
    source = _make_source()
    insert_source(tmp_db, source)
    note = Note(**{**_make_note().model_dump(), "source_uid": "src-uid-1"})
    insert_note(tmp_db, note)
    result = get_note_by_source(tmp_db, "src-uid-1")
    assert result is not None
    assert result.uid == "note-uid-1"


def test_list_notes_by_sync_status(tmp_db):
    from infrastructure.db import insert_note, list_notes_by_sync_status
    from core.schemas import Note
    n1 = _make_note()
    n2 = Note(**{**n1.model_dump(), "uid": "note-uid-2", "slug": "test-note-2",
                 "sync_status": "needs_re_embedding"})
    insert_note(tmp_db, n1)
    insert_note(tmp_db, n2)
    synced = list_notes_by_sync_status(tmp_db, "synced")
    assert len(synced) == 1
    assert synced[0].uid == "note-uid-1"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -k "note" -v
```

Expected: FAIL.

- [ ] **Step 3: Add extra="ignore" to Note in core/schemas.py**

```python
class Note(NoteSystemFields, NoteContentInput):
    model_config = ConfigDict(extra="ignore")
    date_modified: str
    rating: int | None = Field(None, ge=1, le=5)
    sync_status: str = "synced"
```

- [ ] **Step 4: Implement notes CRUD in infrastructure/db.py**

```python
def insert_note(db_path: Path, note: Note) -> None:
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO notes
           (uid, source_uid, slug, note_type, source_type, generation_template,
            rating, sync_status, title, docstring, body, url, date_created, date_modified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (note.uid, note.source_uid, note.slug, note.note_type, note.source_type,
         note.generation_template, note.rating, note.sync_status,
         note.title, note.docstring, note.body, note.url,
         note.date_created, note.date_modified),
    )
    conn.commit()
    conn.close()


def get_note(db_path: Path, uid: str) -> Note | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM notes WHERE uid = ?", (uid,)).fetchone()
    conn.close()
    if row is None:
        return None
    data = dict(row)
    data.setdefault("tags", [])
    return Note(**data)


def update_note(db_path: Path, uid: str, fields: dict) -> None:
    if not fields:
        return
    allowed = {
        "title", "docstring", "body", "note_type", "source_type",
        "rating", "sync_status", "date_modified", "url",
    }
    set_clauses = ", ".join(f"{k} = ?" for k in fields if k in allowed)
    values = [v for k, v in fields.items() if k in allowed]
    if not set_clauses:
        return
    conn = get_connection(db_path)
    conn.execute(f"UPDATE notes SET {set_clauses} WHERE uid = ?", values + [uid])
    conn.commit()
    conn.close()


def get_note_by_source(db_path: Path, source_uid: str) -> Note | None:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM notes WHERE source_uid = ?", (source_uid,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    data = dict(row)
    data.setdefault("tags", [])
    return Note(**data)


def list_notes_by_sync_status(db_path: Path, sync_status: str) -> list[Note]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM notes WHERE sync_status = ?", (sync_status,)
    ).fetchall()
    conn.close()
    results = []
    for row in rows:
        data = dict(row)
        data.setdefault("tags", [])
        results.append(Note(**data))
    return results
```

- [ ] **Step 5: Run all tests**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add infrastructure/db.py core/schemas.py tests/infrastructure/test_db.py
git commit -m "feat: db notes CRUD — insert, get, update, get_by_source, list_by_sync_status"
```

---

## Task 10: infrastructure/db.py — chunks + chunk embeddings

**Files:**
- Modify: `infrastructure/db.py`
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Add chunk tests**

Append to `tests/infrastructure/test_db.py`:

```python
# ---- Chunks ----

def _make_chunks():
    from core.schemas import ChunkResult
    return [
        ChunkResult(uid=f"chunk-{i}", position=i, content=f"content {i}", token_count=100)
        for i in range(3)
    ]


def test_insert_and_retrieve_chunks(tmp_db):
    from infrastructure.db import insert_source, insert_chunks, get_connection
    insert_source(tmp_db, _make_source())
    insert_chunks(tmp_db, "src-uid-1", _make_chunks())
    conn = get_connection(tmp_db)
    rows = conn.execute("SELECT * FROM chunks WHERE source_uid = 'src-uid-1'").fetchall()
    conn.close()
    assert len(rows) == 3
    assert rows[0]["position"] == 0


def test_delete_chunks_for_source(tmp_db):
    from infrastructure.db import insert_source, insert_chunks, delete_chunks_for_source, get_connection
    insert_source(tmp_db, _make_source())
    insert_chunks(tmp_db, "src-uid-1", _make_chunks())
    delete_chunks_for_source(tmp_db, "src-uid-1")
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM chunks WHERE source_uid = 'src-uid-1'").fetchone()[0]
    conn.close()
    assert count == 0


def test_insert_chunk_embeddings(tmp_db):
    from infrastructure.db import insert_source, insert_chunks, insert_chunk_embeddings, get_connection
    insert_source(tmp_db, _make_source())
    insert_chunks(tmp_db, "src-uid-1", _make_chunks())
    embedding = [0.1] * 768
    insert_chunk_embeddings(tmp_db, "chunk-0", embedding)
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM chunks_vec").fetchone()[0]
    conn.close()
    assert count == 1
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -k "chunk" -v
```

Expected: FAIL.

- [ ] **Step 3: Implement in infrastructure/db.py**

```python
def insert_chunks(db_path: Path, source_uid: str, chunks: list[ChunkResult]) -> None:
    conn = get_connection(db_path)
    conn.executemany(
        "INSERT INTO chunks (uid, source_uid, position, content, token_count) VALUES (?, ?, ?, ?, ?)",
        [(c.uid, source_uid, c.position, c.content, c.token_count) for c in chunks],
    )
    conn.commit()
    conn.close()


def delete_chunks_for_source(db_path: Path, source_uid: str) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM chunks WHERE source_uid = ?", (source_uid,))
    conn.commit()
    conn.close()


def insert_chunk_embeddings(db_path: Path, chunk_uid: str, embedding: list[float]) -> None:
    import sqlite_vec
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO chunks_vec(chunk_uid, embedding) VALUES (?, ?)",
        (chunk_uid, sqlite_vec.serialize_float32(embedding)),
    )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run all tests**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/db.py tests/infrastructure/test_db.py
git commit -m "feat: db chunks CRUD + chunk vector insertion"
```

---

## Task 11: infrastructure/db.py — note vectors + search

**Files:**
- Modify: `infrastructure/db.py`
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Add vector + search tests**

Append to `tests/infrastructure/test_db.py`:

```python
# ---- Note vectors + search ----

def test_insert_and_delete_note_embedding(tmp_db):
    from infrastructure.db import insert_note, insert_note_embedding, delete_note_embedding, get_connection
    insert_note(tmp_db, _make_note())
    insert_note_embedding(tmp_db, "note-uid-1", [0.1] * 768)
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM notes_vec").fetchone()[0]
    assert count == 1
    conn.close()
    delete_note_embedding(tmp_db, "note-uid-1")
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM notes_vec").fetchone()[0]
    conn.close()
    assert count == 0


def test_search_chunks_returns_results(tmp_db):
    from infrastructure.db import (
        insert_source, insert_chunks, insert_chunk_embeddings, search_chunks
    )
    source = _make_source()
    insert_source(tmp_db, source)
    chunks = _make_chunks()
    insert_chunks(tmp_db, "src-uid-1", chunks)
    for chunk in chunks:
        insert_chunk_embeddings(tmp_db, chunk.uid, [0.1] * 768)

    query = [0.1] * 768
    results = search_chunks(tmp_db, query, filters=None, limit=5)
    assert len(results) == 3
    assert all(r.distance >= 0 for r in results)
    assert results[0].content.startswith("content")


def test_search_notes_returns_results(tmp_db):
    from infrastructure.db import insert_note, insert_note_embedding, search_notes
    insert_note(tmp_db, _make_note())
    insert_note_embedding(tmp_db, "note-uid-1", [0.1] * 768)
    results = search_notes(tmp_db, [0.1] * 768, filters=None, limit=5)
    assert len(results) == 1
    assert results[0].title == "Test Note"
    assert results[0].note_uid == "note-uid-1"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -k "embedding or search" -v
```

Expected: FAIL.

- [ ] **Step 3: Implement in infrastructure/db.py**

```python
def insert_note_embedding(db_path: Path, note_uid: str, embedding: list[float]) -> None:
    import sqlite_vec
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO notes_vec(note_uid, embedding) VALUES (?, ?)",
        (note_uid, sqlite_vec.serialize_float32(embedding)),
    )
    conn.commit()
    conn.close()


def delete_note_embedding(db_path: Path, note_uid: str) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM notes_vec WHERE note_uid = ?", (note_uid,))
    conn.commit()
    conn.close()


def search_chunks(
    db_path: Path,
    query_embedding: list[float],
    filters: SearchFilters | None,
    limit: int,
) -> list[SearchResult]:
    import sqlite_vec
    conn = get_connection(db_path)
    embedding_bytes = sqlite_vec.serialize_float32(query_embedding)
    rows = conn.execute(
        """SELECT c.content, c.uid AS chunk_uid, c.source_uid, s.title, cv.distance
           FROM chunks_vec cv
           JOIN chunks c ON c.uid = cv.chunk_uid
           JOIN sources s ON s.uid = c.source_uid
           WHERE cv.embedding MATCH ?
           ORDER BY cv.distance
           LIMIT ?""",
        (embedding_bytes, limit),
    ).fetchall()
    conn.close()
    return [
        SearchResult(
            chunk_uid=row["chunk_uid"],
            source_uid=row["source_uid"],
            content=row["content"],
            title=row["title"],
            distance=row["distance"],
        )
        for row in rows
    ]


def search_notes(
    db_path: Path,
    query_embedding: list[float],
    filters: SearchFilters | None,
    limit: int,
) -> list[SearchResult]:
    import sqlite_vec
    conn = get_connection(db_path)
    embedding_bytes = sqlite_vec.serialize_float32(query_embedding)
    rows = conn.execute(
        """SELECT n.uid AS note_uid, n.source_uid, n.title, n.docstring AS content, nv.distance
           FROM notes_vec nv
           JOIN notes n ON n.uid = nv.note_uid
           WHERE nv.embedding MATCH ?
           ORDER BY nv.distance
           LIMIT ?""",
        (embedding_bytes, limit),
    ).fetchall()
    conn.close()
    return [
        SearchResult(
            note_uid=row["note_uid"],
            source_uid=row["source_uid"],
            content=row["content"] or "",
            title=row["title"],
            distance=row["distance"],
        )
        for row in rows
    ]
```

- [ ] **Step 4: Run all tests**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/db.py tests/infrastructure/test_db.py
git commit -m "feat: db note vectors + search_chunks + search_notes"
```

---

## Task 12: infrastructure/db.py — tags + tool_logs

**Files:**
- Modify: `infrastructure/db.py`
- Modify: `tests/infrastructure/test_db.py`

- [ ] **Step 1: Add tags + tool_logs tests**

Append to `tests/infrastructure/test_db.py`:

```python
# ---- Tags ----

def test_upsert_tags_creates_new(tmp_db):
    from infrastructure.db import upsert_tags, get_connection
    tag_uids = upsert_tags(tmp_db, ["bitcoin", "decentralisation"], "fr")
    assert len(tag_uids) == 2
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    conn.close()
    assert count == 2


def test_upsert_tags_idempotent(tmp_db):
    from infrastructure.db import upsert_tags, get_connection
    upsert_tags(tmp_db, ["bitcoin"], "fr")
    upsert_tags(tmp_db, ["bitcoin", "ethereum"], "fr")
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    conn.close()
    assert count == 2  # no duplicate


def test_set_note_tags_full_replace(tmp_db):
    from infrastructure.db import insert_note, set_note_tags, get_connection
    insert_note(tmp_db, _make_note())
    set_note_tags(tmp_db, "note-uid-1", ["bitcoin", "crypto"])
    conn = get_connection(tmp_db)
    count1 = conn.execute(
        "SELECT COUNT(*) FROM note_tags WHERE note_uid = 'note-uid-1'"
    ).fetchone()[0]
    conn.close()
    assert count1 == 2

    # Full replace: second call removes old tags
    set_note_tags(tmp_db, "note-uid-1", ["monnaie"])
    conn = get_connection(tmp_db)
    count2 = conn.execute(
        "SELECT COUNT(*) FROM note_tags WHERE note_uid = 'note-uid-1'"
    ).fetchone()[0]
    conn.close()
    assert count2 == 1


# ---- Tool logs ----

def test_insert_tool_log(tmp_db):
    from infrastructure.db import insert_tool_log, get_connection
    insert_tool_log(tmp_db, "transcribe", '{"file": "test.mp3"}', '{"text": "hello"}', 250, "success")
    conn = get_connection(tmp_db)
    row = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'transcribe'").fetchone()
    conn.close()
    assert row["status"] == "success"
    assert row["duration_ms"] == 250


def test_insert_tool_log_failed(tmp_db):
    from infrastructure.db import insert_tool_log, get_connection
    insert_tool_log(tmp_db, "embed", None, None, 100, "failed", "Connection refused")
    conn = get_connection(tmp_db)
    row = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'embed'").fetchone()
    conn.close()
    assert row["status"] == "failed"
    assert "Connection refused" in row["error"]
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_db.py -k "tag or log" -v
```

Expected: FAIL.

- [ ] **Step 3: Implement in infrastructure/db.py**

```python
def upsert_tags(db_path: Path, names: list[str], language: str) -> list[str]:
    from datetime import date
    from core.uid import generate_uid
    conn = get_connection(db_path)
    today = date.today().isoformat()
    tag_uids = []
    for name in names:
        existing = conn.execute("SELECT uid FROM tags WHERE name = ?", (name,)).fetchone()
        if existing:
            tag_uids.append(existing["uid"])
        else:
            uid = generate_uid()
            conn.execute(
                "INSERT INTO tags (uid, name, language, date_created) VALUES (?, ?, ?, ?)",
                (uid, name, language, today),
            )
            tag_uids.append(uid)
    conn.commit()
    conn.close()
    return tag_uids


def set_note_tags(db_path: Path, note_uid: str, tag_names: list[str]) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM note_tags WHERE note_uid = ?", (note_uid,))
    conn.commit()
    conn.close()
    if not tag_names:
        return
    tag_uids = upsert_tags(db_path, tag_names, "fr")
    conn = get_connection(db_path)
    conn.executemany(
        "INSERT INTO note_tags (note_uid, tag_uid) VALUES (?, ?)",
        [(note_uid, tag_uid) for tag_uid in tag_uids],
    )
    conn.commit()
    conn.close()


def insert_tool_log(
    db_path: Path,
    tool_name: str,
    input_json: str | None,
    output_json: str | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
) -> None:
    from core.uid import generate_uid
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO tool_logs (uid, tool_name, input_json, output_json, duration_ms, status, error)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (generate_uid(), tool_name, input_json, output_json, duration_ms, status, error),
    )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: all tests PASS, including the logging DB tests from Task 6.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/db.py tests/infrastructure/test_db.py
git commit -m "feat: db tags + tool_logs — upsert_tags, set_note_tags, insert_tool_log"
```

---

## Task 13: infrastructure/embedding_provider.py — embed()

**Files:**
- Modify: `infrastructure/embedding_provider.py`
- Create: `tests/infrastructure/test_embedding_provider.py`

v1 scope: Ollama only. OpenAI raises `NotImplementedError` (blocked behind spec warning about embedding model mismatch). See spec section 4.2 warning before adding providers.

- [ ] **Step 1: Write the failing tests**

Create `tests/infrastructure/test_embedding_provider.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def _ollama_settings(tmp_settings):
    """tmp_settings already uses ollama provider."""
    return tmp_settings


def test_embed_ollama_returns_vector(tmp_settings):
    from infrastructure.embedding_provider import embed

    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.1] * 768}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = embed("hello world", tmp_settings)

    assert isinstance(result, list)
    assert len(result) == 768
    assert result[0] == pytest.approx(0.1)

    call_kwargs = mock_post.call_args
    assert "nomic-embed-text" in str(call_kwargs)
    assert "hello world" in str(call_kwargs)


def test_embed_ollama_uses_correct_url(tmp_settings):
    from infrastructure.embedding_provider import embed

    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.0] * 768}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        embed("test", tmp_settings)

    url = mock_post.call_args[0][0]
    assert url == "http://localhost:11434/api/embeddings"


def test_embed_openai_raises_not_implemented(tmp_settings):
    from infrastructure.embedding_provider import embed
    from core.config import UserConfig, EmbeddingUserConfig, LLMUserConfig, VaultUserConfig

    # Override provider to openai
    openai_settings = tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"embedding": EmbeddingUserConfig(provider="openai", model="text-embedding-3-small")}
        )}
    )
    with pytest.raises(NotImplementedError):
        embed("test", openai_settings)


def test_embed_unknown_provider_raises(tmp_settings):
    from infrastructure.embedding_provider import embed
    from core.config import EmbeddingUserConfig

    bad_settings = tmp_settings.model_copy(
        update={"user": tmp_settings.user.model_copy(
            update={"embedding": EmbeddingUserConfig(provider="unknown", model="x")}
        )}
    )
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        embed("test", bad_settings)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_embedding_provider.py -v
```

Expected: FAIL — `embed` is not implemented.

- [ ] **Step 3: Implement embed() in infrastructure/embedding_provider.py**

Replace the stub:

```python
"""
Embedding provider for EgoVault v2.

Dispatches to Ollama (v1) or OpenAI (future, raises NotImplementedError).
See spec section 4.2 warning before adding new providers:
changing the embedding model requires full re-embedding of all chunks + notes.
"""

import requests
from core.config import Settings


def embed(text: str, settings: Settings) -> list[float]:
    """
    Embed text using the configured provider.
    Returns a list of floats (dimension depends on model).
    Raises NotImplementedError for providers not yet implemented in v1.
    """
    provider = settings.user.embedding.provider
    model = settings.user.embedding.model

    if provider == "ollama":
        return _embed_ollama(text, model, settings.install.providers.ollama_base_url)
    elif provider == "openai":
        raise NotImplementedError(
            "OpenAI embedding is not implemented in v1. "
            "See spec section 4.2 for prerequisites before adding new providers."
        )
    else:
        raise ValueError(f"Unknown embedding provider: '{provider}'. Supported: ollama")


def _embed_ollama(text: str, model: str, base_url: str) -> list[float]:
    url = f"{base_url}/api/embeddings"
    response = requests.post(url, json={"model": model, "prompt": text}, timeout=60)
    response.raise_for_status()
    return response.json()["embedding"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_embedding_provider.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/embedding_provider.py tests/infrastructure/test_embedding_provider.py
git commit -m "feat: embedding_provider.embed() — Ollama v1 (OpenAI stub raises NotImplementedError)"
```

---

## Task 14: infrastructure/vault_writer.py — write_note()

**Files:**
- Modify: `infrastructure/vault_writer.py`
- Create: `tests/infrastructure/test_vault_writer.py`

Generates Markdown files with SYSTEM/CONTENT frontmatter zones (spec section 5.3).

- [ ] **Step 1: Write the failing tests**

Create `tests/infrastructure/test_vault_writer.py`:

```python
import pytest
from pathlib import Path
from core.schemas import Note


def _make_note(**overrides):
    data = {
        "uid": "note-uid-1",
        "source_uid": "src-uid-abc",
        "slug": "test-note",
        "note_type": "synthese",
        "source_type": "youtube",
        "generation_template": "standard",
        "rating": 4,
        "sync_status": "synced",
        "title": "Test Note Title",
        "docstring": "What, why, thesis.",
        "body": "## Section\n\nBody content here.",
        "url": None,
        "date_created": "2026-03-26",
        "date_modified": "2026-03-26",
        "tags": ["bitcoin", "decentralisation"],
    }
    data.update(overrides)
    return Note(**data)


def test_write_note_creates_file(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    path = write_note(note, tmp_path)
    assert path.exists()
    assert path.name == "test-note.md"


def test_frontmatter_system_zone(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    path = write_note(note, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "uid: note-uid-1" in content
    assert "date_created: 2026-03-26" in content
    assert "source_uid: src-uid-abc" in content
    assert "generation_template: standard" in content
    assert "DO NOT EDIT" in content


def test_frontmatter_content_zone(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    path = write_note(note, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "date_modified: 2026-03-26" in content
    assert "note_type: synthese" in content
    assert "source_type: youtube" in content
    assert "rating: 4" in content
    assert "bitcoin" in content
    assert "decentralisation" in content


def test_frontmatter_system_before_content(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    uid_pos = content.index("uid:")
    date_mod_pos = content.index("date_modified:")
    assert uid_pos < date_mod_pos  # SYSTEM before CONTENT


def test_body_contains_h1_title(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    assert "# Test Note Title" in content


def test_body_contains_docstring_quote(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    assert "> What, why, thesis." in content


def test_body_contains_note_body(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    content = write_note(note, tmp_path).read_text()
    assert "## Section" in content
    assert "Body content here." in content


def test_null_fields_not_in_frontmatter(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note(
        source_uid=None, generation_template=None, rating=None, url=None, source_type=None
    )
    content = write_note(note, tmp_path).read_text()
    assert "source_uid:" not in content
    assert "generation_template:" not in content
    assert "rating:" not in content
    assert "url:" not in content


def test_write_note_overwrites_existing(tmp_path):
    from infrastructure.vault_writer import write_note
    note = _make_note()
    write_note(note, tmp_path)
    note2 = _make_note(title="Updated Title", body="New body.")
    write_note(note2, tmp_path)
    content = (tmp_path / "test-note.md").read_text()
    assert "Updated Title" in content
    assert "New body." in content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/python -m pytest tests/infrastructure/test_vault_writer.py -v
```

Expected: FAIL — `write_note` is not implemented.

- [ ] **Step 3: Implement infrastructure/vault_writer.py**

Replace the stub file completely:

```python
"""
Generates Markdown files from Note records.

Frontmatter has two zones (spec section 5.3):
  SYSTEM — uid, date_created, source_uid, generation_template (immutable, watcher ignores)
  CONTENT — date_modified, note_type, source_type, rating, tags, url (watcher syncs to DB)
"""

from pathlib import Path
from core.schemas import Note


def write_note(note: Note, vault_path: Path) -> Path:
    """Write note to <vault_path>/<slug>.md. Returns the written file path."""
    frontmatter = _build_frontmatter(note)
    body_section = _build_body(note)
    content = frontmatter + "\n" + body_section
    file_path = vault_path / f"{note.slug}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _build_frontmatter(note: Note) -> str:
    lines = ["---"]

    # SYSTEM zone
    lines.append("# SYSTEM — generated by vault_writer.py")
    lines.append("# DO NOT EDIT — changes will be ignored by sync watcher")
    lines.append(f"uid: {note.uid}")
    lines.append(f"date_created: {note.date_created}")
    if note.source_uid is not None:
        lines.append(f"source_uid: {note.source_uid}")
    if note.generation_template is not None:
        lines.append(f"generation_template: {note.generation_template}")

    lines.append("")

    # CONTENT zone
    lines.append("# CONTENT — editable in Obsidian")
    lines.append("# Changes synced back to DB if uid is intact")
    lines.append(f"date_modified: {note.date_modified}")
    if note.note_type is not None:
        lines.append(f"note_type: {note.note_type}")
    if note.source_type is not None:
        lines.append(f"source_type: {note.source_type}")
    if note.rating is not None:
        lines.append(f"rating: {note.rating}")
    if note.tags:
        lines.append(f"tags: [{', '.join(note.tags)}]")
    if note.url is not None:
        lines.append(f"url: {note.url}")

    lines.append("---")
    return "\n".join(lines)


def _build_body(note: Note) -> str:
    parts = [f"# {note.title}", ""]
    if note.docstring:
        parts.append(f"> {note.docstring}")
        parts.append("")
    parts.append(note.body)
    return "\n".join(parts)
```

- [ ] **Step 4: Run all tests**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/vault_writer.py tests/infrastructure/test_vault_writer.py
git commit -m "feat: vault_writer.write_note() — Markdown + SYSTEM/CONTENT frontmatter"
```

---

## Task 15: Final validation

- [ ] **Step 1: Run the complete test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short
```

Expected: all tests PASS, zero failures.

- [ ] **Step 2: Verify imports are clean (no circular deps)**

```bash
.venv/Scripts/python -c "
from core.config import load_settings
from core.schemas import Note, Source
from core.uid import generate_uid, make_slug
from core import logging as ev_logging
from infrastructure.db import init_db
from infrastructure.embedding_provider import embed
from infrastructure.vault_writer import write_note
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: Plan 1 (Foundation) complete — core/ + infrastructure/ implemented + tested"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|---|---|
| 1.2 Slug derivation (make_slug 6 rules) | Task 2 |
| 5.0 Slug collision (make_unique_slug) | Task 2 |
| 5.2 NoteContentInput.tags validator | Task 3 |
| 5.2 validate_taxonomy (runtime, not hardcoded) | Task 4 |
| 3.1 Three config files + load_settings | Task 5 |
| 6.3 @loggable decorator + _write_log | Task 6 |
| 4.2 DB schema (all tables + sqlite-vec) | Task 7 |
| 4.2 sources CRUD | Task 8 |
| 4.2 notes CRUD | Task 9 |
| 4.2 chunks + chunks_vec | Task 10 |
| 4.2 notes_vec + search patterns A1/A2/B | Task 11 |
| 4.2 tags + tool_logs | Task 12 |
| embedding_provider (Ollama only, spec warning) | Task 13 |
| 5.3 Frontmatter SYSTEM/CONTENT zones | Task 14 |

**Not in this plan (correct — belong to Plan 2/3):**
- tools/ atomic functions
- workflows/ orchestration
- mcp/server.py MCP protocol

**Gaps:** None identified. All spec sections 1–6 relevant to foundation are covered.
