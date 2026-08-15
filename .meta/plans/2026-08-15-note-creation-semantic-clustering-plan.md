# Implementation Plan: Note Creation by Semantic Nucleus & Candidate Lifecycle (Phase 1)

**Date:** 2026-08-15  
**Status:** Plan-Ready  
**Related Spec:** [`.meta/specs/2026-08-14-note-creation-semantic-clustering-spec.md`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/.meta/specs/2026-08-14-note-creation-semantic-clustering-spec.md)  
**Related Vision:** [`docs/VISION-KNOWLEDGE-COMPILER.md`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/docs/VISION-KNOWLEDGE-COMPILER.md) (Tier 0 & Tier 2)  
**Prerequisite Dependency:** Milestone 0 (Golden Configuration, Error Architecture & Cleanup)

---

## 1. Objectives & Scope

1. Eliminate semantic averaging on multi-topic notes by segmenting each `rag_ready` source into $N$ cohesive note candidates.
2. Implement plateau-aware cosine TextTiling with concrete numerical cutoff formulas and strict precedence merging (`max_chunks_per_candidate = 12` is an inviolable ceiling).
3. Deprecate and remove legacy `LargeFormatError` checks to allow unlimited-size sources to flow through segmentation.
4. Enforce single-transaction atomic lock assertion and note creation (`ExpiredLockError`).
5. Provide differentiated lock TTLs for agents ($300\text{ s}$) vs. humans ($3600\text{ s}$) with a lock renewal tool (`renew_candidate_lock`).
6. Define unambiguous re-ingestion contract (unconverted candidates purged/regenerated, converted notes preserved).
7. Factor `review_status` into `curate()` using configurable confidence weights from `config/system.yaml`.

---

## 2. Task Breakdown

### Task 1: Plateau-Aware Topic Segmentation Algorithm (`tools/text/segment.py`)
- **File:** `tools/text/segment.py`
- **Tests:** `tests/tools/text/test_segment.py`
- **Actions:**
  1. Implement pre-condition bypass for short sources ($N < 2 \times \text{min\_chunks\_per\_note}$).
  2. Implement consecutive cosine similarity calculation $s_i = \cos(v_i, v_{i+1})$.
  3. Implement Valley Depth Score $d_i$ with plateau midpoint detection ($s_{i-1} \ge s_i \le s_{i+1}$) and boundary peaks at $0$ and $N-2$.
  4. Implement exact numerical cutoff decision:
     $$d_i \ge \mu_d + k \cdot \sigma_d \quad \text{OR} \quad s_i < S_{\text{min}}$$
     (with fallback threshold $\mu_d + 0.05$ if $\sigma_d == 0$).
  5. Implement budgeted greedy merging with **strict precedence**:
     - Sub-floor segments ($< 3$ chunks) merge with adjacent neighbors.
     - **Precedence Rule:** If merging would push a neighbor $> 12$ chunks (`max_chunks_per_candidate`), the merge is **forbidden**, and the trapped sub-floor segment is preserved with an informational log.
  6. Extract deterministic label (first Markdown heading `#` or sanitized fallback).
  7. Add unit tests for edge cases (1 chunk, 2 chunks, trapped segments, identical plateaus).

### Task 2: Database Schema, Migration & Single-Transaction CRUD (`infrastructure/db.py`)
- **Files:** `infrastructure/db.py`, `core/schemas.py`
- **Tests:** `tests/infrastructure/test_note_candidates_db.py`
- **Actions:**
  1. Add `note_candidates` table definition with `converted_note_uid TEXT UNIQUE REFERENCES notes(uid) ON DELETE SET NULL`.
  2. Add `candidate_uid` and `review_status` columns to `notes` table.
  3. Create idempotent migration script `scripts/migrations/002_add_note_candidates.py`.
  4. Implement single-transaction atomic methods:
     - `insert_note_candidates(source_uid, segments, model_version)`
     - `list_note_candidates(source_uid=None, status='queued')`
     - `get_note_candidate(uid)`
     - `claim_note_candidate(uid, claimed_by, is_human=False)` (uses `agent_claim_ttl_seconds` vs `human_claim_ttl_seconds`)
     - `renew_candidate_lock(uid, claimed_by, ttl_seconds)`
     - `convert_note_candidate_atomic(conn, candidate_uid, note_data, session_id)`: executes lock verification, candidate status update to `converted`, and note insertion in a **single `with conn:` transaction**.
     - `purge_unconverted_candidates(source_uid)` (for re-ingestion cleanup)
  5. Write SQL concurrency, heartbeat renewal, and lock expiration tests.

### Task 3: Ingestion Pipeline Integration & LargeFormat Deprecation (`workflows/ingest.py`)
- **File:** `workflows/ingest.py`
- **Tests:** `tests/workflows/test_ingest.py`
- **Actions:**
  1. Remove legacy `large_format_threshold_tokens` rejection check.
  2. Trigger `segment_chunks` automatically when a source reaches `rag_ready`.
  3. Persist generated candidates into `note_candidates`.
  4. Ensure `finalize_source` allows a source to be finalized while candidates remain in `queued` status.

### Task 4: Drafting, Provenance & Configurable Curate Weights (`tools/vault/`)
- **Files:** `tools/vault/create_note.py`, `tools/vault/update_note.py`, `tools/vault/curate.py`
- **Tests:** `tests/tools/vault/test_create_note.py`, `tests/tools/vault/test_curate.py`
- **Actions:**
  1. Update `create_note` to delegate to `convert_note_candidate_atomic` (raising `ExpiredLockError` if lock lost).
  2. Write provenance to Obsidian YAML frontmatter (`candidate_uid`, `locator`, `chunks`, `review_status`).
  3. In `update_note.py`, sync `review_status` updates from Obsidian Frontmatter to SQLite.
  4. In `curate.py`, factor `review_status` into the confidence score using `settings.system.curate.confidence.reviewed_note_weight` ($1.0$) and `unreviewed_note_weight` ($0.7$).

### Task 5: MCP & CLI Surface Exposure
- **Files:** `mcp/server.py`, `cli/commands/notes.py`, `cli/commands/candidates.py`
- **Tests:** `tests/mcp/test_server.py`, `tests/cli/test_candidates.py`
- **Actions:**
  1. Expose MCP tools:
     - `list_note_candidates(source_uid: str | None, status: str = 'queued')`
     - `get_note_candidate(uid: str)`
     - `claim_note_candidate(uid: str, claimed_by: str, is_human: bool = False)`
     - `renew_candidate_lock(uid: str, claimed_by: str, ttl_seconds: int = 300)`
     - `skip_note_candidate(uid: str)`
     - `get_chunks(chunk_uids: list[str])`
  2. Add CLI commands `egovault candidate list`, `show`, `skip`.

### Task 6: Documentation Alignment & Real-World Vault Validation
- **Files:** `docs/architecture/DATABASES.md`, `CONTRACTS.md`, `ARCHITECTURE.md`, `docs/user-guide/06-mcp.md`, `07-notes.md`
- **Actions:**
  1. Update all architecture docs and user guides.
  2. Run an end-to-end test on real ingested sources in the test vault to verify multi-note topic segmentation.
