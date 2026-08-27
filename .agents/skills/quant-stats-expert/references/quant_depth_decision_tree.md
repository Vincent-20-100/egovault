# Quantitative Depth Decision Tree (`quant_depth_decision_tree.md`)

> **Guiding Principle**: Match quantitative complexity to problem horizon, capital at risk, and execution latency. Never build an asynchronous multi-broker C++ event-loop for an afternoon signal exploration, and never run real capital on an un-purged vectorized backtest that ignores market impact.

---

## 🧭 The 4-Tier Quantitative Matrix

```
                    ┌──────────────────────────────────────────────┐
                    │ What is the operational lifecycle, capital,  │
                    │      and execution frequency of this task?   │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌───────────────────┬─────────────┴───────┬───────────────────┐
         ▼                   ▼                     ▼                   ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│ TIER 0 (NOTEBOOK)││ TIER 1 (SIGNAL)  ││ TIER 2 (RISK/PORT)││ TIER 3 (PLATFORM)│
│ Solo / Exploratory││ Research Script  ││ Risk Engine / Sim││ Institutional /  │
│ (1 cell / script)││ (100–500 lines)  ││ (500–2000 lines) ││ Live Replay (SLA)│
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
• Single `.ipynb` / `.py`• Clean typed functions• Ledoit-Wolf Shrinkage• Replay & Live Equiv.
• Log-returns stats • Vectorized backtest• Cornish-Fisher VaR• Partitioned Parquet
• ADF Stationarity  • Walk-Forward (WFA) • Purged K-Fold (CPCV)• Event-driven loop
• Sharpe + Moments  • Slippage & Spread  • Deflated Sharpe DSR• IBKR/Broker adapter
• Max Drawdown      • Monte Carlo bounds • Hierarchical Risk • Daily QC manifests
```

---

## 📊 Detailed Comparison by Dimension

| Dimension | Tier 0: Solo / Notebook | Tier 1: Research Script | Tier 2: Risk & Portfolio Engine | Tier 3: Institutional Platform |
| :--- | :--- | :--- | :--- | :--- |
| **Typical Target** | Fast alpha hypothesis test, factor correlation scan | Backtest validation of 1-3 signals, Walk-Forward parameter stability | Multi-asset portfolio allocation, VaR limits, factor risk models | Live automated execution, volatility surface engine, HFT/Mid-frequency |
| **Execution Paradigm**| Vectorized NumPy / Pandas | Vectorized Polars with execution lag (`shift(1)`) | Matrix quadratic programming (`cvxpy`) + Purged CV | Event-driven state machine (OrderBook $\to$ Signal $\to$ Order $\to$ Fill) |
| **Temporal Integrity**| Simple visual lag verification | Strict Point-in-Time timestamp alignment | Purged & Embargoed splits + Overlapping return purge | Immutable event partitions with nanosecond timestamps |
| **Transaction Costs** | Ignored or flat 0.05% assumption | Bid-Ask spread + static slippage + borrow rate | Square-root market impact model ($\sigma \sqrt{V/ADV}$) | LOB (Limit Order Book) queue simulation + broker fee schedule |
| **Risk Metrics** | Raw Sharpe, Max Drawdown | Sortino, Calmar, Rolling Volatility | Cornish-Fisher VaR (99%), Expected Shortfall (CVaR), DSR | Real-time factor exposures, Greeks ($\Delta, \Gamma, \mathcal{V}$), Stress Scenarios |
| **Covariance Modeling**| Sample covariance matrix | Exponentially Weighted (EWMA) Covariance | Ledoit-Wolf Shrinkage ($\kappa(A) < 100$) or HRP | Multi-factor risk model (Barra style) + Eigenvalue clipping |

---

## 🚫 The Anti-Pattern Traps

### Trap A: The "Free Money Backtest" (Under-engineering)
* **Symptoms**:
  - Sharpe Ratio of 3.8 on daily equity returns because signal uses `df['close']` to trade at `df['open']` of the exact same day.
  - Zero transaction costs modeled on a high-turnover strategy that trades 50 times per day.
  - Claiming 95% win-rate on non-stationary price cointegration without running ADF/Johansen tests.
* **Remedy**: Upgrade to **Tier 1**. Apply explicit 1-bar execution delay, deduct bid-ask spreads, and calculate Deflated Sharpe Ratio.

### Trap B: The "Hedge Fund in a Box" (Premature Overengineering)
* **Symptoms**:
  - Writing 3,000 lines of custom C++ multi-threaded order book simulation before verifying if the statistical correlation exists in a 10-line Python script.
  - Building distributed Kafka pipelines for an intraday signal tested on only 3 months of data.
* **Remedy**: Downgrade to **Tier 0** or **Tier 1**. Prove statistical validity and economic edge first in Python before engineering low-latency infrastructure.
