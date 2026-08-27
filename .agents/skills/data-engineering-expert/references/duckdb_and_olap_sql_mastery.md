# DuckDB & OLAP SQL Mastery (In-Process Analytical Engine)

> **Core Philosophy**: DuckDB is the SQLite of analytics. It runs in-process, executes vectorized SQL at C++ speed, queries Parquet files directly on disk, and seamlessly interchanges memory with Polars and Apache Arrow via zero-copy buffers.

---

## 🦆 1. Why DuckDB is the Modern Standard for Analytical Pipelines

* **No server daemon**: Embedded C++ binary, starts in <10ms.
* **Vectorized Columnar Execution**: SIMD-optimized column chunks (1024 values per vector).
* **Direct Parquet & Arrow Scan**: Query `.parquet` or Arrow tables without importing them into an internal database format first.
* **Out-of-Core Processing**: Gracefully spills large joins and aggregations to disk when RAM limit is reached.

---

## 💻 2. Direct Parquet Querying & Globbing

DuckDB can read hundreds of Parquet files in parallel using glob patterns and automatic predicate pushdown:

```python
import duckdb

# Connect to in-memory instance or persistent file
con = duckdb.connect()

# Query partitioned Parquet dataset directly with SQL
query = """
SELECT 
    country,
    date_trunc('month', order_date) AS order_month,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_basket
FROM read_parquet('data/silver/orders/dt=*/*.parquet')
WHERE status = 'DELIVERED'
GROUP BY country, order_month
HAVING total_revenue > 10000
ORDER BY order_month DESC, total_revenue DESC;
"""

# Fetch as Polars DataFrame (Zero-Copy via Arrow)
df_analytics = con.execute(query).pl()
```

### Schema Evolution (`union_by_name`):
When disparate Parquet files have evolved columns over time:
```sql
SELECT * FROM read_parquet('data/raw/*.parquet', union_by_name = true);
```

---

## ⚡ 3. Zero-Copy Interop: DuckDB $\longleftrightarrow$ Polars $\longleftrightarrow$ PyArrow

Never convert through CSV or Pandas intermediate buffers. Interchange Arrow memory directly in microseconds:

```python
import duckdb
import polars as pl

# 1. Start with Polars DataFrame
df_polars = pl.DataFrame({
    "user_id": [1, 2, 3, 4],
    "balance": [100.5, 250.0, 12.0, 950.25],
    "tier": ["SILVER", "GOLD", "BRONZE", "GOLD"],
})

# 2. Query Polars directly from DuckDB (registers automatically!)
con = duckdb.connect()
con.register("users_table", df_polars)

sql_result = con.execute("""
    SELECT tier, AVG(balance) as avg_bal, COUNT(*) as user_count
    FROM users_table
    GROUP BY tier
""").pl()  # Return directly to Polars!
```

---

## ⚙️ 4. Out-of-Core Memory Management & Production Configuration

For processing massive datasets larger than physical RAM:

```python
con = duckdb.connect("analytics_vault.duckdb")

# 1. Set explicit RAM memory limit
con.execute("SET memory_limit = '8GB';")

# 2. Designate high-speed NVMe storage for disk spilling
con.execute("SET temp_directory = './var/duckdb_temp';")

# 3. Limit threads to prevent thread thrashing (1-4 GB RAM per thread)
con.execute("SET threads = 4;")

# 4. Disable row insertion order preservation to reduce memory pressure
con.execute("SET preserve_insertion_order = false;")
```

---

## 📤 5. Exporting Optimized Parquet Files with DuckDB

Export aggregated Gold-tier datasets with fine-tuned ZSTD compression and partitioning:

```sql
COPY (
    SELECT * FROM clean_orders
) TO 'data/gold/daily_sales' (
    FORMAT PARQUET,
    CODEC 'ZSTD',
    COMPRESSION_LEVEL 3,
    ROW_GROUP_SIZE 100000,
    PARTITION_BY (order_year, order_month),
    OVERWRITE_OR_IGNORE true
);
```

---

## 🔍 6. Profiling with `EXPLAIN ANALYZE`

Identify bottlenecks, scan selectivity, and join types:

```python
explanation = con.execute("EXPLAIN ANALYZE " + query).fetchone()[1]
print(explanation)
```
