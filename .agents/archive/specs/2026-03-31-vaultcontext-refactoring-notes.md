# VaultContext Refactoring — Brainstorm Notes

**Date:** 2026-03-31
**Phase:** 1 — BRAINSTORM (interactive, completed)
**Participants:** User + Claude
**Next phase:** SPEC (Phase 2) — write the contract based on these decisions

---

## The problem we're solving

Every tool in `tools/` imports `infrastructure/` via late imports inside function bodies.
This violates G4 (architecture boundaries): tools should never know about infrastructure.

**Numbers:** 14 tool files, 22 late imports, touching 4 infrastructure modules:
- `infrastructure/db.py` — 12 tools import it
- `infrastructure/embedding_provider.py` — 5 tools
- `infrastructure/llm_provider.py` — 1 tool
- `infrastructure/vault_writer.py` — 3 tools

**Why it matters:**
- Tools are coupled to SQLite, Ollama, Anthropic — can't swap without touching tools
- Testing requires mocking infrastructure modules — fragile, verbose
- Import cycles risk (core/logging.py already has one)
- Violates the project's architecture-as-portfolio goal

---

## The solution: VaultContext (Direction 2)

**Analogy (validated by user):** Restaurant kitchen.
- The **chef** (workflow/surface) prepares a **workstation** (VaultContext) with fridge (DB),
  oven (embedder), supplier (LLM).
- The **cook** (tool) works on the workstation — doesn't go fetch tools himself.
- The **kitchen designer** (build_context) decides what equipment goes on the workstation.

**What VaultContext is:** A dataclass holding infrastructure *access* (functions, facades).
**What VaultContext is NOT:** A god object. It holds no business state. Tools still receive
their domain inputs (text, chunks, UIDs) as separate parameters.

---

## Decisions with trade-offs

### Decision 1 — `db_path` in VaultContext (not a connection)

**Chosen:** Store `db_path: Path` in VaultContext. Tools pass it to DB functions.

**Why not a connection object?**

| Aspect | db_path (chosen) | Connection object |
|--------|-------------------|-------------------|
| Complexity | Zero — nothing changes in db.py | Must rewrite 40+ functions |
| Thread safety | Each call opens its own connection (safe) | Shared connection + threads = problems |
| Lifecycle | No open/close to manage | Who opens? Who closes? Who commits? |
| Upgrade path | Change db.py internals → tools don't move | Already committed to connection pattern |

**Upgrade path:** If we later want connection pooling, we change `db.py` to use an internal
pool keyed by path. Tools still pass `db_path`, `db.py` handles the rest. Zero tool changes.

**Trade-off accepted:** Slight inefficiency (repeated connection open/close). Acceptable for
a local SQLite app. Would revisit for PostgreSQL migration (but that's a much larger change).

---

### Decision 2 — Embedding as injectable callable with Protocol

**Chosen:** `embed: EmbedFn` in VaultContext, where `EmbedFn` is a Protocol in `core/`.

**How it works:**

```python
# core/context.py — the interface (in core/, imports nothing from project)
class EmbedFn(Protocol):
    def __call__(self, text: str) -> list[float]: ...

# infrastructure/context.py — the factory (in infrastructure/, knows the providers)
def build_context(settings: Settings) -> VaultContext:
    return VaultContext(
        embed=lambda text: embedding_provider.embed(text, settings),
        ...
    )

# tools/vault/search.py — the consumer (knows only core/)
def search(query: str, ctx: VaultContext, ...) -> list[SearchResult]:
    embedding = ctx.embed(query)  # doesn't know it's Ollama, OpenAI, or a mock
```

**Why callable instead of direct import?**

| Aspect | Callable (chosen) | Direct import (current) |
|--------|-------------------|------------------------|
| Decoupling | Total — tool has no idea what provider runs | Tool imports infrastructure/ |
| Testability | `ctx.embed = lambda t: [0.0]*768` — one line | Must mock module import |
| Hookability | Wrap in build_context(): cache, retry, metrics | Must modify embedding_provider.py |
| Debugging | Stack trace shows lambda (slightly less clear) | Direct function name in trace |
| Type safety | Protocol gives full type hint support | Same |

**Why Protocol instead of plain Callable type hint?**

`Callable[[str], list[float]]` works but is opaque. `EmbedFn(Protocol)` is self-documenting,
named, and can carry a docstring. It lives in `core/` (zero infra imports), so tools can
type-hint against it without violating G4.

**Hookability examples (all done in build_context(), tools never change):**
- Semantic cache: wrap embed with cache lookup
- Provider fallback: try Ollama, fall back to OpenAI
- Rate limiting: add delay between calls
- Metrics: count calls, track latency

---

### Decision 3 — LLM generation is optional (`None`)

**Chosen:** `generate: GenerateFn | None` in VaultContext.

**Context:** Only 1 tool out of ~15 uses the LLM (`generate_note_from_source`).

**How it works:**

```python
# VaultContext
generate: GenerateFn | None  # None = LLM not configured

# In the one tool that uses it:
def generate_note_from_source(source_uid: str, ctx: VaultContext, ...) -> NoteResult:
    if ctx.generate is None:
        raise ConfigError("LLM provider not configured")
    content = ctx.generate(source_content, metadata, template)
```

**Why `None` instead of always-callable-that-raises?**

| Aspect | Optional None (chosen) | Always callable |
|--------|----------------------|-----------------|
| Simplicity | Explicit — `if ctx.generate is None` | Hidden behavior in a lambda |
| Discovery | IDE shows `None` possibility, forces handling | Looks like it works, fails at runtime |
| Cost | One `if` check in one tool | A factory function that builds a raising lambda |

**Trade-off accepted:** The tool has one `if` check. If more tools use the LLM in the future,
we can revisit (switch to always-callable). But with 1/15 tools using it, the simplest
approach wins.

**Upgrade path:** If 3+ tools need the LLM, switch to always-callable pattern. Change: one
line in `build_context()` + remove `if None` checks from tools. Trivial.

---

### Decision 4 — VaultDB facade for database functions

**Context:** `infrastructure/db.py` has 40+ public functions. Tools call ~20 of them.
Three options were evaluated for how to handle this.

**Options evaluated:**

**Option 1 — All DB functions as callables in VaultContext:**
```python
ctx.insert_note(note)
ctx.get_source(uid)
ctx.search_chunks(embedding, filters, limit)
```
Rejected: VaultContext becomes a god object with 20+ fields. Violates G5 (over-engineering).

**Option 2 — VaultDB facade class (chosen):**
```python
ctx.db.get_source(uid)
ctx.db.search_chunks(embedding, filters, limit)
```
A thin class (~20 one-line methods) that wraps existing `db.py` functions. The class binds
`db_path` once so tools never need to pass it. Tools access DB via `ctx.db`, never import
`infrastructure/` directly.

**Option 3 — db_path in VaultContext, tools import db.py directly:**
```python
from infrastructure.db import search_chunks
search_chunks(ctx.db_path, embedding, filters, limit)
```
Rejected: leaves 13 infrastructure/ imports in tools (partial G4 violation). Inconsistent
with the portfolio vision — tools would use `ctx.embed()` for embedding but raw imports for DB.

**How VaultDB works (simple explanation):**

Think of it as a **receptionist**. Today, every tool walks into the building (db.py),
shows its badge (db_path), and asks for data. With VaultDB, the receptionist sits at
the workstation (VaultContext). The tool just says "get me source X" — the receptionist
already has the badge.

```python
# infrastructure/vault_db.py
class VaultDB:
    """Receptionist: binds db_path, delegates to db.py functions.
    Each method is one line. No logic, no SQL, just delegation."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def get_source(self, uid: str) -> Source | None:
        return db.get_source(self._db_path, uid)

    def search_chunks(self, embedding, filters, limit) -> list[SearchResult]:
        return db.search_chunks(self._db_path, embedding, filters, limit)

    # ~20 methods like this, one per function tools actually call
```

**What does NOT change:**
- `infrastructure/db.py` stays exactly as-is (all 40+ functions untouched)
- VaultDB just calls those functions, adding the `db_path` automatically
- No SQL in VaultDB, no logic, no new behavior

**Trade-offs:**

| Pro | Con |
|-----|-----|
| **Zero** infrastructure/ imports in tools | ~20 one-line wrapper methods to write (mechanical) |
| G4 fully resolved (not partially) | One more file in codebase |
| `ctx.db = FakeDB()` in tests — trivial mocking | Must keep facade in sync with db.py |
| Hookable: add logging, caching, metrics in facade | Thin indirection (but trivial to follow) |
| PostgreSQL upgrade = new class, same interface | |

**Why this is NOT over-engineering (G5 check):**
- Each method does exactly one thing: calls the existing db.py function with the bound db_path
- No abstraction, no generalization, no interface-for-the-sake-of-interface
- The wrapper exists because of a hard architectural rule (G4), not speculation
- 20 one-line methods in one file < 13 late imports scattered across 12 files

---

### Decision 5 — `build_context()` lives in `infrastructure/context.py`

**Chosen:** Dedicated file in `infrastructure/`.

**Why not `infrastructure/__init__.py`?**
- `__init__.py` is for package exports, not factory functions
- One file = one responsibility (consistent with rest of codebase)
- Easy to find, easy to test

---

### Decision 6 — Sequential refactoring order

**Chosen:** VaultContext first (pure refactor) → unified workflow → ingest_text

**Why sequential, not coupled?**
- VaultContext is a pure refactor: same behavior, new structure. Zero new features.
- Unified workflow will USE VaultContext, so it's cleaner to build on solid ground.
- Mixing refactor + features = debugging nightmare when something breaks.

---

### Decision 7 — Incremental migration (Strategy C)

**Chosen:** Pose the infrastructure first, then migrate tools one by one.

**The phases:**
1. Create `core/context.py` (VaultContext dataclass, Protocols for callables)
2. Create `infrastructure/vault_db.py` (VaultDB facade)
3. Create `infrastructure/context.py` (build_context factory)
4. Adapt surfaces (MCP, API, CLI) to build and pass VaultContext
5. Migrate tools one by one (each migration = one atomic commit)

**Why not big bang (all 14 tools at once)?**
- Massive PR, hard to review, hard to bisect if something breaks
- Each tool migration is independent and testable

**Why not just migrate tools without adapting surfaces first?**
- A tool needs to receive `ctx: VaultContext` from somewhere
- Surfaces are where `build_context()` is called, so they must be ready first

---

## The final VaultContext shape

```python
# core/context.py

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Fn = Function. Named Protocols for type safety and self-documentation.

class EmbedFn(Protocol):
    """Callable that converts text to an embedding vector."""
    def __call__(self, text: str) -> list[float]: ...

class GenerateFn(Protocol):
    """Callable that generates structured note content via LLM."""
    def __call__(self, source_content: str, source_metadata: dict,
                 template_name: str) -> NoteContentInput: ...

class WriteNoteFn(Protocol):
    """Callable that writes a Note as a markdown file. Returns the file path."""
    def __call__(self, note: Note, vault_path: Path) -> Path: ...

@dataclass
class VaultContext:
    settings: Settings              # full config (system + user + install)
    db: VaultDB                     # facade over vault.db functions
    system_db_path: Path            # path to .system.db
    embed: EmbedFn                  # text -> embedding vector
    generate: GenerateFn | None     # LLM generation (None if not configured)
    write_note: WriteNoteFn         # Note -> markdown file
    vault_path: Path                # where to write notes
    media_path: Path                # where to store media files
```

**Why each field exists:**

| Field | Used by | Why in context (what import it replaces) |
|-------|---------|------------------------------------------|
| `settings` | All tools (config values: chunking, taxonomy, etc.) | Was already passed — no change |
| `db` | 12 tools (CRUD, search, tags) | **Replaces** all `from infrastructure.db import ...` (13 late imports) |
| `system_db_path` | Workflows (job tracking), logging | Was `settings.system_db_path` — convenience |
| `embed` | 5 tools (search, create_note, update_note, embed_text, embed_note) | **Replaces** `from infrastructure.embedding_provider import embed` |
| `generate` | 1 tool (generate_note_from_source) | **Replaces** `from infrastructure.llm_provider import generate_note_content` |
| `write_note` | 3 tools (create_note, update_note, generate_note) | **Replaces** `from infrastructure.vault_writer import write_note` |
| `vault_path` | 3 tools (note writing) | Convenience, avoids `settings.install.paths` drilling |
| `media_path` | Media tools (transcribe, extract_audio) | Convenience, avoids `settings.install.paths` drilling |

**After this refactor, tools import ZERO modules from infrastructure/.** G4 fully resolved.

---

## Open items for spec phase

1. **core/logging.py debt** — Currently imports infrastructure/db. VaultContext doesn't solve
   this directly (logging happens outside tool context). Needs a callback pattern — spec will address.
2. **MCP constraint** — FastMCP tools can't accept arbitrary params. MCP server will hold
   the VaultContext at module level (like it holds Settings today). Spec will detail the pattern.
3. **Existing tool signatures** — `(inputs, settings) -> Result` becomes `(inputs, ctx) -> Result`.
   All surfaces and workflows must be updated. Spec will list every file to modify.
4. **Tests** — Every test that calls a tool must build a VaultContext (or use a fixture).
   Spec will define a `make_test_context()` helper.

---

## What this does NOT include

- No new features (pure refactor)
- No PostgreSQL support (just the door opened — see Future work)
- No connection pooling (VaultDB uses db_path internally, opens/closes per call)
- No changes to db.py function signatures (VaultDB wraps them as-is)
- No Protocol for VaultDB yet (plain class — Protocol added when second implementation needed)

## Future work (documented upgrade paths)

1. **db_path → connection pooling:** Currently VaultDB passes a `db_path` to db.py functions
   which each open/close a connection. If performance requires it, VaultDB can manage a pool
   internally — tools never know. Change is inside VaultDB only.

2. **SQLite → PostgreSQL:** Create `PostgresVaultDB` implementing the same methods. Add a
   Protocol in core/ at that point. `build_context()` picks the right implementation based
   on config. Tools never change.

3. **VaultDB hookability:** Add logging, caching, or metrics by wrapping methods in VaultDB.
   Example: count queries, log slow operations, cache frequent lookups. Zero tool changes.
