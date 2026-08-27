# Data Contracts & Schema Control (PyArrow & Pandera)

> **Golden Rule**: Never rely on implicit schema inference in production. Schema drift is the #1 cause of silent pipeline corruption. Enforce explicit, typed schemas at the intake valve.

---

## 📜 1. What is a Data Contract?

A **Data Contract** is a formal, machine-verifiable specification between data producers and data consumers:
* **Structural Types**: Exact column names, nullability, and binary storage types (e.g. `pa.int32()`, `pa.timestamp('us', tz='UTC')`).
* **Semantic Constraints**: Allowed enum sets, numeric ranges (`price >= 0.0`), format regex (`^[a-zA-Z0-9_-]+$`).
* **SLA & Freshness**: Maximum acceptable delay between event generation and arrival.

---

## 🏗️ 2. Explicit PyArrow Schemas as Binary Contracts

Define schemas in Python using `pyarrow.schema` to enforce type safety before data touches storage or memory:

```python
"""Domain PyArrow schema contract for Order entities."""

import pyarrow as pa

ORDER_SCHEMA = pa.schema([
    pa.field("order_id", pa.string(), nullable=False),
    pa.field("customer_id", pa.string(), nullable=False),
    pa.field("order_date", pa.date32(), nullable=False),
    pa.field("amount_cents", pa.int64(), nullable=False),
    pa.field("currency", pa.string(), nullable=False),
    pa.field("status", pa.string(), nullable=False),
    pa.field("is_refunded", pa.bool_(), nullable=False),
    pa.field("created_at", pa.timestamp("us", tz="UTC"), nullable=False),
])
```

### Applying Schema at Read & Write Time:
```python
import pyarrow.parquet as pq
import pyarrow as pa

# Writing Parquet with explicit schema contract
table = pa.Table.from_pydict(data_dict, schema=ORDER_SCHEMA)
pq.write_table(table, "data/silver/orders.parquet", compression="ZSTD", compression_level=3)
```

---

## 🛡️ 3. Semantic Validation with Pandera / Polars

Verify business invariants (null limits, value boundaries) before promoting data to Silver/Gold tiers:

```python
import pandera.polars as pa_pl
import polars as pl


class OrderDataContract(pa_pl.DataFrameModel):
    """Pandera schema model validating business invariants."""

    order_id: pl.String = pa_pl.Field(unique=True)
    amount_cents: pl.Int64 = pa_pl.Field(ge=0, le=10_000_000)
    currency: pl.String = pa_pl.Field(isin=["USD", "EUR", "GBP"])
    status: pl.String = pa_pl.Field(isin=["PENDING", "PAID", "CANCELLED", "REFUNDED"])
    is_refunded: pl.Boolean


def validate_orders(df: pl.DataFrame) -> pl.DataFrame:
    """Validate DataFrame against semantic contract."""
    try:
        return OrderDataContract.validate(df)
    except pa_pl.errors.SchemaError as err:
        logger.error("Data contract violation: {error}", error=str(err))
        raise
```

---

## 🔄 4. Handling Schema Drift & Evolution

```
┌─────────────────────────────────────────────────────────────┐
│                 SCHEMA DRIFT CLASSIFICATION                 │
├────────────────────────────────┬────────────────────────────┤
│ 1. BACKWARD COMPATIBLE         │ 2. BREAKING SCHEMA CHANGE  │
│ • Adding an optional column    │ • Removing a required col  │
│ • Widening type (Int32 ➔ Int64)│ • Renaming a column        │
│ ➔ Auto-evolve with schema union│ ➔ HALT pipeline or route   │
│                                │   to Quarantine / DLQ      │
└────────────────────────────────┴────────────────────────────┘
```

### Strategy: The Quarantine Valve (Non-Halting Pipeline)
When a batch contains unexpected schema violations:
1. Split batch into `valid_records` (100% compliant with contract) and `quarantine_records` (malformed).
2. Process `valid_records` downstream to prevent blocking critical production analytics.
3. Write `quarantine_records` to `data/quarantine/` and fire an alert.
