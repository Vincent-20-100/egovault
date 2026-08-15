# curate() tier-1 base (Librarian sub-context) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a vault question be answered by an isolated fresh-context step that uses the host's own LLM (no API key/local model), fed by a recall-first "generous" retrieval, returning only `{answer, used_source_uids}` to the main conversation.

**Architecture:** One Python change — a `generous` mode on `curate()` that forces hybrid RRF retrieval over both tiers (notes + chunks), wide net, untruncated content. The synthesis/precision is delegated to a librarian sub-agent and a `/ask-vault` slash command, shipped together as a Claude Code plugin. Sampling is the future end-state (tracked debt).

**Tech Stack:** Python 3.x, Pydantic v2, pytest, FastMCP, SQLite (FTS5 hybrid already built), Claude Code plugin format.

**Spec:** `.meta/specs/2026-05-29-curate-tier1-librarian-base-spec.md`

---

## File Structure

- `core/config.py` — add `generous_limit` to `CurateConfig` (modify, ~line 56-60).
- `config/system.yaml` — surface the new config value (modify, `curate:` block).
- `tools/vault/curate.py` — add `generous: bool = False` param + recall-first branch (modify).
- `tests/tools/vault/test_curate.py` — new tests for generous mode (modify).
- `mcp/server.py` — expose `generous` on the `curate` MCP tool (modify, ~line 144-161).
- `.claude-plugin/plugin.json` — plugin manifest (create).
- `agents/librarian.md` — subagent definition bundled in the plugin (create).
- `.claude/agents/librarian.md` — same agent, checked-in for in-repo out-of-box use (create).
- `commands/ask-vault.md` — slash command bundled in the plugin (create).
- `tests/plugin/test_plugin_files.py` — smoke test the plugin/agent/command files parse (create).
- `docs/user-guide/09-mcp.md` + `docs/user-guide/06-search-curate.md` — docs (modify; confirm exact filenames in Task 7).
- `PROJECT-STATUS.md`, `SESSION-CONTEXT.md` — debt + deferred item (modify).

---

## Task 1: Add `generous_limit` config

**Files:**
- Modify: `core/config.py:56-60`
- Modify: `config/system.yaml` (the `curate:` block)

- [ ] **Step 1: Add the field to CurateConfig**

In `core/config.py`, change the `CurateConfig` class to:

```python
class CurateConfig(BaseModel):
    escalation_min_notes: int = 3
    escalation_max_distance: float = 0.5
    synthesis_max_chars_per_item: int = 800
    use_hybrid_retrieval: bool = False  # cosine + BM25/FTS5 via RRF when True
    generous_limit: int = 20  # per-tier candidate count for the librarian's generous mode
```

- [ ] **Step 2: Surface it in system.yaml**

In `config/system.yaml`, locate the `curate:` block and add the key (match the existing keys' style/indentation):

```yaml
  curate:
    escalation_min_notes: 3
    escalation_max_distance: 0.5
    synthesis_max_chars_per_item: 800
    use_hybrid_retrieval: false
    generous_limit: 20
```

(If a key above is absent in the file, only ADD `generous_limit`; do not remove existing keys.)

- [ ] **Step 3: Verify config loads**

Run: `python -c "from core.config import CurateConfig; print(CurateConfig().generous_limit)"`
Expected: `20`

- [ ] **Step 4: Commit**

```bash
git add core/config.py config/system.yaml
git commit -m "feat: add curate.generous_limit config for librarian generous mode"
```

---

## Task 2: `generous` mode on curate() (recall-first)

**Files:**
- Modify: `tools/vault/curate.py`
- Test: `tests/tools/vault/test_curate.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/tools/vault/test_curate.py`:

```python
def _ctx_generous(notes, chunks, hybrid_flag=False, generous_limit=20):
    ctx = MagicMock()
    ctx.embed.return_value = [0.1] * 8
    ctx.db.search_notes_hybrid.return_value = notes
    ctx.db.search_chunks_hybrid.return_value = chunks
    ctx.db.search_notes.return_value = notes
    ctx.db.search_chunks.return_value = chunks
    ctx.settings.system.curate.escalation_min_notes = 3
    ctx.settings.system.curate.escalation_max_distance = 0.5
    ctx.settings.system.curate.synthesis_max_chars_per_item = 800
    ctx.settings.system.curate.use_hybrid_retrieval = hybrid_flag
    ctx.settings.system.curate.generous_limit = generous_limit
    return ctx


def test_generous_forces_hybrid_even_when_flag_false():
    notes = [SearchResult(note_uid="n1", source_uid="s1", content="n", title="N1", distance=0.1)]
    chunks = [SearchResult(chunk_uid="c1", source_uid="s2", content="c", title="C1", distance=0.2)]
    ctx = _ctx_generous(notes, chunks, hybrid_flag=False)
    curate("q", ctx, generous=True)
    ctx.db.search_notes_hybrid.assert_called_once()
    ctx.db.search_chunks_hybrid.assert_called_once()
    ctx.db.search_notes.assert_not_called()
    ctx.db.search_chunks.assert_not_called()


def test_generous_returns_both_tiers_no_escalation_gate():
    # 5 close notes would normally suppress chunk escalation; generous must still fetch chunks.
    notes = [SearchResult(note_uid=f"n{i}", source_uid="s1", content="n", title=f"N{i}", distance=0.1)
             for i in range(5)]
    chunks = [SearchResult(chunk_uid="c1", source_uid="s2", content="c", title="C1", distance=0.3)]
    ctx = _ctx_generous(notes, chunks)
    result = curate("q", ctx, generous=True)
    tiers = {s.tier for s in result.sources}
    assert tiers == {"note", "chunk"}
    assert len(result.sources) == 6  # no [:limit] cap in generous mode


def test_generous_does_not_truncate_content():
    long_body = "x" * 2000  # > synthesis_max_chars_per_item (800)
    notes = [SearchResult(note_uid="n1", source_uid="s1", content=long_body, title="N1", distance=0.1)]
    ctx = _ctx_generous(notes, [])
    result = curate("q", ctx, generous=True)
    assert long_body in result.synthesis  # full content, untruncated


def test_generous_uses_generous_limit():
    notes = [SearchResult(note_uid="n1", source_uid="s1", content="n", title="N1", distance=0.1)]
    ctx = _ctx_generous(notes, [], generous_limit=42)
    curate("q", ctx, generous=True)
    # limit is the 4th positional arg of search_notes_hybrid(query_text, query_embedding, filters, limit)
    assert ctx.db.search_notes_hybrid.call_args.args[3] == 42
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/tools/vault/test_curate.py -k generous -v`
Expected: FAIL — `curate()` got an unexpected keyword argument `generous`.

- [ ] **Step 3: Implement the generous branch**

Replace the body of `tools/vault/curate.py` `curate()` with:

```python
@loggable("curate")
def curate(
    query: str,
    ctx: VaultContext,
    conversation_summary: str | None = None,  # accepted, inert in tier 0
    filters: SearchFilters | None = None,
    limit: int = 5,
    generous: bool = False,
) -> CuratedContext:
    """Deterministic Librarian. generous=True: recall-first wide net for a sub-agent."""
    cfg = ctx.settings.system.curate
    query_embedding = ctx.embed(query)

    if generous:
        # Recall-first: force hybrid, fetch BOTH tiers (no escalation gate), wide net.
        eff_limit = cfg.generous_limit
        notes = ctx.db.search_notes_hybrid(query, query_embedding, filters, eff_limit)
        chunks = ctx.db.search_chunks_hybrid(query, query_embedding, filters, eff_limit)
    else:
        if cfg.use_hybrid_retrieval:
            notes = ctx.db.search_notes_hybrid(query, query_embedding, filters, limit)
        else:
            notes = ctx.db.search_notes(query_embedding, filters, limit)
        relevant = [n for n in notes if n.distance < cfg.escalation_max_distance]
        chunks = []
        if len(relevant) < cfg.escalation_min_notes:
            if cfg.use_hybrid_retrieval:
                chunks = ctx.db.search_chunks_hybrid(query, query_embedding, filters, limit)
            else:
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

    if generous:
        sources = note_sources + chunk_sources  # no cap: the sub-agent does the triage
        cap = None
    else:
        sources = (note_sources + chunk_sources)[:limit]
        cap = cfg.synthesis_max_chars_per_item

    synthesis = "\n\n".join(
        f"[{s.tier}:{s.uid}] {s.title}\n{s.content if cap is None else s.content[:cap]}"
        for s in sources
    )

    return CuratedContext(
        synthesis=synthesis,
        sources=sources,
        confidence=None,
        query=query,
    )
```

- [ ] **Step 4: Run the generous tests**

Run: `python -m pytest tests/tools/vault/test_curate.py -k generous -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the full curate test file (no regression on tier-0)**

Run: `python -m pytest tests/tools/vault/test_curate.py -v`
Expected: all PASS (existing + 4 new).

- [ ] **Step 6: Commit**

```bash
git add tools/vault/curate.py tests/tools/vault/test_curate.py
git commit -m "feat: add recall-first generous mode to curate() for librarian sub-context"
```

---

## Task 3: Expose `generous` on the MCP curate tool

**Files:**
- Modify: `mcp/server.py:144-161`

- [ ] **Step 1: Update the tool signature + docstring + passthrough**

Replace the `curate` MCP tool in `mcp/server.py` with:

```python
@mcp.tool()
def curate(query: str, filters: dict | None = None, limit: int = 5,
           generous: bool = False) -> dict:
    """
    Librarian retrieval — the preferred entry point for any knowledge question.

    Searches your compiled notes first, falls back to raw source chunks only
    when notes are sparse, and returns a single assembled context with
    verifiable source UIDs.

    Set generous=True when an isolated agent will triage the results: it casts a
    wider recall-first net (hybrid retrieval, both notes and chunks, untruncated)
    so the agent can pick the truly relevant sources itself.

    When to use: BEFORE answering any question from the vault. Prefer this
    over search() — it returns curated signal, not raw top-K noise.

    What to call next: get_note(uid) or get_source(source_uid) to read full
    content for any source you want to quote verbatim.
    """
    search_filters = SearchFilters(**(filters or {}))
    result = _curate_tool(query, ctx, filters=search_filters, limit=limit,
                          generous=generous)
    return result.model_dump(mode="json")
```

- [ ] **Step 2: Verify the server imports without error**

Run: `python -c "import mcp.server"`
Expected: no error (exit 0).

- [ ] **Step 3: Commit**

```bash
git add mcp/server.py
git commit -m "feat: expose generous mode on the curate MCP tool"
```

---

## Task 4: Librarian subagent + slash command + plugin manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `agents/librarian.md`
- Create: `.claude/agents/librarian.md` (identical body to `agents/librarian.md`)
- Create: `commands/ask-vault.md`

- [ ] **Step 1: Write the plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "egovault",
  "version": "0.1.0",
  "description": "EgoVault personal knowledge vault — MCP server + librarian sub-context retrieval.",
  "author": "Vincent"
}
```

- [ ] **Step 2: Write the librarian subagent**

Create `agents/librarian.md`:

```markdown
---
name: librarian
description: Use to answer any question from the EgoVault knowledge vault. Delegates retrieval and synthesis to a fresh context so the main conversation stays clean — call this whenever the user asks something their vault likely contains.
tools: curate, get_note, get_source, search
---

You are the EgoVault Librarian. Your job: answer a question using only the vault,
in an isolated context, and return a compact result.

Process:
1. Call `curate(query, generous=true)`. This returns a wide, recall-first pile of
   candidate notes and chunks, each tagged `[tier:uid]` with full content.
2. Read the pile and TRIAGE it: keep only the sources that actually bear on the
   question; ignore the rest. The retrieval is deliberately over-inclusive — the
   filtering is your job.
3. Synthesize a direct, grounded answer from the kept sources. Do not use outside
   knowledge. If the pile contains nothing relevant, say plainly that the vault has
   no relevant material — never invent.
4. Return to the caller ONLY:
   - the answer, and
   - the list of UIDs you actually used (the `uid` of each kept source).

Do not dump the raw pile back to the caller. The whole point is that the caller's
main conversation receives only your distilled answer plus the useful source UIDs.
```

- [ ] **Step 3: Mirror the agent for in-repo out-of-box use**

Create `.claude/agents/librarian.md` with the EXACT SAME content as `agents/librarian.md` (copy it verbatim).

- [ ] **Step 4: Write the slash command**

Create `commands/ask-vault.md`:

```markdown
---
description: Answer a question from the EgoVault knowledge vault via an isolated librarian step (guaranteed fresh context).
argument-hint: <question>
---

Delegate to the `librarian` subagent to answer this question from the vault: $ARGUMENTS

The librarian must run in its own context: it calls `curate(query, generous=true)`,
triages the recall-first pile, synthesizes a grounded answer, and returns ONLY the
answer plus the UIDs of the sources actually used. Do not pull the raw retrieved
pile into this conversation — surface only the librarian's distilled result.
```

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json agents/librarian.md .claude/agents/librarian.md commands/ask-vault.md
git commit -m "feat: ship librarian subagent + ask-vault command + plugin manifest"
```

---

## Task 5: Smoke test the plugin/agent/command files

**Files:**
- Create: `tests/plugin/test_plugin_files.py`

- [ ] **Step 1: Write the test**

Create `tests/plugin/test_plugin_files.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_plugin_manifest_is_valid_json_with_required_keys():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "egovault"
    assert "version" in manifest and "description" in manifest


def test_librarian_agent_has_frontmatter_and_calls_generous_curate():
    body = (ROOT / "agents" / "librarian.md").read_text(encoding="utf-8")
    assert body.startswith("---")
    assert "name: librarian" in body
    assert "description:" in body
    assert "generous=true" in body  # must instruct the recall-first call


def test_in_repo_agent_matches_plugin_agent():
    a = (ROOT / "agents" / "librarian.md").read_text(encoding="utf-8")
    b = (ROOT / ".claude" / "agents" / "librarian.md").read_text(encoding="utf-8")
    assert a == b  # the two copies must not drift


def test_ask_vault_command_has_frontmatter_and_arguments():
    body = (ROOT / "commands" / "ask-vault.md").read_text(encoding="utf-8")
    assert body.startswith("---")
    assert "description:" in body
    assert "$ARGUMENTS" in body
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/plugin/test_plugin_files.py -v`
Expected: PASS (4 tests). If `tests/plugin/` needs an `__init__.py`, the repo's other test dirs show the convention — match it (most pytest layouts need none).

- [ ] **Step 3: Commit**

```bash
git add tests/plugin/test_plugin_files.py
git commit -m "test: smoke-test plugin manifest, librarian agent, ask-vault command"
```

---

## Task 6: Documentation + tracked technical debt

**Files:**
- Modify: `docs/user-guide/` MCP chapter and search/curate chapter (confirm exact filenames first)
- Modify: `PROJECT-STATUS.md`
- Modify: `SESSION-CONTEXT.md`

- [ ] **Step 1: Find the exact user-guide chapter filenames**

Run: `ls docs/user-guide/`
Identify the MCP chapter and the search/curate chapter (per PROJECT-STATUS they are chapters 09 = mcp and 06 = search-curate).

- [ ] **Step 2: Document the librarian pattern in the MCP chapter**

In the MCP chapter, add a section that covers: (a) installing EgoVault as a Claude Code plugin (`/plugin install`) which bundles the MCP server + `librarian` subagent + `/ask-vault` command; (b) the two ways to trigger isolated retrieval — explicit `/ask-vault <question>` (guaranteed) vs. automatic delegation to the `librarian` subagent (heuristic); (c) that this uses the host's own LLM, no API key needed. Match the chapter's existing heading style and tone.

- [ ] **Step 3: Document generous mode in the search/curate chapter**

In the search/curate chapter, add a short subsection: `curate(generous=true)` casts a recall-first wide net (hybrid retrieval, both notes and chunks, untruncated) intended for an isolated agent that does the final triage — as opposed to the default precise mode. Note that precision is then provided by the agent's reasoning.

- [ ] **Step 4: Add the technical-debt entry**

In `PROJECT-STATUS.md`, under "## Known technical debt", add a row:

```markdown
| **Librarian base uses host-side delegation (no sampling)** | MAJOR | Base relies on subagent/slash delegation because MCP sampling is unsupported by Claude Code/Desktop (verified 2026-05-29). MIGRATE to MCP sampling when clients ship support → transparent + automatic + reliable server-side isolation. Track: anthropics/claude-code#1785. |
```

- [ ] **Step 5: Note the deferred sampling migration in SESSION-CONTEXT.md**

In `SESSION-CONTEXT.md`, under "## Deferred items", add a row:

```markdown
| **Migrate librarian to MCP sampling** | spec `2026-05-29-curate-tier1-librarian-base` §10 | When Claude Code/Desktop advertise the sampling capability |
```

- [ ] **Step 6: Commit**

```bash
git add docs/user-guide/ PROJECT-STATUS.md SESSION-CONTEXT.md
git commit -m "docs: librarian pattern + generous mode + sampling-migration debt"
```

---

## Task 7: Full suite + status update

**Files:**
- Modify: `PROJECT-STATUS.md` (session history + implemented features)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -q`
Expected: previous green count + 8 new tests (4 generous + 4 plugin), 0 failures.
(Baseline per PROJECT-STATUS was 511 passed / 1 skipped.)

- [ ] **Step 2: Run ruff on changed files**

Run: `ruff check tools/vault/curate.py mcp/server.py core/config.py tests/tools/vault/test_curate.py tests/plugin/test_plugin_files.py`
Expected: no errors. Fix any reported.

- [ ] **Step 3: Update PROJECT-STATUS implemented features + session history**

Add a session-history row dated 2026-05-29 summarizing: curate() tier-1 base shipped (generous mode + librarian subagent + /ask-vault command + plugin manifest), no-API-key host-LLM design, sampling deferred. Mark the curate() tier-1 base as done in the relevant list.

- [ ] **Step 4: Commit**

```bash
git add PROJECT-STATUS.md
git commit -m "docs: status update - curate() tier-1 base (librarian) shipped"
```

---

## Notes for the implementer

- The librarian's `{answer, used_source_uids}` contract is enforced by the agent/command PROMPT, not by Python — there is intentionally no unit test for the LLM's synthesis behavior (spec §8). Do not fabricate one.
- Do NOT implement server-side LLM synthesis (`ctx.complete()`/ollama/API) or MCP sampling here — both are out of scope (spec §12) and are separate later specs.
- Keep tier-0 (`generous=False`) behavior byte-for-byte unchanged; the existing curate tests must stay green untouched.
- Commit messages stay ASCII-only (project rule for Windows shell).
