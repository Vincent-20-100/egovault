# Data Quality & Observability (Circuit Breakers & Invariants)

> **Core Philosophy**: Data Observability is not looking at dashboards after users complain. It is embedding **automated circuit breakers** inside the pipeline to halt or quarantine data the instant an invariant or statistical distribution boundary is violated.

---

## 🛡️ 1. The 5 Dimensions of Data Quality (DQ)

```
┌─────────────────────────────────────────────────────────────┐
│                 5 DATA QUALITY DIMENSIONS                   │
├──────────────────────────────┬──────────────────────────────┤
│ 1. COMPLETENESS              │ 4. TIMELINESS / FRESHNESS    │
│    Null rate < threshold %   │    Event lag < SLA minutes   │
├──────────────────────────────┼──────────────────────────────┤
│ 2. UNIQUENESS                │ 5. VOLUME & ANOMALY          │
│    Zero duplicate PKs        │    Row delta within +/- 20%  │
├──────────────────────────────┼──────────────────────────────┤
│ 3. VALIDITY / CONFORMANCE    │                              │
│    Range, Regex, Enums       │                              │
└──────────────────────────────┴──────────────────────────────┘
```

---

## ⚡ 2. Automated Circuit Breakers in Polars / Python

Implement a dedicated Quality Gatekeeper function that runs before data publication:

```python
"""Automated Data Quality circuit breaker using Polars."""

import polars as pl
from dataclasses import dataclass


@dataclass(frozen=True)
class QualityMetrics:
    total_rows: int
    null_customer_rate: float
    duplicate_order_count: int
    negative_amount_count: int


class DataQualityError(Exception):
    """Raised when a dataset fails automated quality circuit breakers."""


def evaluate_quality_gate(df: pl.DataFrame, max_allowed_null_rate: float = 0.01) -> QualityMetrics:
    """Compute quality metrics and trip circuit breaker on invariant violations."""
    total_rows = df.height
    if total_rows == 0:
        raise DataQualityError("CRITICAL: Ingested batch is completely empty (0 rows).")

    # Vectorized computation of quality metrics in a single pass
    stats = df.select(
        null_customers=pl.col("customer_id").is_null().sum(),
        duplicate_orders=pl.col("order_id").is_duplicated().sum(),
        negative_amounts=(pl.col("amount") < 0.0).sum(),
    ).to_dicts()[0]

    null_rate = stats["null_customers"] / total_rows

    metrics = QualityMetrics(
        total_rows=total_rows,
        null_customer_rate=null_rate,
        duplicate_order_count=stats["duplicate_orders"],
        negative_amount_count=stats["negative_amounts"],
    )

    # 1. Check Completeness Circuit Breaker
    if null_rate > max_allowed_null_rate:
        raise DataQualityError(
            f"Null customer_id rate {null_rate:.2%} exceeds threshold {max_allowed_null_rate:.2%}"
        )

    # 2. Check Uniqueness Circuit Breaker
    if metrics.duplicate_order_count > 0:
        raise DataQualityError(
            f"Found {metrics.duplicate_order_count} duplicate order_id records."
        )

    # 3. Check Validity Circuit Breaker
    if metrics.negative_amount_count > 0:
        raise DataQualityError(
            f"Found {metrics.negative_amount_count} records with negative monetary amounts."
        )

    return metrics
```

---

## 📈 3. Statistical Anomaly & Volume Drift Detection

Compare the current batch's volume and distributions against historical moving averages to detect upstream extraction failures:

```python
"""Volume anomaly detection comparing against historical baseline."""


def check_volume_anomaly(
    current_row_count: int,
    historical_avg_count: float,
    max_pct_deviation: float = 0.30,
) -> None:
    """Trip alert if batch row count drops or spikes unexpectedly."""
    if historical_avg_count <= 0:
        return

    pct_diff = abs(current_row_count - historical_avg_count) / historical_avg_count

    if pct_diff > max_pct_deviation:
        raise DataQualityError(
            f"Volume anomaly detected: Current batch has {current_row_count} rows, "
            f"deviating by {pct_diff:.1%} from historical average of {historical_avg_count:.0f} rows."
        )
```

---

## 📊 4. Data Quality Governance Matrix

| Check Type | Severity | Action on Failure | Alert Destination |
| :--- | :--- | :--- | :--- |
| **Duplicate Primary Key** | CRITICAL | Halt Pipeline (Abort Publish) | PagerDuty / Slack Engineering |
| **Volume Drop > 50%** | CRITICAL | Halt Pipeline | PagerDuty / On-Call |
| **Null Rate > 2%** | WARNING | Route bad rows to DLQ, publish valid | Slack Data Alerts |
| **New Unseen Category** | INFO | Accept and log schema evolution | Observability Dashboard |
