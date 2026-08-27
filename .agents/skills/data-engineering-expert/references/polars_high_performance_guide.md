# Polars High-Performance Pipeline Guide (Rust-Backed Speed)

> **Golden Rule**: Never treat Polars as "just a faster Pandas". Polars is a compiled, vectorized, multi-threaded query engine. Write declarative expressions on `LazyFrame` and let the query optimizer parallelize across all CPU cores.

---

## ⚡ 1. The Core Paradigm: Lazy by Default (`scan_parquet`)

```
┌─────────────────────────────────────────────────────────────┐
│                    THE POLARS QUERY LIFECYCLE               │
├─────────────────────────────────────────────────────────────┤
│ 1. DECLARE INTENT   ➔ pl.scan_parquet("data/*.parquet")     │
│ 2. OPTIMIZE PLAN    ➔ Predicate Pushdown (Filter Early)     │
│                     ➔ Projection Pushdown (Read Few Columns)│
│ 3. EXECUTE STREAM   ➔ .collect(streaming=True) (Batched RAM)│
└─────────────────────────────────────────────────────────────┘
```

### A. Eager vs Lazy Execution:

```python
import polars as pl

# ❌ ANTI-PATTERN: Eager read loads 10GB into RAM immediately
# df = pl.read_parquet("large_dataset/*.parquet")
# result = df.filter(pl.col("country") == "FR").select(["id", "revenue"])

# ✅ SENIOR PATTERN: Lazy scan pushes filters down to the Parquet reader
lazy_query = (
    pl.scan_parquet("large_dataset/*.parquet")
    .filter(pl.col("country") == "FR")
    .select(["id", "revenue", "created_at"])
)

# Execution Strategy 1: Streaming in-memory collection
df_result = lazy_query.collect(streaming=True)

# Execution Strategy 2: Direct streaming sink to disk (Zero full-dataset RAM allocation)
lazy_query.sink_parquet("data/silver/orders.parquet", compression="zstd")
```

---

## 🚫 2. The 5 Polars Anti-Patterns to Ban

### Anti-Pattern 1: Python UDFs (`.map_elements()` or `.apply()`)
* **Why it breaks**: Drops out of Rust multi-threaded C-speed and invokes the Python GIL on every row.
* **Fix**: Use native Polars expressions:

```python
# ❌ Anti-pattern: 100x slower
# df.with_columns(status=pl.col("score").map_elements(lambda s: "PASS" if s > 0.8 else "FAIL"))

# ✅ Idiomatic Polars Expression:
df = df.with_columns(
    status=pl.when(pl.col("score") > 0.8)
    .then(pl.lit("PASS"))
    .otherwise(pl.lit("FAIL"))
)
```

### Anti-Pattern 2: Iterating with `for row in df.iter_rows()`
* **Why it breaks**: Reconstructs Python objects for millions of rows.
* **Fix**: Use vectorized window functions (`.over()`), cumulative expressions, or `.group_by()`.

### Anti-Pattern 3: Unnecessary `.to_pandas()` in ETL Logic
* **Why it breaks**: Copies entire memory buffers into Pandas' single-threaded structure.
* **Fix**: Stay in Polars for all transformation, filtering, joining, and aggregation. Convert to Pandas only at the very final step if calling an external visualization tool.

### Anti-Pattern 4: Filtering After Heavy Sorting
* **Why it breaks**: Sorting millions of rows before discarding 90% of them wastes CPU.
* **Fix**: Always place `.filter()` as early as possible in your transformation chain.

### Anti-Pattern 5: Bloated 64-bit Data Types
* **Why it breaks**: Storing small integers as `Int64` or categories as raw `String` doubles memory footprint.
* **Fix**: Downcast intentionally:
  - `pl.Int32` or `pl.Int16` for identifiers / counters.
  - `pl.Float32` for metrics / ratios.
  - `pl.Enum` or `pl.Categorical` for low-cardinality string columns.

---

## 🚀 3. Essential High-Performance Expression Patterns

### A. Window Functions (`.over()`) without Group-By Explosion
Compute group metrics (e.g. customer ranking, running totals) directly in-place:

```python
# Calculate running customer spend and rank in a single pass
enriched_df = df.with_columns(
    customer_total_spend=pl.col("amount").sum().over("customer_id"),
    order_rank=pl.col("created_at").rank(descending=True).over("customer_id"),
)
```

### B. High-Speed Conditional Aggregations
Aggregate multiple filtered conditions in one pass:

```python
summary = df.group_by("department").agg(
    total_sales=pl.col("amount").sum(),
    high_value_orders=pl.col("amount").filter(pl.col("amount") > 1000).count(),
    avg_active_score=pl.col("score").filter(pl.col("is_active")).mean(),
)
```

### C. Date & Timestamp Manipulations
```python
df = df.with_columns(
    order_date=pl.col("created_at").dt.date(),
    order_hour=pl.col("created_at").dt.hour(),
    epoch_ms=pl.col("created_at").dt.epoch("ms"),
)
```

---

## 🔍 4. Auditing and Debugging the Query Plan

Always inspect how Polars optimizes your pipeline:

```python
query = (
    pl.scan_parquet("data/silver/*.parquet")
    .filter(pl.col("status") == "COMPLETED")
    .group_by("category")
    .agg(pl.col("revenue").sum())
)

# Print the optimized execution tree
print(query.explain())
```
