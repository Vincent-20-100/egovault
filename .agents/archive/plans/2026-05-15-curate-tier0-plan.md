# curate() Tier 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `curate()` — a deterministic Librarian tool that orchestrates notes→chunks search into a single stable `CuratedContext`, exposed via MCP and CLI.

**Architecture:** Pure-deterministic tier 0. `curate()` embeds the query once, searches compiled notes (tier 2), escalates to raw chunks (tier 1) only when notes are insufficient by a config-driven threshold, merges (notes first), and assembles a minimal text block. No LLM. Schema is frozen so tier 1 (future) only upgrades `synthesis` quality and fills `confidence`.

**Tech Stack:** Python 3.x, Pydantic v2, pytest, FastMCP, Typer.

**Spec:** `.meta/specs/2026-05-15-curate-tier0-spec.md`

---

## File Structure

- `core/schemas.py` — add `CuratedSource`, `CuratedContext` models
- `core/config.py` — add `CurateConfig`, wire into `SystemConfig`
- `config/system.yaml` — add `curate:` block
- `tools/vault/curate.py` — **new** — the tier 0 tool (only `core`/`ctx` deps)
- `mcp/server.py` — add `curate` MCP tool (thin wrapper)
- `cli/commands/curate.py` — **new** — CLI command (routing only)
- `cli/main.py` — register `curate` command
- `tests/tools/vault/test_curate.py` — **new** — behaviour tests
- `tests/cli/test_curate_cmd.py` — **new** — CLI smoke test
- Docs ripple: `.claude/rules/vault-usage.md`, `docs/architecture/ARCHITECTURE.md`, `PROJECT-STATUS.md`, `SESSION-CONTEXT.md`, `docs/VISION-KNOWLEDGE-COMPILER.md`

---

## Task 1: CuratedContext schema

**Files:**
- Modify: `core/schemas.py` (after `SearchFilters`, ~line 194)
- Test: `tests/core/test_schemas.py` (create if absent)

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_schemas.py
from core.schemas import CuratedSource, CuratedContext


def test_curated_context_defaults():
    src = CuratedSource(tier="note", uid="n1", title="T", content="C", distance=0.1)
    ctx = CuratedContext(synthesis="s", sources=[src], query="q")
    assert ctx.confidence is None
    assert ctx.sources[0].tier == "note"
    assert ctx.sources[0].source_uid is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_schemas.py::test_curated_context_defaults -v`
Expected: FAIL with `ImportError: cannot import name 'CuratedSource'`

- [ ] **Step 3: Add the models**

In `core/schemas.py`, after the `SearchFilters` class:

```python
class CuratedSource(BaseModel):
    tier: Literal["note", "chunk"]
    uid: str
    source_uid: str | None = None
    title: str
    content: str
    distance: float


class CuratedContext(BaseModel):
    synthesis: str
    sources: list[CuratedSource]
    confidence: float | None = None
    query: str
```

(`Literal` and `BaseModel` are already imported in this file — verify the `from typing import ... Literal` line near the top; it is used by `ExportResult`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_schemas.py::test_curated_context_defaults -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/schemas.py tests/core/test_schemas.py
git commit -m "feat: add CuratedContext schema for curate() tier 0"
```

---

## Task 2: Curate config

**Files:**
- Modify: `core/config.py` (add class after `WebConfig` ~line 53, wire into `SystemConfig` ~line 56)
- Modify: `config/system.yaml` (add block after `web:`)
- Test: `tests/core/test_config.py` (append; create if absent)

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_config.py
from core.config import load_settings


def test_curate_config_defaults():
    s = load_settings()
    assert s.system.curate.escalation_min_notes == 3
    assert s.system.curate.escalation_max_distance == 0.5
    assert s.system.curate.synthesis_max_chars_per_item == 800
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_config.py::test_curate_config_defaults -v`
Expected: FAIL with `AttributeError: 'SystemConfig' object has no attribute 'curate'`

- [ ] **Step 3: Add CurateConfig and wire it**

In `core/config.py`, after `WebConfig`:

```python
class CurateConfig(BaseModel):
    escalation_min_notes: int = 3
    escalation_max_distance: float = 0.5
    synthesis_max_chars_per_item: int = 800
```

In `SystemConfig`, add the field (with a default so existing configs keep working):

```python
class SystemConfig(BaseModel):
    chunking: ChunkingConfig
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMSystemConfig
    upload: UploadConfig = UploadConfig()
    web: WebConfig = WebConfig()
    curate: CurateConfig = CurateConfig()
    taxonomy: TaxonomyConfig
```

In `config/system.yaml`, after the `web:` block:

```yaml
curate:
  escalation_min_notes: 3        # < N relevant notes → escalate to chunks
  escalation_max_distance: 0.5   # "relevant" threshold — TO CALIBRATE in real-world test
  synthesis_max_chars_per_item: 800
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_config.py::test_curate_config_defaults -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/config.py config/system.yaml tests/core/test_config.py
git commit -m "feat: add curate config block (escalation + truncation)"
```

---

## Task 3: curate() tool — note-only path

**Files:**
- Create: `tools/vault/curate.py`
- Test: `tests/tools/vault/test_curate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/vault/test_curate.py
from unittest.mock import MagicMock
from core.schemas import SearchResult
from tools.vault.curate import curate


def _ctx_with(notes, chunks):
    ctx = MagicMock()
    ctx.embed.return_value = [0.0] * 8
    ctx.db.search_notes.return_value = notes
    ctx.db.search_chunks.return_value = chunks
    ctx.settings.system.curate.escalation_min_notes = 3
    ctx.settings.system.curate.escalation_max_distance = 0.5
    ctx.settings.system.curate.synthesis_max_chars_per_item = 800
    return ctx


def test_notes_sufficient_no_chunk_escalation():
    notes = [
        SearchResult(note_uid=f"n{i}", source_uid="s1", content=f"body {i}",
                     title=f"Note {i}", distance=0.1)
        for i in range(3)
    ]
    ctx = _ctx_with(notes, [])
    result = curate("q", ctx)
    ctx.db.search_chunks.assert_not_called()
    assert result.confidence is None
    assert result.query == "q"
    assert len(result.sources) == 3
    assert all(s.tier == "note" for s in result.sources)
    assert "[note:n0] Note 0" in result.synthesis
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/tools/vault/test_curate.py::test_notes_sufficient_no_chunk_escalation -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.vault.curate'`

- [ ] **Step 3: Write the tool**

```python
# tools/vault/curate.py
"""
Librarian tool — tier 0 (deterministic).

Orchestrates the two-tier search (compiled notes → raw chunks) into a single
stable CuratedContext. No LLM: synthesis is a minimal assembled block,
confidence is None. Tier 1 will upgrade only synthesis quality and confidence.
"""

from core.context import VaultContext
from core.schemas import SearchFilters, CuratedSource, CuratedContext
from core.logging import loggable


@loggable("curate")
def curate(
    query: str,
    ctx: VaultContext,
    conversation_summary: str | None = None,  # accepted, inert in tier 0
    filters: SearchFilters | None = None,
    limit: int = 5,
) -> CuratedContext:
    """Deterministic Librarian: search notes, escalate to chunks if sparse, assemble."""
    cfg = ctx.settings.system.curate
    query_embedding = ctx.embed(query)

    notes = ctx.db.search_notes(query_embedding, filters, limit)
    relevant = [n for n in notes if n.distance < cfg.escalation_max_distance]

    chunks = []
    if len(relevant) < cfg.escalation_min_notes:
        chunks = ctx.db.search_chunks(query_embedding, filters, limit)

    note_sources = [
        CuratedSource(tier="note", uid=n.note_uid, source_uid=n.source_uid,
                      title=n.title, content=n.content, distance=n.distance)
        for n in sorted(notes, key=lambda r: r.distance)
    ]
    chunk_sources = [
        CuratedSource(tier="chunk", uid=c.chunk_uid, source_uid=c.source_uid,
                      title=c.title, content=c.content, distance=c.distance)
        for c in sorted(chunks, key=lambda r: r.distance)
    ]
    sources = (note_sources + chunk_sources)[:limit]

    cap = cfg.synthesis_max_chars_per_item
    synthesis = "\n\n".join(
        f"[{s.tier}:{s.uid}] {s.title}\n{s.content[:cap]}" for s in sources
    )

    return CuratedContext(
        synthesis=synthesis,
        sources=sources,
        confidence=None,
        query=query,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/tools/vault/test_curate.py::test_notes_sufficient_no_chunk_escalation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/vault/curate.py tests/tools/vault/test_curate.py
git commit -m "feat: curate() tier 0 — note-only path"
```

---

## Task 4: curate() — escalation, merge, edges

**Files:**
- Modify: `tests/tools/vault/test_curate.py` (append tests)

- [ ] **Step 1: Write the failing tests**

```python
def test_escalation_merges_notes_first_then_chunks():
    notes = [SearchResult(note_uid="n1", source_uid="s1", content="nbody",
                          title="N1", distance=0.2)]
    chunks = [SearchResult(chunk_uid="c1", source_uid="s2", content="cbody",
                           title="C1", distance=0.05)]
    ctx = _ctx_with(notes, chunks)
    result = curate("q", ctx, limit=5)
    ctx.db.search_chunks.assert_called_once()
    assert [s.tier for s in result.sources] == ["note", "chunk"]


def test_zero_results_no_error():
    ctx = _ctx_with([], [])
    result = curate("q", ctx)
    assert result.synthesis == ""
    assert result.sources == []
    assert result.confidence is None


def test_truncation_to_limit():
    notes = [SearchResult(note_uid=f"n{i}", source_uid="s", content="b",
                          title=f"N{i}", distance=0.9) for i in range(10)]
    ctx = _ctx_with(notes, [SearchResult(chunk_uid="c", source_uid="s",
                    content="b", title="C", distance=0.01)])
    result = curate("q", ctx, limit=3)
    assert len(result.sources) == 3


def test_conversation_summary_is_inert():
    notes = [SearchResult(note_uid="n1", source_uid="s", content="b",
                          title="N", distance=0.1) for _ in range(3)]
    a = curate("q", _ctx_with(notes, []))
    b = curate("q", _ctx_with(notes, []), conversation_summary="lots of context")
    assert a.model_dump() == b.model_dump()


def test_per_item_content_truncation():
    notes = [SearchResult(note_uid="n1", source_uid="s",
                          content="x" * 5000, title="N", distance=0.1)
             for _ in range(3)]
    ctx = _ctx_with(notes, [])
    ctx.settings.system.curate.synthesis_max_chars_per_item = 100
    result = curate("q", ctx)
    assert "x" * 100 in result.synthesis
    assert "x" * 101 not in result.synthesis
```

- [ ] **Step 2: Run tests to verify status**

Run: `python -m pytest tests/tools/vault/test_curate.py -v`
Expected: All PASS (Task 3 implementation already covers these). If `test_truncation_to_limit` or merge order fails, fix `curate.py` sorting/slicing accordingly — notes list must precede chunks before the `[:limit]` slice.

- [ ] **Step 3: Commit**

```bash
git add tests/tools/vault/test_curate.py
git commit -m "test: curate() tier 0 — escalation, merge order, edges"
```

---

## Task 5: MCP tool wrapper

**Files:**
- Modify: `mcp/server.py` (imports near top + new `@mcp.tool()` after the `search` tool, ~line 141)

- [ ] **Step 1: Add the import**

Near the other tool imports in `mcp/server.py` (where `_search_tool` is imported — find `from tools.vault.search import search as _search_tool` or equivalent), add:

```python
from tools.vault.curate import curate as _curate_tool
```

- [ ] **Step 2: Add the MCP tool**

After the `search` `@mcp.tool()` block (after line ~141):

```python
@mcp.tool()
def curate(query: str, filters: dict | None = None, limit: int = 5) -> dict:
    """
    Librarian retrieval — the preferred entry point for any knowledge question.

    Searches your compiled notes first, falls back to raw source chunks only
    when notes are sparse, and returns a single assembled context with
    verifiable source UIDs.

    When to use: BEFORE answering any question from the vault. Prefer this
    over search() — it returns curated signal, not raw top-K noise.

    What to call next: get_note(uid) or get_source(source_uid) to read full
    content for any source you want to quote verbatim.
    """
    search_filters = SearchFilters(**(filters or {}))
    result = _curate_tool(query, ctx, filters=search_filters, limit=limit)
    return result.model_dump(mode="json")
```

- [ ] **Step 3: Smoke-check the server imports**

Run: `python -c "import mcp.server"`
Expected: no error (module imports cleanly).

- [ ] **Step 4: Commit**

```bash
git add mcp/server.py
git commit -m "feat: expose curate() as MCP tool"
```

---

## Task 6: CLI command

**Files:**
- Create: `cli/commands/curate.py`
- Modify: `cli/main.py` (register command)
- Test: `tests/cli/test_curate_cmd.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_curate_cmd.py
from unittest.mock import patch
from typer.testing import CliRunner
from cli.main import app
from core.schemas import CuratedContext, CuratedSource

runner = CliRunner()


def test_curate_cmd_prints_synthesis():
    fake = CuratedContext(
        synthesis="[note:n1] Title\nbody",
        sources=[CuratedSource(tier="note", uid="n1", title="Title",
                               content="body", distance=0.1)],
        query="q",
    )
    with patch("cli.commands.curate._build_ctx"), \
         patch("cli.commands.curate._run_curate", return_value=fake):
        result = runner.invoke(app, ["curate", "q"])
    assert result.exit_code == 0
    assert "n1" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_curate_cmd.py::test_curate_cmd_prints_synthesis -v`
Expected: FAIL (`ModuleNotFoundError` / no `curate` command registered)

- [ ] **Step 3: Write the command**

```python
# cli/commands/curate.py
"""
Curate command — Librarian tier 0 retrieval.

Routing layer only. No business logic.
"""

from typing import Annotated

import typer

from cli.output import print_error

app = typer.Typer(help="Librarian retrieval over the vault.")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _run_curate(query: str, ctx, limit: int):
    from tools.vault.curate import curate
    return curate(query, ctx, limit=limit)


@app.command()
def curate_cmd(
    query: Annotated[str, typer.Argument(help="Knowledge question")],
    limit: Annotated[int, typer.Option("--limit", help="Max sources")] = 5,
) -> None:
    """Librarian tier 0 retrieval over the vault."""
    if not query.strip():
        print_error("Query must not be empty.", "empty_query", False, False)
        raise typer.Exit(1)

    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found. Run the setup script first.",
                    "config_error", False, False, str(e))
        raise typer.Exit(1)

    try:
        result = _run_curate(query, ctx, limit)
    except Exception as e:
        print_error("Curate failed.", "curate_error", False, False, str(e))
        raise typer.Exit(1)

    if not result.sources:
        typer.echo("No results found.")
        return

    typer.echo(result.synthesis)
    typer.echo("\n--- sources ---")
    for s in result.sources:
        typer.echo(f"[{s.tier}:{s.uid}] {s.title}  (distance={s.distance:.4f})")
```

- [ ] **Step 4: Register the command**

In `cli/main.py`, mirror the existing `search` registration:

```python
from cli.commands.curate import curate_cmd as _curate
...
app.command("curate")(_curate)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/cli/test_curate_cmd.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add cli/commands/curate.py cli/main.py tests/cli/test_curate_cmd.py
git commit -m "feat: egovault curate CLI command"
```

---

## Task 7: Full suite + ripple docs

**Files:**
- Modify: `.claude/rules/vault-usage.md`, `docs/architecture/ARCHITECTURE.md`,
  `PROJECT-STATUS.md`, `SESSION-CONTEXT.md`, `docs/VISION-KNOWLEDGE-COMPILER.md`

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -q`
Expected: all pass, zero regressions. Fix any breakage before continuing.

- [ ] **Step 2: Update vault-usage rule**

In `.claude/rules/vault-usage.md`, under "When MCP tools are available", change the
"Before answering a knowledge question" bullet to call `curate()` first, then
`search_notes` only when verbatim quoting is needed. Update the workflow order list to
add `curate` as step 2 (between Ingest and raw Search).

- [ ] **Step 3: Update ARCHITECTURE.md**

Add `curate()` to the glossary: "Librarian tier 0 — deterministic notes→chunks
orchestration returning `CuratedContext`. No LLM. Tier 1 (LLM synthesis) deferred."
Add a one-line entry in the tools/vault section.

- [ ] **Step 4: Update status + context files**

- `PROJECT-STATUS.md`: add to implemented features table
  (`curate() tier 0 | 2026-05-15 | Done`), tick the pending task, add a session-history
  row, advance roadmap item 17.
- `SESSION-CONTEXT.md`: add to "Deferred items": curate() tier 1 (needs generic
  `complete` Protocol on VaultContext), API `/curate` endpoint, escalation threshold
  calibration. Mark open question #4 (curate() design) resolved for tier 0.
- `docs/VISION-KNOWLEDGE-COMPILER.md`: in "Incremental implementation path", mark
  step 1 (`curate()` tier 0) as **implemented (2026-05-15)**.

- [ ] **Step 5: Commit**

```bash
git add .claude/rules/vault-usage.md docs/architecture/ARCHITECTURE.md PROJECT-STATUS.md SESSION-CONTEXT.md docs/VISION-KNOWLEDGE-COMPILER.md
git commit -m "docs: wire curate() tier 0 into rules, architecture, status"
```

---

## Self-Review

**Spec coverage:**
- §2 schema → Task 1 ✅
- §3 flow (embed once, notes, escalation, chunks, merge notes-first, assemble, None confidence, zero-result) → Tasks 3+4 ✅
- §3 no tool→tool import → Task 3 uses `ctx.db.search_*` directly ✅
- §4 config → Task 2 ✅
- §5 surfaces MCP+CLI, API deferred → Tasks 5+6; API not implemented (correct) ✅
- §6 tests (all 7 cases) → Tasks 3+4 + CLI smoke Task 6 ✅
- §7 ripple → Task 7 ✅
- §8 deferred tracked → Task 7 step 4 ✅

**Placeholder scan:** none — all steps contain runnable code/commands.

**Type consistency:** `CuratedSource`/`CuratedContext` field names identical across Tasks 1, 3, 6. `_build_ctx`/`_run_curate` names match between Task 6 command and its test. `ctx.settings.system.curate.*` names match Task 2 config and Task 3 usage. `ctx.db.search_notes/search_chunks(embedding, filters, limit)` matches `infrastructure/db.py` signatures.
