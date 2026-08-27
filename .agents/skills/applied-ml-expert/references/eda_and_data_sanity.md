# Pre-Modeling EDA & Data Sanity Gates (`eda_and_data_sanity.md`)

> **Golden Rule**: Never feed raw data into an ML estimator without running a 5-minute pre-flight sanity check. A silent bug in your input data will not crash your code—it will produce a deceptively high validation score that collapses in production.

---

## ⚡ The 5-Minute Pre-Flight Sanity Checklist

Before writing any `model.fit()`, execute these 5 checks:

```
┌─────────────────────────────────────────────────────────────┐
│                 5-MINUTE DATA SANITY GATES                  │
├──────────────────────────────┬──────────────────────────────┤
│ 1. TARGET DISTRIBUTION       │ 4. HIGH-CARDINALITY / IDS    │
│    Balance, skewness, zeros  │    Drop UUIDs, auto-inc IDs  │
├──────────────────────────────┼──────────────────────────────┤
│ 2. MISSINGNESS AUDIT         │ 5. CORRELATION & LEAKAGE     │
│    NaN %, missing mechanisms │    Check target correlations │
├──────────────────────────────┼──────────────────────────────┤
│ 3. DUPLICATES & OVERLAP      │                              │
│    Exact row duplicates      │                              │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🐍 1. Fast Python Sanity Snippet (Pandas & Polars)

### Pandas Version (Copy-pasteable in any Notebook)
```python
import pandas as pd
import numpy as np

def run_ml_sanity_check(df: pd.DataFrame, target_col: str) -> None:
    print(f"📊 Dataset Shape: {df.shape[0]:,} rows, {df.shape[1]} columns")
    
    # 1. Target check
    target = df[target_col]
    if target.dtype == "object" or target.nunique() <= 10:
        dist = target.value_counts(normalize=True)
        print(f"\n🎯 Target (Classification) Distribution:\n{dist.to_string()}")
        min_class_pct = dist.min()
        if min_class_pct < 0.05:
            print(f"⚠️  Severe class imbalance detected: minority class = {min_class_pct:.1%}. Use PR-AUC, not Accuracy!")
    else:
        print(f"\n🎯 Target (Regression) Stats:\nMean: {target.mean():.3f} | Median: {target.median():.3f} | Std: {target.std():.3f} | Min: {target.min():.3f} | Max: {target.max():.3f}")
        skew = target.skew()
        if abs(skew) > 1.5:
            print(f"⚠️  High target skewness ({skew:.2f}). Consider log1p transform or MAE loss.")

    # 2. Missing values
    null_pct = (df.isna().sum() / len(df)).sort_values(ascending=False)
    high_nulls = null_pct[null_pct > 0]
    if not high_nulls.empty:
        print(f"\n⚠️  Columns with Missing Values:\n{high_nulls.head(10).to_string()}")

    # 3. High cardinality ID candidates
    id_candidates = [col for col in df.columns if col != target_col and df[col].nunique() == len(df)]
    if id_candidates:
        print(f"\n🚫  Dropped High-Cardinality ID Candidates (Potential Leakage/Noise): {id_candidates}")

    # 4. Perfect target correlations (Potential direct target leakage)
    numeric_df = df.select_dtypes(include=[np.number])
    if target_col in numeric_df.columns:
        corrs = numeric_df.corr()[target_col].drop(target_col).abs().sort_values(ascending=False)
        suspicious_leaks = corrs[corrs > 0.95]
        if not suspicious_leaks.empty:
            print(f"\n🚨  SUSPICIOUS TARGET LEAKAGE (Correlation > 0.95):\n{suspicious_leaks.to_string()}")

# Example usage:
# run_ml_sanity_check(df, target_col="churn")
```

---

## 🔍 2. Identifying the 3 Major Leakage Traps

### Trap 1: The "Post-Event Feature" Leakage
* **Problem**: Including features that are only generated *after* the target event has occurred.
* **Example**: Predicting customer churn using a feature called `cancellation_reason_code` or `ticket_closed_date`.
* **Fix**: Ensure temporal integrity: every feature must be known strictly at $t_{\text{prediction}}$.

### Trap 2: The "ID Feature" Memorization
* **Problem**: Passing `customer_id`, `transaction_uuid`, or auto-increment primary keys into a Decision Tree or GBDT. The model memorizes exact leaf nodes for specific training IDs.
* **Fix**: Drop all high-cardinality identifier columns before feature engineering.

### Trap 3: The "Whole-Dataset Imputation" Leakage
* **Problem**: Computing `df['age'].fillna(df['age'].mean())` across the entire dataframe *before* splitting train/val.
* **Fix**: Split first, compute mean on `train` only, then transform `val` (or use `sklearn.pipeline.Pipeline` with `SimpleImputer`).
