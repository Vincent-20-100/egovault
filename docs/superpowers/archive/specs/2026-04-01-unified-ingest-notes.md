# Unified Ingest Workflow — Brainstorm Notes

**Date:** 2026-04-01
**Phase:** BRAINSTORM (Phase 1)
**Participants:** User + Claude
**Spec:** `specs/2026-03-31-unified-ingest-architecture.md`

---

## Context

The unified ingest spec was written 2026-03-31, **before** the VaultContext refactoring.
VaultContext is now fully implemented (374 tests passing). The spec needs adaptation
to the current architecture before moving to PLAN.

---

## Decisions

### A — VaultContext replaces Settings in spec

**Decision:** All references to `settings` in the spec become `ctx: VaultContext`.
The spec was written pre-VaultContext. Current architecture (CLAUDE.md, ARCHITECTURE.md)
always takes precedence over older specs.

**Rationale:** Permanent docs override provisional docs (CLAUDE.md §3 rule).

### B — Extractors as private functions in workflow

**Decision:** Extractors are private functions in `workflows/ingest.py`, not separate files.
Each extractor is 3-5 lines. No premature abstraction (G5).

**Rationale:** No debate needed — this aligns with G5 and current codebase patterns.

### C — `parse_html` included in V1

**Decision:** Include `parse_html` in V1 as a local-only tool (`tools/text/parse_html.py`).

**Rationale:** `parse_html` takes an HTML **string** as input and returns plain text.
Zero network access, zero security concern. It's equivalent to `_extract_pdf_text()` but
for HTML. This enables manual HTML ingestion (copy-paste) before web scraping exists.
The web **fetching** layer (SSRF, DNS rebinding, rate limiting) is what requires the
security brainstorm — not local HTML parsing.

May be refined when web ingestion is added later.

### D — IngestError hierarchy (structured, option 2)

**Decision:** Create `IngestError` as base class with `error_code`, `user_message`,
`http_status`. Migrate `LargeFormatError` to inherit from it.

**Rationale:** This is the right moment to structure error handling. The base class
will serve all current and future ingest types. One-time migration cost, long-term benefit.

### E — Thin wrappers for backward compatibility

**Decision:** Keep `ingest_youtube.py`, `ingest_audio.py`, `ingest_pdf.py` as one-line
wrappers that delegate to `workflows/ingest.py`. Mark them clearly as deprecated wrappers.

**Rationale:** Avoids breaking existing imports in tests and surfaces all at once.
Wrappers are trivial (1-2 lines). Must be clearly tracked in PROJECT-STATUS.md and
SESSION-CONTEXT.md as debt to clean up in a future session.

### F — Crash recovery deferred

**Decision:** `recover_source()` (spec §16) is NOT part of V1.

**Rationale:** Not critical for the refactoring. Sources stuck in `processing` can be
cleaned manually. Recovery will be added in a future session after the unified workflow
is stable. Must be documented in PROJECT-STATUS.md and SESSION-CONTEXT.md.

### G — `source_assets` table deferred

**Decision:** `source_assets` table (spec §15, for image handling) is NOT created in V1.
No empty tables for features that don't exist yet.

**Rationale:** Adding a table "just in case" couples the DB to unimplemented features.
The table will be added when image handling is implemented. Must be documented in
PROJECT-STATUS.md and SESSION-CONTEXT.md.

---

## V1 Scope — Final

### Included

- `workflows/ingest.py` — unified pipeline with extractor registry
- Extractors: youtube, audio, pdf, texte (+ html via parse_html)
- `tools/text/parse_html.py` — local HTML string → plain text
- `IngestError` hierarchy in `core/errors.py`
- `ingest_text` — new source type
- Thin wrappers in old workflow files (backward compat)
- Refactor API/CLI/MCP to use unified workflow
- `ctx: VaultContext` everywhere (not `settings`)

### Excluded (deferred, documented)

- Crash recovery (`recover_source`)
- `source_assets` table (image handling)
- Web ingestion (requires security brainstorm for fetch layer)
- Image handling tiers 1-2

---

## Open questions resolved

| Question from spec | Resolution |
|--------------------|------------|
| §14.1 YouTube dispatch | `fetch_subtitles` already handles fallback internally — no change needed |
| §14.2 Text source_type default | `"texte"` for raw text, `"personnel"` for reflexion notes — confirmed |
| §14.4 Extractors location | Private functions in workflow (G5) — confirmed |

---

## Next step

Move to Phase 2 (SPEC update) — adapt the existing spec to reflect these decisions,
then Phase 3 (PLAN).
