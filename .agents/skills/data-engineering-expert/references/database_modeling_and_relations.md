# Database Modeling, Table Relationships & Schema Management

> **Core Philosophy**: Good data architecture starts with clean relational modeling. Choose the right modeling paradigm for the job: **Normalized 3NF for Transactional (OLTP) integrity** and **Dimensional Star Schema / OBT for Analytical (OLAP) speed**. Always prioritize clarity, explicit relationships, and predictable data integrity.

---

## 🔑 0. Normalization & Key Typology (Foundations)

> Methodology reference: *Database Design for Mere Mortals* (Hernandez) — the standard step-by-step approach to sound relational design.

**Normal Forms (apply in order — each fixes one specific anomaly class):**
- **1NF**: Every column holds a single atomic value, no repeating groups (no `phone1, phone2, phone3` columns — that's a 1:N relationship hiding in disguise, extract a child table).
- **2NF**: (Only relevant with composite keys) Every non-key column depends on the **whole** key, not just part of it. Violation symptom: a column that's actually a fact about only one part of a composite PK.
- **3NF**: No non-key column depends on another non-key column (no transitive dependency). Violation symptom: storing `city` and `zip_code` on an `orders` table when `city` is really a fact about `zip_code`, not about the order.
- **BCNF**: A stricter 3NF for the rare case of multiple overlapping candidate keys — rarely needed to name explicitly, but the underlying rule ("every determinant must be a candidate key") is what stops subtle update anomalies 3NF alone misses.
- **Deliberate denormalization** (OLAP star schema, wide marts) is a conscious *later* trade-off for read speed — never a substitute for not having modeled 3NF correctly first. See §3 below.

**Key Typology:**
- **Candidate Key**: any column (or minimal column set) that could uniquely identify a row. A table can have several.
- **Primary Key**: the candidate key chosen to be *the* identifier. Must be stable (never changes) and minimal.
- **Natural Key**: a real-world attribute used as key (e.g. `email`, `national_id`). Risk: real-world values change or turn out non-unique (people share emails, SSNs get corrected) — a natural key you thought was stable can force a painful migration later.
- **Surrogate Key**: a system-generated identifier (`UUID`, auto-increment `BIGSERIAL`) with no business meaning. Default recommendation for PKs — immune to real-world data drift. Still enforce a `UNIQUE` constraint on the natural key(s) so integrity isn't lost.
- **Composite Key**: a PK made of 2+ columns, typical for junction/associative tables (`PRIMARY KEY (order_id, product_id)`).
- **Foreign Key**: a column referencing another table's PK — the mechanism that makes a relationship enforceable by the database itself, not just by application code.

---

## 🏛️ 1. OLTP (Transactional) vs OLAP (Analytical) Paradigms

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   WHICH MODELING PARADIGM TO CHOOSE?                     │
├─────────────────────────────────────┬────────────────────────────────────┤
│ OLTP (Transactional - PostgreSQL,   │ OLAP (Analytical - DuckDB,         │
│ SQLite, MySQL)                      │ Snowflake, BigQuery, ClickHouse)   │
├─────────────────────────────────────┼────────────────────────────────────┤
│ • Goal: Fast writes, ACID, zero     │ • Goal: Fast aggregation over      │
│   redundancy, immediate consistency │   millions of rows, read-heavy     │
│ • Paradigm: 3rd Normal Form (3NF)   │ • Paradigm: Dimensional Modeling   │
│ • Foreign Keys & strict constraints │   (Star Schema) or One Big Table   │
│ • Row-oriented storage              │ • Columnar storage (Parquet/Arrow) │
└─────────────────────────────────────┴────────────────────────────────────┘
```

---

## 🔗 2. Relational Table Relationships & Constraints (OLTP Standard)

### A. The 3 Fundamental Relationship Types

```sql
-- 1. ONE-TO-ONE (1:1): Split sensitive or optional profile data
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url TEXT
);

-- 2. ONE-TO-MANY (1:N): Standard parent-child hierarchy
CREATE TABLE orders (
    order_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. MANY-TO-MANY (N:M): Junction / Associative table
CREATE TABLE products (
    product_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0)
);

CREATE TABLE order_items (
    order_id UUID NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

### B. Foreign Key Cascading Strategies
* `ON DELETE RESTRICT` (Recommended default for vital parents): Prevents deletion of a parent record (e.g. `users`) if child records (e.g. `orders`) exist.
* `ON DELETE CASCADE`: Automatically cleans up child records when parent is deleted (e.g. deleting an `order` deletes its `order_items`).
* `ON DELETE SET NULL`: Preserves children while detaching from parent (e.g. when an optional `category` is deleted).

### C. Smart Indexing Strategy (OLTP)
* **Foreign Keys**: Always index foreign key columns (`CREATE INDEX idx_orders_user_id ON orders(user_id);`) to avoid full table scans on joins.
* **Partial Indexes**: Index only active rows for efficiency (`CREATE INDEX idx_active_orders ON orders(status) WHERE status = 'PENDING';`).
* **Composite Indexes**: Align column order with query filters (`CREATE INDEX idx_orders_user_date ON orders(user_id, created_at DESC);`).

---

## 🌟 3. Dimensional Modeling for Analytics (OLAP / Star Schema)

In analytical warehouses and data marts, normalize less and structure around **Business Events (Facts)** and **Contextual Entities (Dimensions)**:

```
                      ┌────────────────────────┐
                      │     dim_customers      │
                      ├────────────────────────┤
                      │ customer_key (PK)      │
                      │ customer_id (NK)       │
                      │ country, segment       │
                      └───────────┬────────────┘
                                  │ 1
                                  │
                                  │ *
┌────────────────────────┐   ┌────┴───────────────────┐   ┌────────────────────────┐
│      dim_products      │   │       fct_orders       │   │       dim_dates        │
├────────────────────────┤   ├────────────────────────┤   ├────────────────────────┤
│ product_key (PK)       ├───┤ order_key (PK)         ├───┤ date_key (PK - YYYYMMDD│
│ product_id (NK)        │ * │ customer_key (FK)      │ * │ full_date              │
│ category, brand        │   │ product_key (FK)       │   │ day_name, month_name   │
└────────────────────────┘   │ date_key (FK)          │   │ is_weekend, quarter    │
                             │ quantity, gross_amount │   └────────────────────────┘
                             └────────────────────────┘
```

### Slowly Changing Dimensions (SCD):
* **SCD Type 1 (Overwrite)**: Simple updates without tracking history. Used for correcting typos (e.g. updating an email address).
* **SCD Type 2 (Historical Tracking)**: Preserves history by adding new rows with validity intervals (`valid_from`, `valid_to`, `is_current = true`). Essential for accurate financial reporting over time.

---

## 🔄 4. Bridging Relational DBs with the Medallion Architecture

```
  ┌───────────────────────┐
  │  Source OLTP Database │ (PostgreSQL, SQLite, MySQL)
  └───────────┬───────────┘
              │ (Change Data Capture / CDC or Daily Batch Extraction)
              ▼
  ┌───────────────────────┐
  │     BRONZE LAYER      │ Verbatim raw table snapshots / CDC JSON logs
  │     (Raw Ingestion)   │ with metadata (_receipt_ts, _source_table)
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │     SILVER LAYER      │ Normalized, cleaned entity tables (orders, users).
  │    (Conformed Core)   │ Types cast, duplicates removed, foreign keys validated.
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │      GOLD LAYER       │ Dimensional Star Schemas (fct_orders + dim_users)
  │    (Business Marts)   │ or Wide OBT tables optimized for DuckDB/BI queries.
  └───────────────────────┘
```

---

## 🛡️ 5. Schema Evolution & Database Migrations (Zero-Downtime)

When evolving database schemas over time, follow the **Expand-Contract Pattern**:

1. **Phase 1 (Expand)**: Add the new column/table without modifying existing code (`ALTER TABLE users ADD COLUMN full_name TEXT;`).
2. **Phase 2 (Dual-Write / Backfill)**: Update application to write to both old and new columns, and backfill historical data.
3. **Phase 3 (Contract)**: Update application to read exclusively from the new column.
4. **Phase 4 (Cleanup)**: Safely drop the deprecated column in a separate, later deployment.
