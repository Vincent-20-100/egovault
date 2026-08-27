# Temporal Integrity, Point-in-Time & Purged CV (`temporal_integrity_and_purging.md`)

> **First Law of Quantitative Backtesting**:
> *« A quantitative model must only observe information that was available and published strictly before the decision timestamp. »*

---

## 🧭 1. Point-in-Time Data Modeling & Information Arrival Latency

In real markets, information does not arrive instantaneously at bar close:

```
[Event Occurs: 16:00] ──▶ [Brokers Publish & Data Cleans: 16:15] ──▶ [Order Sent: Next Open 09:00]
```

### The 3 Rules of Point-in-Time Alignment:
1. **Earnings / Macro Releases**: A release announced on date $t$ after-market cannot be traded during session $t$. Trade timestamp must be $t+1$.
2. **Fundamental Revisions**: Financial statement metrics must use the *filing date* (10-K / 10-Q SEC timestamp), not the fiscal period end date.
3. **Execution Delay**: A signal calculated on daily close $P_t$ can only be executed at $P_{t+1}^{\text{open}}$ or with a documented execution slippage at $P_{t+1}^{\text{close}}$.

---

## 🛡️ 2. Purged & Embargoed Cross-Validation (López de Prado)

When labels are constructed over a multi-day holding period (e.g. 5-day forward return or triple-barrier labeling), standard K-Fold CV creates massive data leakage across adjacent folds.

```
┌──────────────────────────────┬───────────────────┬──────────────────────────────┐
│       TRAIN FOLD 1           │   VALIDATION FOLD │   TRAIN FOLD 2 (EMBARGOED)   │
│   (Purged at boundary)       │                   │                              │
└───────────────────────[PURGE]┴───────────────────┴[EMBARGO]─────────────────────┘
```

### The Purging & Embargoing Algorithm

```python
import pandas as pd
import numpy as np

class PurgedGroupTimeSeriesSplit:
    """Purged and Embargoed Cross-Validation splitter for overlapping time series."""
    def __init__(self, n_splits: int = 5, pct_embargo: float = 0.01):
        self.n_splits = n_splits
        self.pct_embargo = pct_embargo

    def split(self, events: pd.DataFrame):
        """Yields train and test indices with overlap purging and trailing embargo.
        
        events DataFrame must contain: ['t1'] (the label evaluation end-time for each sample).
        """
        indices = np.arange(len(events))
        test_chunks = np.array_split(indices, self.n_splits)
        
        for test_idx in test_chunks:
            test_start = events.index[test_idx[0]]
            test_end = events.index[test_idx[-1]]
            test_max_t1 = events.iloc[test_idx]['t1'].max()
            
            # 1. Purge training samples whose holding period overlaps with test start
            train_mask = (events['t1'] < test_start) | (events.index > test_max_t1)
            
            # 2. Apply Embargo after test set
            embargo_offset = int(len(events) * self.pct_embargo)
            embargo_end_idx = min(len(events) - 1, test_idx[-1] + embargo_offset)
            embargo_end_time = events.index[embargo_end_idx]
            
            train_mask = train_mask & ((events.index < test_start) | (events.index > embargo_end_time))
            
            train_indices = indices[train_mask]
            yield train_indices, test_idx
```

---

## 🔄 3. Walk-Forward Analysis (WFA) Protocol

For dynamic trading strategies, prefer Walk-Forward Analysis over static backtests:

```
Window 1: [--- Train: Year 1-3 ---][-- Test: Year 4 --]
Window 2:        [--- Train: Year 2-4 ---][-- Test: Year 5 --]
Window 3:               [--- Train: Year 3-5 ---][-- Test: Year 6 --]
```

* **Anchored / Expanding Window**: Train on all historical data up to year $k$, test on year $k+1$.
* **Rolling Window**: Train on fixed-length window (e.g. 3 years), test on the subsequent 1 year.
* **Out-of-Sample Splicing**: Concatenate all out-of-sample test periods to form the **Unbiased Walk-Forward Equity Curve**.
