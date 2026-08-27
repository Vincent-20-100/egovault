# dbt & SQL Data Modeling Standards (The 3-Tier Layering Standard)

> **Core Philosophy**: Treat SQL like modular, compiled software. Eliminate 500-line monolithic query scripts. Decompose transformations into a strict 3-tier DAG: **Staging $\to$ Intermediate $\to$ Marts**, linked with immutable dependency graphs.

---

## 🏛️ 1. The 3-Tier dbt Directory Layout

```text
models/
├── staging/               # Layer 1: Source conformance & typing (1:1 with raw tables)
│   ├── stripe/
│   │   ├── src_stripe.yaml
│   │   ├── stg_stripe__charges.sql
│   │   └── stg_stripe__customers.sql
│   └── shopify/
│       ├── src_shopify.yaml
│       └── stg_shopify__orders.sql
│
├── intermediate/          # Layer 2: Business logic, complex joins, entity resolution
│   ├── finance/
│   │   ├── int_orders_joined_to_payments.sql
│   │   └── int_customer_lifetime_value_calculated.sql
│   └── operations/
│
└── marts/                 # Layer 3: Final analytical tables (Dimensional or OBT)
    ├── core/
    │   ├── dim_customers.sql
    │   └── fct_orders.sql
    └── finance/
        └── fct_monthly_mrr.sql
```

---

## 📋 2. Layer Definitions & Contracts

### A. Staging Layer (`stg_<source>__<entity>.sql`)
* **Role**: The atomic cleaning layer. Exactly 1 staging model per source table.
* **Rules**:
  - ✅ Rename columns to consistent project conventions (`id` $\to$ `order_id`).
  - ✅ Cast strings to dates/booleans/numbers (`created_at::timestamp`).
  - ✅ Basic sanitization (e.g. `trim(lower(email))`).
  - ❌ **STRICTLY FORBIDDEN**: No `JOIN`, no `GROUP BY`, no multi-table business logic.
* **Materialization**: `view`.

```sql
-- models/staging/stripe/stg_stripe__charges.sql
WITH source AS (
    SELECT * FROM {{ source('stripe', 'charges') }}
),

renamed AS (
    SELECT
        id AS charge_id,
        customer AS customer_id,
        amount / 100.0 AS amount_usd,
        status AS payment_status,
        created::timestamp AS created_at,
        currency
    FROM source
)

SELECT * FROM renamed
```

---

### B. Intermediate Layer (`int_<entity>_<verb>.sql`)
* **Role**: The business logic workshop. Bridges atomic staging atoms to final marts.
* **Rules**:
  - ✅ Perform multi-source joins (e.g. Stripe charges + Shopify orders).
  - ✅ Apply business window functions (`ROW_NUMBER() OVER (...)`).
  - ✅ Pre-compute complex metrics.
* **Materialization**: `view` or `ephemeral`.

---

### C. Marts Layer (`fct_<entity>.sql` & `dim_<entity>.sql`)
* **Role**: The consumption surface for BI dashboards, ML pipelines, and LLMs.
* **Dimensional Modeling**:
  - **Dimension Tables (`dim_`)**: Who, what, where entities (slowly changing attributes). Example: `dim_customers`, `dim_products`.
  - **Fact Tables (`fct_`)**: Discrete events, measurements, financial transactions. Example: `fct_orders`, `fct_pageviews`.
* **Materialization**: `table` or `incremental`.

---

## 📜 3. Clean CTE Structure Standard

Every SQL model must follow the **3-Part CTE Pattern** (Import $\to$ Transform $\to$ Final):

```sql
-- 1. IMPORT CTEs (Reference upstream models cleanly at the top)
WITH orders AS (
    SELECT * FROM {{ ref('stg_shopify__orders') }}
),

payments AS (
    SELECT * FROM {{ ref('stg_stripe__charges') }}
),

-- 2. LOGICAL / TRANSFORMATION CTEs (Single responsibility steps)
successful_payments AS (
    SELECT
        order_id,
        SUM(amount_usd) AS total_paid_usd
    FROM payments
    WHERE payment_status = 'paid'
    GROUP BY order_id
),

joined_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.order_status,
        COALESCE(p.total_paid_usd, 0.0) AS total_paid_usd
    FROM orders o
    LEFT JOIN successful_payments p ON o.order_id = p.order_id
)

-- 3. FINAL SELECT (Simple select * from the last CTE)
SELECT * FROM joined_orders
```

---

## ⚡ 4. Incremental Strategies (Idempotent Warehousing)

For high-volume datasets, avoid full table recomputation on every run:

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        on_schema_change='sync_all_columns'
    )
}}

SELECT *
FROM {{ ref('stg_orders') }}
{% if is_incremental() %}
    WHERE updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```
