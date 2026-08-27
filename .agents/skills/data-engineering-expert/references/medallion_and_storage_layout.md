# Medallion Architecture & Parquet Storage Standards

> **Core Philosophy**: A data lake is not a garbage dump. It is an ordered, 3-tier purification refinery (Bronze $\to$ Silver $\to$ Gold) where data transitions from unparsed verbatim raw capture to clean, typed, high-performance columnar analytical assets.

---

## 🏛️ 1. The 3-Tier Medallion Architecture

```
  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
  │  BRONZE LAYER   │ ───▶ │  SILVER LAYER   │ ───▶ │   GOLD LAYER    │
  │  (Raw Landing)  │      │  (Conformed)    │      │  (Analytics/BI) │
  └────────┬────────┘      └────────┬────────┘      └────────┬────────┘
           │                        │                        │
           ▼                        ▼                        ▼
  • Verbatim source payload• Strict PyArrow schema  • Star schema (dim/fct)
  • Append-only & immutable• Cleaned & cast types   • Aggregated metrics
  • Timestamped receipt    • Deduplicated by PK     • Optimized for queries
  • Parquet / Raw JSON     • Partitioned by date    • Parquet / DuckDB / DWH
```

### A. Bronze Layer (Raw / Ingestion Valve)
* **Contract**: Zero destructive transformation. Store the exact raw input with system ingestion metadata.
* **Required Metadata Columns**:
  - `_bronze_receipt_ts`: UTC ISO8601 timestamp when the pipeline received the data.
  - `_bronze_source_file`: Name or URI of the originating file/stream.
  - `_bronze_run_id`: Unique execution run identifier.
* **Storage format**: Partitioned Parquet or compressed raw JSONL.

### B. Silver Layer (Cleaned / Conformed Core)
* **Contract**: Single source of truth for business entities.
* **Transformations**:
  - Cast strings to strict native types (dates, floats, integers, enums).
  - Deduplicate on primary business keys (`id`, `order_id`).
  - Standardize column names (`snake_case`).
  - Route malformed rows to a **Dead-Letter Queue (DLQ)** (`silver_rejections/`).
* **Storage format**: Partitioned Parquet with ZSTD compression.

### C. Gold Layer (Business Marts / Analytical Products)
* **Contract**: Consumption-ready for BI dashboards, ML feature stores, and LLM context curation.
* **Transformations**:
  - Pre-computed rollups and metrics (e.g. `daily_active_users`, `revenue_by_cohort`).
  - Dimensional models: Fact tables (`fct_orders`) joined with Dimension tables (`dim_customers`).
  - Wide / One Big Table (OBT) formats for low-latency analytical queries.

---

## 📦 2. Parquet Storage Optimization Standards

Apache Parquet is a columnar binary format with rich embedded statistics (min, max, null counts per column).

```
┌─────────────────────────────────────────────────────────────┐
│                    PARQUET FILE ANATOMY                     │
├─────────────────────────────────────────────────────────────┤
│  Header (PAR1)                                              │
├─────────────────────────────────────────────────────────────┤
│  Row Group 1 (100k - 1M rows)                               │
│  ├── Column Chunk A (Dictionary + ZSTD Data Pages)          │
│  └── Column Chunk B (RLE / Snappy Data Pages)               │
├─────────────────────────────────────────────────────────────┤
│  Row Group 2 (100k - 1M rows)                               │
│  ├── Column Chunk A ...                                     │
│  └── Column Chunk B ...                                     │
├─────────────────────────────────────────────────────────────┤
│  Footer Metadata: File Schema, Column Stats (Min/Max/Nulls) │
└─────────────────────────────────────────────────────────────┘
```

### A. File Sizing Standard (The "Small Files" Problem)
* ❌ **Anti-Pattern**: Writing thousands of 200KB `.parquet` files per hour. This destroys query engine performance due to excessive filesystem metadata calls and tiny row groups.
* ✅ **Best Practice**: Target **128 MB to 512 MB per Parquet file**.
* For streaming pipelines, buffer micro-batches in memory or landing storage and compact daily into consolidated 128MB+ files using a compaction worker.

### B. Row Group Tuning (Parallel Processing Units)
* Row groups dictate the parallelism granularity for Polars, DuckDB, and Spark.
* **Optimal Row Group Size**: **100,000 to 1,000,000 rows** (approx. 32MB to 64MB uncompressed per row group).
* If row groups are too small (<10,000 rows), metadata overhead skyrockets; if too large (>5,000,000 rows), out-of-core memory pressure spikes on individual threads.

### C. Compression Codec Matrix

| Codec | Level | Speed | Compression Ratio | Best Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **ZSTD** (Recommended) | `level=3` | Fast | ⭐⭐⭐⭐⭐ (Highest) | Default for Silver and Gold analytical storage |
| **Snappy** | Default | Ultra-fast | ⭐⭐⭐ (Moderate) | High-throughput streaming ingestion |
| **GZIP** | - | Slow | ⭐⭐⭐⭐ | ❌ Avoid for Parquet (legacy, CPU heavy) |

---

## 🗂️ 3. Partitioning Strategy (Hive Style vs Over-Partitioning)

Partitioning splits data into subdirectories (`dt=YYYY-MM-DD/country=FR/`) allowing query engines to skip entire directories (*Partition Pruning*).

### A. The Cardinality Rule
* **Only partition on low-cardinality, query-heavy keys** (e.g. `year_month=2026-08` or `dt=2026-08-24`).
* ❌ **Anti-Pattern (Cardinality Explosion)**: Partitioning on `user_id`, `hour`, or `uuid`. Creating 100,000 folders with 5KB files will choke query engines.

### B. Standard Layout
```text
data/
├── bronze/
│   └── dt=2026-08-24/
│       └── raw_events_run_001.parquet
├── silver/
│   └── orders/
│       ├── dt=2026-08-24/
│       │   └── part_0.parquet (128 MB, zstd)
│       └── dt=2026-08-25/
│           └── part_0.parquet
└── gold/
    ├── fct_daily_revenue/
    │   └── part_0.parquet
    └── dim_customers/
        └── part_0.parquet
```
