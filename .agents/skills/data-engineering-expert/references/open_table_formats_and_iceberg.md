# Open Table Formats & Apache Iceberg (Git-Like Lakehouse Architecture)

> **Core Philosophy**: Raw Parquet gives you columnar speed; **Apache Iceberg** gives you database ACID guarantees, time-travel, and Git-like branching on top of object storage. Use Iceberg when multiple writers/readers require atomic commits and zero-copy Write-Audit-Publish isolation.

---

## 🏛️ 1. Why Open Table Formats (Iceberg vs Raw Parquet)

```
┌─────────────────────────────────────────────────────────────┐
│                 RAW PARQUET VS APACHE ICEBERG               │
├──────────────────────────────┬──────────────────────────────┤
│ RAW PARQUET ON S3            │ APACHE ICEBERG ON S3/MINIO   │
│ • No ACID transactions       │ • Full ACID snapshot commits │
│ • Directory listing is slow  │ • Metadata tree (O(1) scan)  │
│ • Schema changes risk breaks │ • Full Schema Evolution      │
│ • Manual partition management│ • Hidden Partitioning        │
│ • No time-travel             │ • Time-Travel & Rollbacks    │
│ • WAP requires folder rename │ • Zero-copy Branching (WAP)  │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🌿 2. Git-Like Branching for Write-Audit-Publish (Nessie & Iceberg Pattern)

Using modern Iceberg table formats with REST or Project Nessie catalogs, you can perform full Write-Audit-Publish (WAP) workflows using zero-copy isolated branches:

```
                  [ Iceberg Table: main branch ]
                                │
                 1. CREATE BRANCH 'run_20260825_001'
                                │
                                ▼
                 2. WRITE TO BRANCH (Isolated Data)
                                │
                                ▼
                 3. AUDIT QUALITY (Run DQ assertions on branch)
                                │
                 ┌──────────────┴──────────────┐
                 ▼ (Audit PASS)                ▼ (Audit FAIL)
       4. FAST-FORWARD MERGE           4. DROP BRANCH
          into 'main' (Atomic)            (Production untouched)
```

### Python PyIceberg Implementation Example:
```python
"""Branch-based Write-Audit-Publish with PyIceberg & REST/Nessie Catalog."""

from pyiceberg.catalog import load_catalog
import pyarrow as pa


def execute_iceberg_wap_publish(
    catalog_name: str,
    table_identifier: str,
    data_arrow: pa.Table,
    run_id: str,
) -> None:
    """Write data to an isolated Iceberg branch, audit, and fast-forward commit."""
    catalog = load_catalog(catalog_name)
    table = catalog.load_table(table_identifier)
    branch_name = f"wap_{run_id}"

    # 1. Create an isolated branch pointer at current head
    table.manage_snapshots().create_branch(branch_name).commit()

    try:
        # 2. Write data to the isolated branch
        table.append(data_arrow, branch=branch_name)

        # 3. Audit quality on the branch snapshot
        branch_snapshot = table.snapshot_by_name(branch_name)
        if branch_snapshot is None:
            raise ValueError(f"Failed to find snapshot for branch {branch_name}")

        # 4. Fast-forward merge: Atomically publish branch to main
        table.manage_snapshots().fast_forward_branch("main", branch_name).commit()
    finally:
        # Cleanup: Remove temporary branch pointer
        try:
            table.manage_snapshots().remove_branch(branch_name).commit()
        except Exception:
            pass
```

---

## ⏱️ 3. Watermark-Based Incremental Processing

Instead of full table reprocessing, use high-watermark state tracking to process only new or updated records:

```python
"""Watermark incremental state extraction with DuckDB & Polars."""

import duckdb
import polars as pl
from pathlib import Path


def extract_incremental_delta(
    con: duckdb.DuckDBPyConnection,
    source_parquet: str,
    watermark_file: Path,
) -> tuple[pl.DataFrame, str]:
    """Read only records arriving after the last recorded watermark."""
    # 1. Read last committed watermark
    last_watermark = "1970-01-01T00:00:00Z"
    if watermark_file.exists():
        last_watermark = watermark_file.read_text(encoding="utf-8").strip()

    # 2. Query delta with DuckDB
    query = f"""
        SELECT *
        FROM read_parquet('{source_parquet}')
        WHERE updated_at > '{last_watermark}'
        ORDER BY updated_at ASC
    """
    df_delta = con.execute(query).pl()

    # 3. Derive new watermark
    if df_delta.height > 0:
        new_watermark = df_delta["updated_at"].max()
    else:
        new_watermark = last_watermark

    return df_delta, str(new_watermark)
```

---

## 🪣 4. DuckDB with S3 / MinIO Object Storage

Query remote cloud object storage directly from local DuckDB instances:

```sql
-- Configure DuckDB S3 / MinIO credentials
INSTALL httpfs;
LOAD httpfs;

SET s3_endpoint = 'minio:9000';
SET s3_use_ssl = false;
SET s3_access_key_id = 'minioadmin';
SET s3_secret_access_key = 'minioadmin';
SET s3_url_style = 'path';

-- Query remote Parquet in MinIO
SELECT count(*) 
FROM read_parquet('s3://warehouse/silver/orders/*.parquet');
```
