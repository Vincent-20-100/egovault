# Idempotency & Pipeline Axioms (The Write-Audit-Publish Pattern)

> **Golden Rule**: Every data pipeline run must be 100% idempotent and deterministic. Executing a pipeline 1 time or 100 times against partition `2026-08-24` must result in the exact same state, with zero duplicate rows and zero manual cleanup required.

---

## 🔁 1. The Write-Audit-Publish (WAP) Pattern

The **WAP Pattern** guarantees that bad, corrupted, or incomplete data is never visible to production consumers.

```
┌─────────────────────────────────────────────────────────────┐
│                 WRITE-AUDIT-PUBLISH WORKFLOW                │
├─────────────────────────────────────────────────────────────┤
│ 1. WRITE (Isolation)                                        │
│    Write output to staging partition `_staging/dt=2026-08/` │
│    Inaccessible to production queries.                      │
├─────────────────────────────────────────────────────────────┤
│ 2. AUDIT (Automated Gate)                                   │
│    Run Quality Assertions (Row counts > 0, Null % < 1%,     │
│    Unique PKs, Amount sum delta within 5% of historical).   │
├─────────────────────────────────────────────────────────────┤
│ 3. PUBLISH (Atomic Swap)                                    │
│    If Audit PASS ➔ Atomic Directory Rename / Symlink Swap   │
│    If Audit FAIL ➔ Alert + Route to Quarantine / DLQ        │
└─────────────────────────────────────────────────────────────┘
```

### Python / Filesystem Atomic Swap Implementation:
```python
"""Atomic partition publisher enforcing the WAP pattern."""

from pathlib import Path
import shutil
import uuid
import polars as pl


def publish_partition_atomically(
    df: pl.DataFrame,
    target_dir: Path,
    partition_name: str,
) -> None:
    """Write DataFrame to staging, validate, and atomically publish."""
    target_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = target_dir / f"_staging_{uuid.uuid4().hex[:8]}"
    final_partition_dir = target_dir / partition_name

    staging_dir.mkdir(parents=True, exist_ok=True)
    staging_file = staging_dir / "part_0.parquet"

    # Step 1: WRITE
    df.write_parquet(staging_file, compression="zstd")

    # Step 2: AUDIT
    staged_df = pl.scan_parquet(staging_file)
    row_count = staged_df.select(pl.len()).collect().item()
    if row_count == 0:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise ValueError("Audit failed: Partition contains 0 rows.")

    # Step 3: PUBLISH (Atomic replace with rollback safety)
    backup_dir = target_dir / f"_backup_{partition_name}_{uuid.uuid4().hex[:8]}"

    if final_partition_dir.exists():
        final_partition_dir.rename(backup_dir)

    try:
        staging_dir.rename(final_partition_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
    except Exception:
        # Rollback on failure
        if backup_dir.exists() and not final_partition_dir.exists():
            backup_dir.rename(final_partition_dir)
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
```

---

## 🚫 2. Banning Blind Appends (`APPEND` Anti-Pattern)

* ❌ **The Fatal Trap**: Using `df.write_parquet(..., mode="append")` or `INSERT INTO ...` on a schedule. If a network blip causes a retry, or if a backfill is run twice, data is silently duplicated.
* ✅ **The Senior Rule**: Use **Partition Overwrites** (`INSERT OVERWRITE PARTITION (dt='...')`) or **Atomic Upserts** with idempotency keys (`ON CONFLICT (id) DO UPDATE`).

---

## 🗄️ 3. Dead-Letter Queue (DLQ): Rejection is Evidence

* ❌ **Anti-Pattern**: Filtering out dirty rows with `df.filter(is_valid)` and discarding the rest into `/dev/null`.
* ✅ **The Rule**: Never silently drop data. Bad data is mission-critical evidence for upstream debugging. Route rejected records to a **Dead-Letter Queue (DLQ)** table tagged with explicit reason codes:

```python
"""Separating clean records from QC rejections with explicit audit tags."""

import polars as pl
from datetime import datetime, timezone


def process_with_rejection_audit(raw_df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Split dataset into clean data and rejected audit records."""
    now_utc = datetime.now(timezone.utc).isoformat()

    # Define quality conditions
    has_valid_id = pl.col("order_id").is_not_null() & (pl.col("order_id") != "")
    has_valid_amount = pl.col("amount").is_not_null() & (pl.col("amount") > 0.0)

    # 1. Clean partition
    clean_df = raw_df.filter(has_valid_id & has_valid_amount)

    # 2. Tagged Rejections
    rejected_df = raw_df.filter(~(has_valid_id & has_valid_amount)).with_columns(
        rejected_at=pl.lit(now_utc),
        rejection_reason=pl.when(~has_valid_id)
        .then(pl.lit("ERR_INVALID_OR_MISSING_ID"))
        .when(~has_valid_amount)
        .then(pl.lit("ERR_NEGATIVE_OR_ZERO_AMOUNT"))
        .otherwise(pl.lit("ERR_UNKNOWN_VALIDATION")),
    )

    return clean_df, rejected_df
```

---

## 📜 4. The Immutable Run Manifest (Lineage Tracking)

Every pipeline job must emit a machine-readable JSON manifest stored alongside the data partition:

```json
{
  "run_id": "2026-08-24_ingest_orders_004",
  "pipeline_version": "v2.1.0",
  "executed_at": "2026-08-24T23:15:00Z",
  "source_inputs": [
    {
      "path": "s3://raw-landing/orders/dt=2026-08-24/part-0.jsonl",
      "sha256": "4f9a8b2..."
    }
  ],
  "target_partition": "data/silver/orders/dt=2026-08-24/",
  "metrics": {
    "rows_ingested": 54200,
    "rows_published": 54188,
    "rows_rejected": 12,
    "duration_seconds": 3.42,
    "output_bytes": 14205800
  },
  "status": "SUCCESS"
}
```
