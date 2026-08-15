# Spec: Source Segmentation into Notes by Semantic Nucleus

**Date:** 2026-08-14 (Updated: 2026-08-15 — Hardened against all 6 Claude Peer-Review Points)  
**Status:** Validated — Plan-Ready  
**Supersedes:** `.meta/archive/specs/2026-04-06-large-source-synthesis-spec.md` — entirely superseded by this deterministic chunk segmentation design.  
**Related Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md` (Cognitive Architecture, Tier 0 & Tier 2)

---

## 1. Context & Problem Statement

### 1.1 The Discovered Flaw
A multi-topic source reduced to 1 note destroys retrieval recall via semantic averaging (single vector for title + docstring + body). A chunk is a mechanical cut; a note must be a semantic nucleus. **1 source → N notes**.

### 1.2 Deprecation of LargeFormatError
The legacy `LargeFormatError` (which rejected sources $> 50,000$ tokens) is deprecated and removed. All sources flow through the unified pipeline and are automatically segmented into candidates capped at `max_chunks_per_candidate = 12` (~9,600 tokens).

---

## 2. Mathematical Algorithm & Boundary Rules

### 2.1 Step 0: Pre-condition Guardrail (Short Sources)
If total chunk count $N < 2 \times \text{min\_chunks\_per\_note}$ (default: $N < 6$):
- **Bypass segmentation entirely.**
- Produce **exactly 1 candidate** containing all $N$ chunks.

### 2.2 Step 1: Consecutive Similarity & Plateau-Aware Valley Detection
1. Compute the sequence of consecutive cosine similarities:
   $$s_i = \cos(v_i, v_{i+1}) \quad \text{for } i \in [0, N-2]$$
2. Detect local minima with plateau support using weak inequalities ($s_{i-1} \ge s_i \le s_{i+1}$). For plateaus of equal similarity ($s_i = s_{i+1} = \dots = s_{i+m}$), the trough index is placed at the integer midpoint $i + \lfloor m/2 \rfloor$. Indices $0$ and $N-2$ serve as implicit boundary peaks if no inner peak exists.
3. For each local minimum index $i$, calculate its **Valley Depth Score** $d_i$:
   $$d_i = \frac{\max_{\text{left}}(s) + \max_{\text{right}}(s)}{2} - s_i$$
   *(where $\max_{\text{left}}$ and $\max_{\text{right}}$ are the highest similarity peaks flanking $s_i$ before encountering any deeper trough).*
4. Calculate the mean $\mu_d$ and standard deviation $\sigma_d$ of all valley depth scores $d_i$.
5. **Exact Boundary Decision Formula:** A semantic boundary is declared at index $i$ if:
   $$d_i \ge \mu_d + k \cdot \sigma_d \quad \text{OR} \quad s_i < S_{\text{min}}$$
   - If $\sigma_d == 0$ (all depths identical), fallback threshold is $\mu_d + 0.05$.
   - $k = \text{config.system.note\_segmentation.sensitivity\_k}$ (default: $0.5$).
   - $S_{\text{min}} = \text{config.system.note\_segmentation.min\_similarity\_floor}$ (default: $0.35$).

Each contiguous segment between boundaries forms a raw segment $[c_{\text{start}}, \dots, c_{\text{end}}]$.

---

### 2.3 Step 2: Budgeted Merging & Guardrail Precedence Rules

Raw segments are greedily merged (merging the adjacent pair with the highest mean cosine similarity) to satisfy:
1. **Target Floor `min_chunks_per_note = 3` (Soft Target)**: Sub-floor segments ($< 3$ chunks) attempt to merge with their most similar adjacent neighbor.
2. **Ceiling `max_notes_per_source = 30` (Soft Target)**: If segment count $> 30$, merge adjacent pairs down towards 30.
3. **Hard Ceiling `max_chunks_per_candidate = 12` (Strict Invariant)**:
   - **Resolution of Trapped Segments (Point 5):** A merge is **strictly forbidden** if the combined chunk count exceeds $12$.
   - If a sub-floor segment (e.g. 2 chunks) is trapped between two saturated segments of 12 chunks, the hard ceiling **takes absolute precedence**. The trapped segment remains an isolated candidate of 2 chunks, and a log entry is recorded (`logger.info("Preserved sub-floor candidate of size %d due to adjacent ceiling saturation", len(segment))`).

---

## 3. Database Schema, Concurrency & Re-ingestion Lifecycle

### 3.1 Table Definition
```sql
CREATE TABLE note_candidates (
    uid                 TEXT PRIMARY KEY,
    source_uid          TEXT NOT NULL REFERENCES sources(uid) ON DELETE CASCADE,
    sequence_index      INTEGER NOT NULL,
    chunk_uids          TEXT NOT NULL,          -- JSON list ["chk_1", "chk_2", ...]
    label               TEXT NOT NULL,          -- Markdown heading or fallback
    locator             TEXT,                   -- Timestamps, page numbers, or line numbers
    status              TEXT NOT NULL DEFAULT 'queued', -- queued | in_progress | converted | skipped
    claimed_by          TEXT,                   -- Session/agent identifier
    claimed_at          TEXT,                   -- ISO8601 UTC timestamp
    converted_note_uid  TEXT UNIQUE REFERENCES notes(uid) ON DELETE SET NULL,
    model_version       TEXT NOT NULL,          -- Hash of embedding config at segmentation time
    created_at          TEXT NOT NULL
);

CREATE INDEX idx_candidates_source ON note_candidates(source_uid);
CREATE INDEX idx_candidates_status ON note_candidates(status);
```

### 3.2 Human vs. Agent Lock TTL & Renewal (Point 2)
To prevent locking out humans writing in Obsidian while still reclaiming abandoned agent tasks:
- **Agent sessions:** Default TTL = `config.system.note_segmentation.agent_claim_ttl_seconds` ($300\text{ s}$ / 5 min).
- **Human/Manual sessions:** Default TTL = `config.system.note_segmentation.human_claim_ttl_seconds` ($3600\text{ s}$ / 1 hour, or permanent until explicit release).
- **Heartbeat tool:** New MCP/API tool `renew_candidate_lock(candidate_uid, session_id, ttl_seconds)` allows long-running drafts to extend their lock.

### 3.3 Atomic Single-Transaction Note Conversion (Point 3)
The creation of the note and the updating of `note_candidates` occur inside a **single atomic SQLite transaction**:
```python
with conn:
    # 1. Verify lock and update candidate status atomically
    cursor = conn.execute("""
        UPDATE note_candidates
        SET status = 'converted', converted_note_uid = :note_uid
        WHERE uid = :candidate_uid
          AND status = 'in_progress'
          AND claimed_by = :session_id
    """, {"candidate_uid": candidate_uid, "note_uid": note_uid, "session_id": session_id})
    
    if cursor.rowcount == 0:
        raise ExpiredLockError(
            f"Candidate '{candidate_uid}' lock lost or expired.",
            error_code="expired_candidate_lock",
            actionable_hint="Re-claim candidate with claim_note_candidate() before conversion."
        )
    
    # 2. Insert the note referencing candidate_uid
    conn.execute("""
        INSERT INTO notes (uid, source_uid, candidate_uid, title, docstring, body, review_status, ...)
        VALUES (:uid, :source_uid, :candidate_uid, :title, :docstring, :body, :review_status, ...)
    """, note_params)
```

### 3.4 Re-ingestion & PDF Migration Contract (Point 1)
When a source is re-ingested (e.g. Phase 2 PDF layout re-extraction producing new chunks):
1. **Unconverted Candidates (`queued`, `in_progress`, `skipped`):** Are purged from `note_candidates` and re-segmented from the new chunks.
2. **Converted Candidates & Existing Notes:**
   - Existing notes and their `converted` candidate records are **preserved as immutable historical records**.
   - Their `chunk_uids` field is tagged with `"legacy_reingested": true` in candidate metadata.
   - The note's `locator` remains intact for human reading.
   - New un-converted candidates generated from the new PDF parse are created for any newly discovered sections or pages.

---

## 4. Curate Confidence Weighting (Zero-Hardcode — Point 6)

In `config/system.yaml`:
```yaml
curate:
  confidence:
    reviewed_note_weight: 1.0       # Weight for human-reviewed notes
    unreviewed_note_weight: 0.7     # Weight for unreviewed AI drafts
```

`tools/vault/curate.py` reads `ctx.settings.system.curate.confidence.reviewed_note_weight` and `unreviewed_note_weight` directly from `ctx.settings`. Zero magic numbers.
