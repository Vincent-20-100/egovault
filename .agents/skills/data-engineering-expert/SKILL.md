---
name: data-engineering-expert
description: >-
  Data Engineering, Pipeline & Relational Database Architect guidance for building high-performance, robust,
  and auditable data systems — from OLTP schema design to analytical pipelines. Enforces Modern Data Stack
  standards: Polars LazyFrames & Streaming, DuckDB in-process OLAP, Apache Arrow & Parquet columnar layouts,
  3-layer dbt/SQL modeling (Staging -> Intermediate -> Marts), Medallion Architecture (Bronze -> Silver -> Gold),
  Write-Audit-Publish (WAP) idempotency, Data Contracts & Schema enforcement, Dead-Letter Queue (DLQ) rejection
  auditing, relational normalization & key typology, advanced modeling (state/status history, hierarchies,
  supertype/subtype) and classic SQL traps (fan trap, chasm trap, NULL semantics).
  Use whenever designing a database schema, building/optimizing/auditing data pipelines, ETL/ELT workflows,
  or writing/reviewing SQL models and queries.
---

# Modern Data Engineering & Relational Database Framework (`data-engineering-expert`)

Act as a **Staff Data Engineer & Database Architect**. Your goal is to produce **high-performance, memory-efficient, deterministic, and auditable data systems** — from correctly normalized OLTP schemas to analytical pipelines — eliminating amateur anti-patterns (eager pandas memory crashes, non-idempotent blind appends, silent row dropping, nested SQL spaghetti, unenforceable polymorphic FKs, boolean-soup status columns) while strictly leveraging columnar processing (Parquet, Polars, DuckDB, Arrow, dbt) and sound relational modeling.

---

## 🧭 Fast Reference Trigger Matrix

Consult the appropriate reference guide depending on the specific pipeline task:

| Topic & Trigger | Reference Guide | Key Takeaway / Scope |
| :--- | :--- | :--- |
| **Architecture Sizing** *(Script vs Modular vs Lake)* | [./references/pipeline_depth_decision_tree.md](./references/pipeline_depth_decision_tree.md) | Tier 0 (solo/disposable) · Tier 1 <50k · Tier 2 50k–10M · Tier 3 >10M, plus counter-cases against Tier 3. |
| **Relational & Dimensional Modeling** | [./references/database_modeling_and_relations.md](./references/database_modeling_and_relations.md) | Normalization (1NF-BCNF) & key typology, OLTP 3NF vs OLAP Star Schema, 1:1 / 1:N / N:M, foreign keys & indexes. |
| **Advanced Relational Patterns & SQL Traps** | [./references/advanced_relational_patterns_and_sql_traps.md](./references/advanced_relational_patterns_and_sql_traps.md) | State/status modeling, temporal & bitemporal design, hierarchies, supertype/subtype, polymorphic-association anti-pattern, fan trap, chasm trap, NULL semantics. |
| **SQL Dialect Syntax & Optimization** | [./references/sql_dialect_syntax_reference.md](./references/sql_dialect_syntax_reference.md) | Cross-engine join/function syntax gaps (Postgres/MySQL/SQL Server/SQLite/DuckDB), index & query optimization pitfalls. |
| **Open Table Formats & ACID Lakehouse** | [./references/open_table_formats_and_iceberg.md](./references/open_table_formats_and_iceberg.md) | Apache Iceberg, Nessie branching WAP, watermarks, S3/MinIO. |
| **Medallion & Storage Optimization** | [./references/medallion_and_storage_layout.md](./references/medallion_and_storage_layout.md) | Bronze $\to$ Silver $\to$ Gold, row group sizing (100k–1M), ZSTD compression. |
| **Polars High Performance & Vectorization** | [./references/polars_high_performance_guide.md](./references/polars_high_performance_guide.md) | LazyFrames, `scan_*`, `sink_parquet`, streaming, anti-UDF expressions. |
| **DuckDB In-Process OLAP & SQL** | [./references/duckdb_and_olap_sql_mastery.md](./references/duckdb_and_olap_sql_mastery.md) | Out-of-core SQL, zero-copy Arrow interop, Parquet globbing & export. |
| **dbt & SQL Modeling Standard** | [./references/dbt_and_sql_data_modeling.md](./references/dbt_and_sql_data_modeling.md) | 3-layer DAG (`stg_` $\to$ `int_` $\to$ `fct_`/`dim_`), CTE standards, incremental models. |
| **Data Contracts & Schema Validation** | [./references/data_contracts_and_schemas.md](./references/data_contracts_and_schemas.md) | PyArrow explicit schemas, Pandera validation, schema drift handling. |
| **Idempotency & Atomic Publishing** | [./references/idempotency_and_pipeline_axioms.md](./references/idempotency_and_pipeline_axioms.md) | Write-Audit-Publish (WAP), atomic partition swaps, Dead-Letter Queue (DLQ). |
| **Data Quality, Tests & Observability** | [./references/data_quality_and_observability.md](./references/data_quality_and_observability.md) | Circuit breakers, invariant checks, volume drift detection, run manifests. |
| **Orchestration & Production Tooling** | [./references/orchestration_and_tooling.md](./references/orchestration_and_tooling.md) | End-to-end Python pipeline skeleton, Dagster/Prefect patterns, `uv` toolchain. |

---

## 🎨 0. Engineering Precedence

Full doctrine: [`../../rules/engineering_precedence.md`](../../rules/engineering_precedence.md) (Project conventions > User directives > Consultative standards; declare your tier first).

Tier calibration specific to this skill (by row volume):
| Tier | Scope | Stack |
|---|---|---|
| 1 | <50k rows / one-off script | Standard library (`csv`, `json`, `sqlite3`) or simple Polars |
| 2 | 50k–10M rows / recurring pipeline | Polars LazyFrame + DuckDB + Parquet (ZSTD) + Medallion |
| 3 | >10M rows / enterprise platform | Apache Iceberg/Delta Lake + Nessie WAP + dbt-core + Dagster/Prefect |

---

## 🌟 1. Core Operating Principles (The 6 Pillars)

0. **Declare Your Tier First**: Before building a pipeline, state `Tier chosen: T{0|1|2|3} — because: {reason}`. See [./references/pipeline_depth_decision_tree.md](./references/pipeline_depth_decision_tree.md) for the Tier 0 (solo/disposable) override and the counter-cases against reaching for a Lakehouse.
1. **Columnar First by Default**: Store intermediate and analytical data in Apache Parquet compressed with ZSTD or Snappy. Never use CSV or JSON for inter-stage storage. Target 128MB–512MB file sizes with 100k–1M row groups.
2. **Lazy & Streaming Evaluation**: Always use `pl.scan_parquet()`, `pl.scan_csv()`, `lazy_df.sink_parquet()`, or DuckDB queries instead of eagerly loading entire datasets into RAM (`pl.read_csv`, `pd.read_parquet`). Leverage query optimizer pushdowns (predicate & projection).
3. **Medallion Layer Separation**:
   * **Bronze (Raw Landing)**: Verbatim, immutable, timestamped (`_bronze_receipt_ts`).
   * **Silver (Cleaned / Conformed)**: Validated, typed, deduplicated, partitioned.
   * **Gold (Business Marts)**: Aggregated, consumption-ready star schemas or wide tables.
4. **Strict Idempotency (WAP Pattern)**: Re-running a pipeline on partition `2026-08-24` 1 time or 100 times must produce the exact same deterministic state. Always use atomic partition overwrites; never blind appends.
5. **Rejection is Evidence (Dead-Letter Queue)**: Never silently drop malformed or invalid records with `df.filter()` or `dropna()`. Route invalid rows to a `rejections/` quarantine table tagged with reason codes and measured values.
6. **Data Contracts & Provenance**: Enforce explicit PyArrow schemas at boundaries. Generate an immutable **Execution Manifest** for every batch (run ID, input hashes, code version, output rows, duration).

---

## 🧭 2. Quick Engine Decision Matrix

| Engine | Best for |
|---|---|
| **Polars** (Python/Rust) | Complex transforms, custom business math, streaming & window functions, fast file parsing |
| **DuckDB** (in-process SQL) | Analytical SQL queries, multi-Parquet joins, zero-copy Arrow export, fast OLAP aggregations |
| **dbt-core** (warehouse SQL) | Large-scale data teams, DAG lineage & staging, team collaboration, metric layers & docs |

---

## 🛠️ Automated Parquet & Pipeline Inspection

Inspect Parquet file metadata, row group counts, column encodings, and null statistics without loading data into memory:

```bash
python scripts/parquet_pipeline_inspector.py data/silver/orders.parquet --verbose
```

---

## 🔄 Maintenance

Protocol: [`../../rules/skill_maintenance_protocol.md`](../../rules/skill_maintenance_protocol.md).

