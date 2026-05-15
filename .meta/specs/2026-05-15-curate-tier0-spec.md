# Spec — `curate()` tier 0 (Librarian, deterministic baseline)

**Date:** 2026-05-15
**Status:** Validated by user (brainstorm) — ready for implementation plan.
**North star:** `docs/VISION-KNOWLEDGE-COMPILER.md` — step 1 of incremental path.
**Scope:** Tier 0 only (deterministic). Tier 1 (LLM synthesis) is a separate future spec.

---

## 1. Purpose

`curate()` is the Librarian tool's deterministic baseline: a single entry point that
orchestrates the existing two-tier search (compiled notes → raw chunks), assembles a
minimal consumable result, and returns a stable `CuratedContext`. It is a **tool with
intelligence**, not an autonomous agent — same pattern as `generate_note_from_source`,
minus (for now) the LLM call.

Tier 0 ships value immediately with **zero new dependency** and **zero LLM requirement**.
Tier 1 will later upgrade only the *quality* of the `synthesis` field and fill
`confidence` — without any contract change.

## 2. Contract — `CuratedContext` schema

New Pydantic models in `core/schemas.py`:

```python
class CuratedSource(BaseModel):
    tier: Literal["note", "chunk"]      # note = tier 2, chunk = tier 1
    uid: str                             # note_uid or chunk_uid (verifiable)
    source_uid: str | None = None
    title: str
    content: str
    distance: float                      # raw similarity, honest

class CuratedContext(BaseModel):
    synthesis: str                       # tier 0: deterministic assembled block
    sources: list[CuratedSource]         # structured, verifiable list
    confidence: float | None = None      # None in tier 0
    query: str                           # echo of the input query
```

**Frozen contract.** Tier 1 changes only the *quality* of `synthesis` and fills
`confidence`. No field is added or removed across tiers. This is what makes tiered
degradation transparent to the conversational agent.

## 3. Function — `tools/vault/curate.py`

```python
@loggable("curate")
def curate(
    query: str,
    ctx: VaultContext,
    conversation_summary: str | None = None,   # accepted, INERT in tier 0
    filters: SearchFilters | None = None,
    limit: int = 5,
) -> CuratedContext:
```

Deterministic flow:

1. **Search notes** (tier 2): `ctx.db.search_notes(ctx.embed(query), filters, limit)`.
2. **Escalation decision** (config-driven): count notes with
   `distance < curate.escalation_max_distance`. If that count `< curate.escalation_min_notes`
   → escalate.
3. **Search chunks** (tier 1) only if escalated:
   `ctx.db.search_chunks(ctx.embed(query), filters, limit)` (reuse the cached query
   embedding — embed once).
4. **Merge + sort**: notes first (tier 2 priority), then chunks; each group sorted by
   ascending `distance`; total truncated to `limit`.
5. **Assemble `synthesis`**: minimal concatenation of truncated `content`, each block
   prefixed `[<tier>:<uid>] <title>`. Deliberately poor — no rephrasing, no dedup beyond
   exact-uid. Per-item truncation at `curate.synthesis_max_chars_per_item`.
6. **`confidence = None`**, `sources` = structured items, `query` = echo.

Edge case: zero results → `synthesis=""`, `sources=[]`, `confidence=None`, no error raised.

**No tool→tool import** (`code-style.md`: "never cross-import between tools").
`curate()` does not import `tools.vault.search`; it calls `ctx.embed` + `ctx.db.search_*`
directly — exactly the two one-liners `search.py` itself uses. Query is embedded once and
the vector reused for both note and chunk searches.

## 4. Config — `config/system.yaml`

```yaml
curate:
  escalation_min_notes: 3        # < N relevant notes → escalate to chunks
  escalation_max_distance: 0.5   # "relevant" threshold — TO CALIBRATE in real-world test
  synthesis_max_chars_per_item: 800
```

`escalation_max_distance` is an explicit magic number that **cannot be calibrated without
real data** (trap #9). Default is a placeholder; calibration is a deferred task tied to
the real-world testing milestone.

## 5. Surfaces

| Surface | This spec | Notes |
|---------|-----------|-------|
| MCP `curate` | ✅ | Thin wrapper (G11: no business logic). Primary surface — Librarian pattern lives here. |
| CLI `egovault curate "<query>" [--limit N]` | ✅ | Prints `synthesis` + `sources` (uid + distance). Used to test tier 0 without LLM during real-world test. |
| API `/curate` | ❌ deferred | No HTTP consumer identified (YAGNI). Tracked as deferred item. |

`search_notes` is **kept unchanged** (low-level tier 1/2 raw access). `curate()`
orchestrates it; it does not replace it. `.claude/rules/vault-usage.md` updated to:
"knowledge question → `curate()` first, then `search_notes` if verbatim needed".

## 6. Tests

`tests/tools/vault/test_curate.py` — mock at boundary
(`ctx.db.search_notes`/`ctx.db.search_chunks` + `ctx.embed`), never internal functions:

- notes sufficient → no chunk escalation
- notes insufficient → escalate, merge notes + chunks, notes ranked first
- zero results → empty `synthesis`/`sources`, no error
- truncation to `limit`
- `conversation_summary` provided → identical result vs. omitted (proves inert)
- `confidence is None` always in tier 0
- per-item content truncation at config limit

`tests/cli/test_curate_cmd.py` — smoke test of the CLI command.

## 7. Ripple — references to update (no stale refs)

- `.claude/rules/vault-usage.md` — curate-first guidance
- `docs/architecture/ARCHITECTURE.md` — `curate()` in glossary + Librarian tier 0 flow
- `PROJECT-STATUS.md` — feature done + roadmap entry
- `SESSION-CONTEXT.md` — deferred items (see §8) + architecture decision
- `docs/VISION-KNOWLEDGE-COMPILER.md` — mark "step 1 (tier 0): spec written"
- `CHANGELOG` if present

## 8. Deferred / out of scope (tracked, not forgotten)

| Item | Where tracked | When |
|------|--------------|------|
| **Tier 1 — LLM synthesis** | this spec + SESSION-CONTEXT | new spec after real-world test; needs new generic `complete` Protocol on `VaultContext` (none exists today — only specialized `generate`) |
| **Real `confidence`** | tier 1 spec | with tier 1 |
| **API endpoint `/curate`** | SESSION-CONTEXT deferred items | when an HTTP consumer exists |
| **`conversation_summary` active use** | tier 1 spec | with tier 1 |
| **Escalation threshold calibration** | PROJECT-STATUS / real-world test | during real-world testing |
| **`compile()` (persisted multi-source synthesis)** | VISION-KNOWLEDGE-COMPILER.md step 3 | later |
| **AGENTS.md pre-packaged librarian** | VISION-KNOWLEDGE-COMPILER.md step 4 | later |

## 9. Non-goals

Not replacing RAG. Not autonomous agent behaviour. No decision loop. No rewrite —
builds strictly on existing `search` + `ctx`.
