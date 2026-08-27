# Data Pipeline Depth Decision Tree (Anti-Overengineering & Pragmatism)

> **Core Philosophy**: Match data architecture complexity to actual data volume, team size, and operational lifespan. Never build an Iceberg Lakehouse with 5 Docker containers for a 500-row Excel conversion, and never write a single spaghetti script for a multi-tenant production data platform.

---

## 🧭 1. The 3-Tier Data Pipeline Decision Matrix

```
                    ┌──────────────────────────────────────────────┐
                    │ What is the data volume, frequency & scope   │
                    │           of this data workload?             │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│  TIER 1 (NANO)   │             │ TIER 2 (MODULAR) │             │  TIER 3 (LAKE)   │
│ Scripts / One-off│             │ Analytics / Apps │             │ Data Platforms   │
│  (< 50k rows)    │             │(50k – 10M rows)  │             │   (> 10M rows)   │
└────────┬─────────┘             └────────┬─────────┘             └────────┬─────────┘
         │                                │                                │
         ▼                                ▼                                ▼
• 1 Python script                • Clean `src/` modular layout    • Lakehouse Platform (Iceberg)
• Stdlib (`csv`, `sqlite3`,      • Polars (`scan_parquet`)        • Apache Iceberg + Nessie / REST
  `pathlib`) or simple Polars    • DuckDB (in-process SQL)        • Git-like Branching (WAP)
• CSV / JSON / Excel / SQLite    • Parquet (ZSTD)                 • Object Storage (MinIO / S3)
• Human-readable files ok        • Medallion (`data/{b,s,g}`)     • Modern DAGs (Dagster / Prefect)
• Simple try/except + logging    • Atomic partition swap          • Watermark-based incremental
• Zero heavy Docker infra        • Dead-Letter Queue (DLQ)        • Automated Quality Assertions
```

---

## 📊 2. Detailed Comparison by Dimension

| Dimension | Tier 1: Nano Script / POC | Tier 2: Modular Pipeline (Default) | Tier 3: Lakehouse Platform (Enterprise) |
| :--- | :--- | :--- | :--- |
| **Typical Target** | One-off CSV cleanup, Excel conversion, ad-hoc API export | Application data backend, periodic daily ETL, RAG knowledge pipeline | Centralized data platform, multi-tenant analytics, multi-source pipeline |
| **Platform Strategy** | Zero-dependency standalone script | Custom Python package (`src/pkg`) | **dbt + Dagster / Prefect + Lakehouse** |
| **File Formats** | **CSV / JSON / SQLite / Parquet** | **Parquet (ZSTD, Snappy)** | **Apache Iceberg over MinIO/S3** |
| **Compute Engine** | Python stdlib (`csv`), simple `polars`/`pandas` | **Polars LazyFrame + DuckDB** | **DuckDB / Spark / PyIceberg** |
| **Storage Layout** | Single file or flat `data/` folder | Structured Medallion: `data/{bronze, silver, gold}` | Iceberg Tables on MinIO with Nessie/REST catalog |
| **Idempotency** | File overwrite mode (`mode="w"`) | **Atomic Partition Swap** (`.replace()`) | **Automated Nessie / Iceberg Branching (WAP)** |
| **Quality Control** | Basic assertions (`assert len(rows) > 0`) | Invariant assertions + **Dead-Letter Queue** | Built-in tests (`not-null`, `unique`, accepted values, custom SQL) |
| **Orchestration** | Single script run / cron | Standalone Python module / Typer CLI | **Dagster / Prefect / Airflow / Cloud Orchestrator** |

---

## 🚫 3. The Two Anti-Pattern Traps

### Trap A: The "Spaghetti Vibe-Pipeline" (Under-Engineering on Real Data)
* **Symptoms**:
  - Loading 5 million rows into Pandas with `pd.read_csv()` and crashing RAM.
  - Blindly appending (`mode="a"`) to a table, causing duplicate rows whenever a pipeline retries.
  - Dropping bad rows silently with `df.dropna()` without logging what was lost or why.
  - Hardcoded absolute paths (`C:\Users\Vincent\Downloads\test.csv`).
* **Remedy**: Upgrade immediately to **Tier 2**. Switch to `pl.scan_parquet()`, use atomic partition overwrite, and route invalid rows to a Dead-Letter Queue.

### Trap B: The "Overengineered Cathedral" (Over-Engineering on Simple Data)
* **Symptoms**:
  - Spinning up 7 Docker containers (MinIO, Nessie, Dagster, PostgreSQL, Redis) just to clean up a 300-row customer list.
  - Forcing Parquet format on a spreadsheet that a human manager needs to open in Microsoft Excel.
  - Writing 8 layers of dbt models for a 20-line aggregation.
* **Remedy**: Downgrade to **Tier 1**. Use a clean, single Python script with `csv` or `polars`, write directly to a formatted CSV (`utf-8-sig` for Excel compatibility), and keep dependencies minimal.

---

## 🧘 4. Universal Invariants (Required in EVERY Tier)

Regardless of whether you write a 20-line script or an enterprise lakehouse:

1. **Idempotence by Design**: Re-running the script must never produce duplicate output or corrupt state.
2. **Never Swallow Failures Silently**: No empty `except: pass`. If an error occurs, log it or crash visibly with context.
3. **Defensive Input Validation**: Verify that source files exist and contain data before starting heavy compute.
4. **Choose Format by Consumer**:
   - If consumed by **Humans / Excel** $\to$ Use **CSV (`encoding='utf-8-sig'`)** or Excel.
   - If consumed by **Machines / Pipelines / Analytics** $\to$ Use **Parquet**.

---

## 🧪 5. Tier 0 — Solo Exploratory / Disposable (Context Override)

A context override, not a volume bracket: applies even past 50k rows when a single person is digging through data once, for a decision that will be made today (a peer-matching sanity check, an ad-hoc join to answer "does this hypothesis hold").

* One script, `pandas` or `polars` eager is fine — the LazyFrame discipline exists to save memory and time on repeated runs, neither of which applies here.
* No Medallion layout, no DLQ — a printed `df.isna().sum()` and a manual eyeball of rejected rows is enough.
* **Upgrade trigger**: the moment the exploration becomes a pipeline someone (including future-you) re-runs on new data — promote to Tier 1/2 immediately, don't let the notebook silently become production.

---

## 🚦 6. When NOT to Reach for Tier 3 (Counter-Cases)

Row count alone does not justify a Lakehouse. Stay at Tier 2 even past 10M rows when:

* **You are the sole consumer and sole operator** — Nessie branching and a REST catalog pay off when multiple teams write concurrently, not when one person runs a nightly script.
* **The data is bounded and won't keep growing** — a one-time 50M-row historical backfill processed once doesn't need a platform built for perpetual ingestion.
* **DuckDB-over-Parquet already answers every query fast enough** — if nothing is timing out or blocking, there is no problem for Iceberg to solve yet.
* **Standing up the platform (Docker, catalog, orchestrator) costs more engineering time than the pipeline itself will ever run** — the classic sign of Trap B.

Tier 3 earns its cost when concurrent writers, time-travel/rollback requirements, or multi-source federation are a near-certainty — not a hypothetical "might scale someday."

---

## 📣 7. Declare Your Tier Before Building

Before writing pipeline code, state the choice in one line so it's visible and correctable by the user rather than silently baked in:

```text
Tier chosen: T{0|1|2|3} — because: {one clause justifying it against volume/frequency/operator-count}
```

If the user disagrees, that's a signal to renegotiate scope, not to silently comply — surface the trade-off.
