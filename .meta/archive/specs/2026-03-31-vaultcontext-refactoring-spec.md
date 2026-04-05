# VaultContext Refactoring — Specification

**Date:** 2026-03-31
**Status:** ACTIVE
**Supersedes:** Nothing (new feature)
**Brainstorm notes:** `.meta/specs/2026-03-31-vaultcontext-refactoring-notes.md`
**Phase:** 2 — SPEC

---

## 1. What and why

### What

Introduce `VaultContext` — a dataclass that holds all infrastructure dependencies (DB access,
embedding function, LLM function, note writer). Tools receive `ctx: VaultContext` instead of
importing `infrastructure/` directly.

### Why

- **22 late imports** from `infrastructure/` in `tools/` violate G4 (architecture boundaries)
- Tools are coupled to concrete implementations (SQLite, Ollama, Anthropic)
- Testing requires module-level mocking instead of simple dependency injection
- Inconsistent with portfolio-grade architecture goal

### What this is NOT

- Not a new feature — pure refactor, identical behavior
- Not a god object — holds infrastructure *access*, not business state
- Not PostgreSQL support — just opens the door

---

## 2. VaultContext definition

Lives in `core/context.py` (core/ imports nothing from the project).

### Protocols (type-safe callables)

```python
class EmbedFn(Protocol):
    """Convert text to an embedding vector."""
    def __call__(self, text: str) -> list[float]: ...

class GenerateFn(Protocol):
    """Generate structured note content via LLM."""
    def __call__(self, source_content: str, source_metadata: dict,
                 template_name: str) -> NoteContentInput: ...

class WriteNoteFn(Protocol):
    """Write a Note as a markdown file. Return the file path."""
    def __call__(self, note: Note, vault_path: Path) -> Path: ...
```

### The dataclass

```python
@dataclass
class VaultContext:
    settings: Settings              # full config
    db: VaultDB                     # facade over vault.db functions
    system_db_path: Path            # path to .system.db
    embed: EmbedFn                  # text -> embedding vector
    generate: GenerateFn | None     # LLM generation (None = not configured)
    write_note: WriteNoteFn         # Note -> markdown file
    vault_path: Path                # where to write notes
    media_path: Path                # where to store media
```

---

## 3. VaultDB facade

Lives in `infrastructure/vault_db.py`. Thin wrapper: binds `db_path`, delegates to `db.py`.

Each method is one line. No SQL, no logic, no new behavior. `db.py` stays untouched.

### Methods needed (derived from actual tool usage)

**Sources:**
- `get_source(uid: str) -> Source | None`
- `update_source_status(uid: str, status: str) -> None`
- `soft_delete_source(uid: str) -> None`
- `hard_delete_source(uid: str) -> None`
- `restore_source(uid: str) -> str`
- `list_sources_pending_deletion() -> list[Source]`

**Notes:**
- `get_note(uid: str) -> Note | None`
- `get_note_by_source(source_uid: str) -> Note | None`
- `insert_note(note: Note) -> None`
- `update_note(uid: str, fields: dict) -> None`
- `soft_delete_note(uid: str) -> None`
- `hard_delete_note(uid: str) -> None`
- `restore_note(uid: str) -> str`
- `list_notes_pending_deletion() -> list[Note]`
- `orphan_notes_for_source(source_uid: str) -> None`

**Chunks & embeddings:**
- `delete_chunks_for_source(source_uid: str) -> None`
- `delete_chunk_embeddings_for_source(uid: str) -> None`
- `insert_note_embedding(note_uid: str, embedding: list[float]) -> None`
- `delete_note_embedding(note_uid: str) -> None`

**Search:**
- `search_chunks(query_embedding: list[float], filters: SearchFilters | None, limit: int) -> list[SearchResult]`
- `search_notes(query_embedding: list[float], filters: SearchFilters | None, limit: int) -> list[SearchResult]`

**Utility:**
- `get_existing_slugs(table: str) -> set[str]`

**Total: 22 methods**, all one-line delegations.

### Why `get_existing_slugs` instead of `get_vault_connection`

Two tools (`generate_note_from_source`, `mermaid`) currently use raw `get_vault_connection()`
to run ad-hoc SQL queries. These must be replaced by proper VaultDB methods:
- `generate_note_from_source` uses it to get existing note slugs → `get_existing_slugs("notes")`
- `mermaid` uses it for graph queries → dedicated method or refactored (addressed in plan)

Tools must NEVER get a raw connection. That defeats the purpose of the facade.

---

## 4. build_context() factory

Lives in `infrastructure/context.py`. Knows all providers. Builds VaultContext.

```python
def build_context(settings: Settings) -> VaultContext:
    db = VaultDB(settings.vault_db_path)

    embed_fn = lambda text: embedding_provider.embed(text, settings)

    generate_fn = None
    if _llm_is_configured(settings):
        generate_fn = lambda content, metadata, template: (
            llm_provider.generate_note_content(content, metadata, template, settings)
        )

    write_fn = lambda note, vault_path: vault_writer.write_note(note, vault_path)

    return VaultContext(
        settings=settings,
        db=db,
        system_db_path=settings.system_db_path,
        embed=embed_fn,
        generate=generate_fn,
        write_note=write_fn,
        vault_path=settings.vault_path,
        media_path=settings.media_path,
    )
```

### `_llm_is_configured()` helper

Checks if the LLM provider has valid credentials. Extracted from current logic scattered
in workflows (where it's duplicated).

---

## 5. Tool signature changes

### Before

```python
@loggable("search")
def search(query: str, settings: Settings, filters=None, mode="chunks", limit=5):
    from infrastructure.db import search_chunks, search_notes      # late import
    from infrastructure.embedding_provider import embed             # late import
    embedding = embed(query, settings)
    return search_chunks(settings.vault_db_path, embedding, ...)
```

### After

```python
@loggable("search")
def search(query: str, ctx: VaultContext, filters=None, mode="chunks", limit=5):
    embedding = ctx.embed(query)
    return ctx.db.search_chunks(embedding, ...)
```

**Changes per tool:**
1. Replace `settings: Settings` with `ctx: VaultContext` in signature
2. Remove all `from infrastructure.*` late imports
3. Replace `embed(text, settings)` with `ctx.embed(text)`
4. Replace `generate_note_content(...)` with `ctx.generate(...)`
5. Replace `write_note(note, path)` with `ctx.write_note(note, ctx.vault_path)`
6. Replace `func(settings.vault_db_path, ...)` with `ctx.db.func(...)`
7. Replace `settings.xxx` with `ctx.settings.xxx` for config access

---

## 6. Surface changes

### MCP (`mcp/server.py`)

Currently: `settings = load_settings()` at module level.
After: `ctx = build_context(load_settings())` at module level.

Tool wrappers change from:
```python
results = _search_tool(query, settings, ...)
```
To:
```python
results = _search_tool(query, ctx, ...)
```

Also: move `create_note` business logic (45 lines of slug generation, UID creation)
out of `server.py` into `tools/vault/create_note.py`. This resolves the G11 violation.

### API (`api/main.py`, all routers)

Currently: `app.state.settings = settings`
After: `app.state.ctx = build_context(settings)`

Routers change from:
```python
settings = request.app.state.settings
```
To:
```python
ctx = request.app.state.ctx
```

Also: move `approve_note` business logic out of `api/routers/notes.py` into a tool.

### CLI (`cli/commands/*.py`)

Currently: `settings = _load_settings()`
After: `ctx = _build_context()` (helper that calls `load_settings()` then `build_context()`)

### Workflows (`workflows/ingest_*.py`)

Currently: `def ingest_youtube(url, settings, ...)`
After: `def ingest_youtube(url, ctx, ...)`

Workflows already import tools and infrastructure directly. After refactor, they import
tools only (tools use `ctx.db` instead of importing `infrastructure/db`).

Workflow-level DB operations (insert_source, insert_chunks, update_source_status, etc.)
also go through `ctx.db`.

---

## 7. core/logging.py debt

**Problem:** `core/logging.py` imports `infrastructure.db.get_system_connection` inside
`_write_log()`. This is a circular dependency (core → infrastructure).

**Solution:** Callback injection at startup.

```python
# core/logging.py
_log_writer: Callable | None = None

def configure(log_writer: Callable) -> None:
    global _log_writer
    _log_writer = log_writer

def _write_log(...):
    if _log_writer:
        _log_writer(tool_name, input_json, output_json, duration_ms, status, error)
```

```python
# api/main.py (at startup)
import core.logging as log_mod
from infrastructure.db import insert_tool_log, get_system_connection

def _log_to_db(tool_name, input_json, output_json, duration_ms, status, error):
    insert_tool_log(settings.system_db_path, tool_name, ...)

log_mod.configure(_log_to_db)
```

This eliminates the only core/ → infrastructure/ import.

---

## 8. Test strategy

### Test fixture: `make_test_context()`

In `tests/conftest.py`:

```python
@pytest.fixture
def ctx(tmp_path, settings):
    """Build a VaultContext for testing with mocked providers."""
    from infrastructure.vault_db import VaultDB
    db_path = tmp_path / "vault.db"
    init_db(db_path, dims=settings.system.embedding.dims)

    return VaultContext(
        settings=settings,
        db=VaultDB(db_path),
        system_db_path=tmp_path / ".system.db",
        embed=lambda text: [0.0] * settings.system.embedding.dims,
        generate=None,
        write_note=lambda note, path: path / f"{note.slug}.md",
        vault_path=tmp_path / "vault",
        media_path=tmp_path / "media",
    )
```

### Test migration

Every test that currently passes `settings` to a tool must pass `ctx` instead.
The `ctx` fixture provides mock embed/generate/write_note by default.

Tests that need specific provider behavior override the fixture:
```python
def test_search_with_real_embedding(ctx):
    ctx.embed = lambda text: real_embed(text)  # override for this test
```

---

## 9. File map — complete impact analysis

### New files (4)

| File | Role |
|------|------|
| `core/context.py` | VaultContext dataclass + Protocols (EmbedFn, GenerateFn, WriteNoteFn) |
| `infrastructure/vault_db.py` | VaultDB facade (22 one-line methods wrapping db.py) |
| `infrastructure/context.py` | `build_context()` factory |
| `tests/infrastructure/test_vault_db.py` | Tests for VaultDB facade |

### Modified files — tools (14 files)

All receive `ctx: VaultContext` instead of `settings: Settings`, remove late imports.

| File | Infrastructure imports removed |
|------|-------------------------------|
| `tools/vault/search.py` | `db.search_chunks`, `db.search_notes` |
| `tools/vault/create_note.py` | `db.insert_note`, `db.get_source`, `db.insert_note_embedding`, `embedding_provider.embed`, `vault_writer.write_note` |
| `tools/vault/update_note.py` | `db.get_note`, `db.update_note`, `db.delete_note_embedding`, `db.insert_note_embedding`, `embedding_provider.embed`, `vault_writer.write_note` |
| `tools/vault/generate_note_from_source.py` | `db.get_source`, `db.get_note_by_source`, `db.get_note`, `db.get_vault_connection`, `db.insert_note`, `db.insert_note_embedding`, `embedding_provider.embed`, `llm_provider.generate_note_content`, `vault_writer.write_note` |
| `tools/vault/delete_note.py` | `db.get_note`, `db.soft_delete_note`, `db.hard_delete_note`, `db.delete_note_embedding` |
| `tools/vault/delete_source.py` | `db.get_source`, `db.soft_delete_source`, `db.hard_delete_source`, `db.orphan_notes_for_source`, `db.delete_chunk_embeddings_for_source`, `db.delete_chunks_for_source` |
| `tools/vault/finalize_source.py` | `db.get_source`, `db.update_source_status` |
| `tools/vault/purge.py` | `db.list_notes_pending_deletion`, `db.list_sources_pending_deletion`, `db.delete_note_embedding`, `db.hard_delete_note`, `db.orphan_notes_for_source`, `db.delete_chunk_embeddings_for_source`, `db.delete_chunks_for_source`, `db.hard_delete_source` |
| `tools/vault/restore_note.py` | `db.get_note`, `db.restore_note` |
| `tools/vault/restore_source.py` | `db.get_source`, `db.restore_source` |
| `tools/text/embed.py` | `embedding_provider.embed` |
| `tools/text/embed_note.py` | `db.get_note`, `db.delete_note_embedding`, `db.insert_note_embedding`, `db.update_note` |
| `tools/export/mermaid.py` | `db.get_vault_connection` |
| `tools/export/typst.py` | `db.get_note` |

### Modified files — surfaces (8 files)

| File | Change |
|------|--------|
| `mcp/server.py` | Build `ctx` at module level, pass to tools, move create_note logic out |
| `api/main.py` | Build `ctx` in lifespan, store in `app.state.ctx` |
| `api/routers/search.py` | Use `ctx` from app state |
| `api/routers/notes.py` | Use `ctx`, move approve_note logic to tool |
| `api/routers/ingest.py` | Use `ctx`, pass to workflows |
| `api/routers/sources.py` | Use `ctx` |
| `api/routers/vault.py` | Use `ctx` |
| `api/routers/jobs.py` | Use `ctx.system_db_path` |

### Modified files — CLI (6 files)

| File | Change |
|------|--------|
| `cli/commands/search.py` | Build `ctx`, pass to tool |
| `cli/commands/notes.py` | Build `ctx`, pass to tool |
| `cli/commands/sources.py` | Build `ctx`, pass to tool |
| `cli/commands/ingest.py` | Build `ctx`, pass to workflow |
| `cli/commands/purge.py` | Build `ctx`, pass to tool |
| `cli/commands/status.py` | Build `ctx`, pass to tool |

### Modified files — workflows (3 files)

| File | Change |
|------|--------|
| `workflows/ingest_youtube.py` | Receive `ctx`, use `ctx.db` + `ctx.embed`, stop importing infrastructure/ |
| `workflows/ingest_audio.py` | Same |
| `workflows/ingest_pdf.py` | Same |

### Modified files — core (1 file)

| File | Change |
|------|--------|
| `core/logging.py` | Replace infrastructure import with callback injection |

### Modified files — tests (~25 files)

All test files that call tools or workflows must pass `ctx` fixture instead of `settings`.

| Test area | Files affected |
|-----------|---------------|
| `tests/tools/vault/` | 10 files (test_search, test_create_note, etc.) |
| `tests/tools/text/` | 3 files (test_embed, test_embed_note, test_chunk) |
| `tests/tools/export/` | 2 files (test_mermaid, test_typst) |
| `tests/workflows/` | 3 files |
| `tests/mcp/` | 1 file |
| `tests/api/` | ~6 files (those that test tool integration) |
| `tests/conftest.py` | Add `ctx` fixture |

### Unchanged files

| File | Why unchanged |
|------|--------------|
| `infrastructure/db.py` | VaultDB wraps it, doesn't modify it |
| `infrastructure/embedding_provider.py` | build_context() calls it, not modified |
| `infrastructure/llm_provider.py` | build_context() calls it, not modified |
| `infrastructure/vault_writer.py` | build_context() calls it, not modified |
| `core/config.py` | Settings unchanged |
| `core/schemas.py` | Schemas unchanged |
| `core/errors.py` | Errors unchanged |
| `tools/media/*` | No infrastructure imports (transcribe uses whisper directly) |
| `tools/text/chunk.py` | No infrastructure imports |
| `tools/text/summarize.py` | No infrastructure imports |

---

## 10. What changes and what doesn't

### Changes

- Tool signatures: `settings: Settings` → `ctx: VaultContext`
- Tool bodies: late imports → `ctx.db`, `ctx.embed`, `ctx.generate`, `ctx.write_note`
- Surfaces: `load_settings()` → `build_context(load_settings())`
- Workflows: `settings` param → `ctx` param
- Tests: `settings` fixture → `ctx` fixture
- core/logging.py: infrastructure import → callback injection

### Does NOT change

- `infrastructure/db.py` — all 40+ functions stay exactly as-is
- `infrastructure/embedding_provider.py` — untouched
- `infrastructure/llm_provider.py` — untouched
- `infrastructure/vault_writer.py` — untouched
- `core/config.py`, `core/schemas.py` — untouched
- All config files — untouched
- Tool behavior — identical input/output, only the plumbing changes
- `@loggable` decorator — still works (wraps the tool function as before)

---

## 11. Migration order

Incremental (Strategy C from brainstorm). Each step = one commit.

1. **Foundation:** Create `core/context.py`, `infrastructure/vault_db.py`, `infrastructure/context.py`
2. **Test fixture:** Add `ctx` fixture to `tests/conftest.py`
3. **Logging debt:** Fix `core/logging.py` callback pattern
4. **Surfaces:** Adapt MCP, API, CLI to build and pass VaultContext
5. **Tools — vault/ group:** Migrate 10 vault tools (one commit per tool or per logical group)
6. **Tools — text/ group:** Migrate embed.py, embed_note.py
7. **Tools — export/ group:** Migrate mermaid.py, typst.py
8. **Workflows:** Migrate ingest_youtube, ingest_audio, ingest_pdf
9. **Cleanup:** Remove any remaining late imports, verify G4 compliance

Tests run after each step. No step proceeds if tests fail.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Breaking 367 tests during migration | Incremental: each step tested independently |
| VaultDB out of sync with db.py | VaultDB tests verify delegation works |
| MCP module-level context stale in tests | Same pattern as current Settings: test patches `ctx` |
| Tool accidentally uses `settings` instead of `ctx.settings` | Grep for `settings:.*Settings` after migration — must be zero in tools/ |
| `@loggable` breaks with new signature | Decorator is signature-agnostic (uses `*args, **kwargs`) |
