# Orchestration & Modern Pipeline Tooling (`uv`, Dagster, dbt)

> **Core Philosophy**: A production data pipeline is an asset-oriented dependency graph. Orchestrate workflows with explicit inputs, deterministic outputs, automatic retries with backoff, and modern Rust-backed package management (`uv`).

---

## ⚡ 1. The Modern Python Data Stack Toolchain

```toml
# pyproject.toml
[project]
name = "my-data-pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "polars[all]>=1.5.0",
    "duckdb>=1.0.0",
    "pyarrow>=17.0.0",
    "pandera[polars]>=0.20.0",
    "pydantic-settings>=2.4.0",
    "loguru>=0.7.2",
    "tenacity>=8.5.0",
    "typer>=0.12.0",
]

[project.optional-dependencies]
dbt = [
    "dbt-core>=1.8.0",
    "dbt-duckdb>=1.8.0",
]
orchestration = [
    "dagster>=1.8.0",
]
dev = [
    "pytest>=8.3.0",
    "ruff>=0.5.0",
]
```

---

## 🏗️ 2. Complete End-to-End Pipeline Skeleton

Here is a complete, production-grade local pipeline implementing Medallion layout, WAP pattern, and run manifest generation:

```python
"""Production Data Pipeline Skeleton: Bronze -> Silver -> Gold."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

import duckdb
from loguru import logger
import polars as pl


import os
import shutil


def run_pipeline(source_file: Path, base_data_dir: Path) -> dict:
    """Execute complete end-to-end Medallion pipeline run."""
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = time.perf_counter()
    logger.info("Starting pipeline run {run_id}", run_id=run_id)

    # ----------------------------------------------------
    # 1. BRONZE: Raw Ingestion (Landing with Lazy Streaming)
    # ----------------------------------------------------
    bronze_dir = base_data_dir / "bronze" / f"run_id={run_id}"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    bronze_file = bronze_dir / "raw_events.parquet"

    # Scan and sink with receipt metadata (zero-memory full buffer loading)
    lazy_raw = pl.scan_csv(source_file).with_columns(
        _bronze_receipt_ts=pl.lit(datetime.now(timezone.utc).isoformat()),
        _bronze_run_id=pl.lit(run_id),
    )
    lazy_raw.sink_parquet(bronze_file, compression="zstd")
    bronze_row_count = pl.scan_parquet(bronze_file).select(pl.len()).collect().item()
    logger.info("Bronze layer written: {rows} records", rows=bronze_row_count)

    # ----------------------------------------------------
    # 2. SILVER: Clean, Validate & Dead-Letter Queue
    # ----------------------------------------------------
    silver_dir = base_data_dir / "silver" / "orders"
    silver_staging = base_data_dir / "silver" / f"_staging_{run_id}"
    dlq_dir = base_data_dir / "silver_rejections"
    silver_staging.mkdir(parents=True, exist_ok=True)
    dlq_dir.mkdir(parents=True, exist_ok=True)

    # Lazy scan from Bronze
    silver_lazy = pl.scan_parquet(bronze_file).with_columns(
        order_id=pl.col("id").cast(pl.String),
        amount=pl.col("amount").cast(pl.Float64),
        created_at=pl.col("date").str.to_datetime(),
    )

    # Quality filter
    valid_mask = pl.col("order_id").is_not_null() & (pl.col("amount") > 0.0)
    clean_df = silver_lazy.filter(valid_mask).collect(streaming=True)
    rejected_df = (
        silver_lazy.filter(~valid_mask)
        .with_columns(rejection_reason=pl.lit("ERR_INVALID_ORDER_OR_AMOUNT"))
        .collect()
    )

    # Write Staged Silver & DLQ
    staged_silver_file = silver_staging / "orders.parquet"
    clean_df.write_parquet(staged_silver_file, compression="zstd")
    if rejected_df.height > 0:
        rejected_df.write_parquet(dlq_dir / f"rejections_{run_id}.parquet", compression="zstd")

    # WAP Gate: Atomic publish with cross-platform safety
    silver_dir.mkdir(parents=True, exist_ok=True)
    target_silver_file = silver_dir / "orders.parquet"
    os.replace(staged_silver_file, target_silver_file)
    shutil.rmtree(silver_staging, ignore_errors=True)
    logger.info(
        "Silver published: {rows} clean, {rejected} rejected",
        rows=clean_df.height,
        rejected=rejected_df.height,
    )

    # ----------------------------------------------------
    # 3. GOLD: Analytical Aggregations (DuckDB)
    # ----------------------------------------------------
    gold_dir = base_data_dir / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold_output = gold_dir / "daily_revenue.parquet"

    con = duckdb.connect()
    con.execute(f"""
        COPY (
            SELECT 
                CAST(created_at AS DATE) as order_date,
                COUNT(DISTINCT order_id) as total_orders,
                ROUND(SUM(amount), 2) as daily_revenue
            FROM read_parquet('{(silver_dir / "orders.parquet").as_posix()}')
            GROUP BY order_date
            ORDER BY order_date DESC
        ) TO '{gold_output.as_posix()}' (FORMAT PARQUET, CODEC 'ZSTD');
    """)
    logger.info("Gold analytical mart compiled with DuckDB")

    # ----------------------------------------------------
    # 4. MANIFEST: Execution Provenance
    # ----------------------------------------------------
    elapsed = time.perf_counter() - start_time
    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(elapsed, 3),
        "bronze_rows": bronze_row_count,
        "silver_clean_rows": clean_df.height,
        "silver_rejected_rows": rejected_df.height,
        "status": "SUCCESS",
    }
    manifest_file = base_data_dir / "manifests" / f"run_{run_id}.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest
```

---

## 🧭 3. Asset-Oriented Orchestration (Dagster & Modern Schedulers)

In production Tier 2 / Tier 3 environments, wrap the Medallion stages as **Software-Defined Assets (SDA)**:

```python
"""Declarative Asset-Oriented Pipeline with Dagster."""

from dagster import asset, AssetExecutionContext
import polars as pl
from pathlib import Path


@asset(group_name="medallion")
def raw_orders_bronze(context: AssetExecutionContext) -> Path:
    """Ingest landing CSV into raw immutable Bronze Parquet."""
    output_path = Path("data/bronze/orders.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pl.scan_csv("data/landing/orders.csv").sink_parquet(output_path, compression="zstd")
    return output_path


@asset(deps=[raw_orders_bronze], group_name="medallion")
def clean_orders_silver(context: AssetExecutionContext) -> Path:
    """Conform and validate Bronze into Silver with DLQ auditing."""
    output_path = Path("data/silver/orders.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Lazy transform & streaming WAP publish
    lazy = pl.scan_parquet("data/bronze/orders.parquet")
    valid = lazy.filter(pl.col("id").is_not_null())
    valid.sink_parquet(output_path, compression="zstd")
    return output_path
```

