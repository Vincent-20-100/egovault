# Industrial Engineering Axioms & Data Provenance (Institutional Grade)

> **Inspiration & Pedigree**: Extracted from institutional quantitative systems and mission-critical production engines. These rules elevate Python code from amateur "vibe-coding" or notebook experimentation to robust, auditable industrial software.

---

## 🏛️ 1. The 7 Industrial Axioms

```
   ┌──────────────────────────────────────────────────────────────────┐
   │                 7 INSTITUTIONAL ENGINEERING AXIOMS               │
   ├────────────────────────────────┬─────────────────────────────────┤
   │ 1. DETERMINISM & PROVENANCE    │ 5. PURE ENGINES VS I/O          │
   │    Code + Config + Input = Out │    No side-effects in math      │
   ├────────────────────────────────┼─────────────────────────────────┤
   │ 2. SAME-CODE REPLAY INVARIANT  │ 6. SCALAR FIRST, BATCH SECOND   │
   │    Zero dual-path drift        │    Test edge cases on scalars   │
   ├────────────────────────────────┼─────────────────────────────────┤
   │ 3. NEVER HIDE FALLBACKS        │ 7. PERSIST REJECTS AS EVIDENCE  │
   │    Degraded mode is an output  │    QC reason codes on discard   │
   ├────────────────────────────────┼─────────────────────────────────┤
   │ 4. CONFIG HASH != CODE VERSION │                                 │
   │    Independent lineage keys    │                                 │
   └────────────────────────────────┴─────────────────────────────────┘
```

---

## 🧭 2. Deep Dive on Each Axiom

### Axiom 1: Determinism & Provenance (The Job Manifest)
Given the same raw inputs, same configuration version, and same code version, the system **must** produce byte-for-byte identical outputs.
Every batch job or data transformation must produce an immutable **Execution Manifest**:

```json
{
  "run_id": "2026-08-24_batch_001",
  "environment": "production",
  "code_version": "v1.4.2",
  "config_hashes": {
    "system": "sha256:8f4c2e...",
    "business_rules": "sha256:3b1a9c..."
  },
  "input_partitions": ["data/raw/dt=2026-08-24/part-0.parquet"],
  "output_partitions": ["data/curated/dt=2026-08-24/analytics.parquet"],
  "records_processed": 14250,
  "records_rejected": 12,
  "status": "SUCCESS",
  "duration_seconds": 4.18
}
```

---

### Axiom 2: The Same-Code Path Invariant (Live vs Replay / Test)
* **The Anti-Pattern**: Writing a live streaming processor, and then writing a separate "historical backtest" or "batch script" doing similar logic. Dual code paths **always** drift and cause silent divergence.
* **The Rule**: Historical backfill, unit testing, and live execution **must call the exact same core functions and classes**. Only the I/O adapter (streaming socket vs parquet replay reader) changes.

---

### Axiom 3: Never Hide Fallback Behavior
* If an algorithm falls back to an alternative calculation (e.g. using previous day's close when live spread is too wide, or linear interpolation when a curve fit fails), **never hide it in a log message**.
* **The Rule**: Expose the fallback explicitly in the returned data model / schema as a status flag:
```python
@dataclass(frozen=True)
class PriceSnapshot:
    price: float
    reference_type: str  # "MID_LIVE", "LAST_TRADE", "OFFICIAL_CLOSE", "INTERPOLATED_FALLBACK"
    is_fallback: bool
    quality_score: float
```

---

### Axiom 4: Never Silently Drop Items in QC (Rejection is Evidence)
* **The Anti-Pattern**: Filtering out invalid rows with `df[df['spread'] < 0.2]` without tracking what was excluded.
* **The Rule**: Quality Control (QC) must produce both a **Clean Dataset** and a **Rejection Table** tagged with explicit, stable reason codes (`ERR_SPREAD_TOO_WIDE`, `ERR_STALE_TIMESTAMP`, `ERR_NEGATIVE_BID`):

```python
@dataclass(frozen=True)
class QCRejection:
    record_id: str
    reason_code: str
    measured_value: float
    threshold_applied: float
    context: dict
```

---

### Axiom 5: Pure Computational Kernels (Zero I/O in Math)
* Separate calculations from side-effects:
  - **Ingestion Callbacks**: Normalize, timestamp (`receipt_ts`, `canonical_ts`), and write to storage. Zero heavy math in callbacks.
  - **Calculation Engines**: Pure functions `(Inputs, Config) -> Output`. No database queries, no network calls, no system clock queries (`datetime.now()`) inside the math loop (pass timestamps as parameters).

---

### Axiom 6: Scalar First, Vectorized Second
* When implementing numerical models, root solvers, or complex business logic:
  1. Write and test the **pure scalar function** first (`calculate_item(x, y)`). Test edge cases (zeros, infinities, negatives, NaN).
  2. Build the **vectorized / batch wrapper** second (`calculate_batch(items)`).
* Debugging is 10x faster and unit test fixtures are trivial to maintain.

---

### Axiom 7: Normalized Timestamp Disambiguation
Never use a single generic `timestamp` field. Differentiate event chronology explicitly:
* `exchange_ts` / `source_ts`: When the event occurred at the origin.
* `receipt_ts`: When your application ingested the event.
* `canonical_ts` / `snapshot_ts`: The aligned discrete bucket time used for downstream calculation.
