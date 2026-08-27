---
name: quant-stats-expert
description: >-
  Quantitative Researcher, Econometrician & Financial Engineering guidance for building mathematically rigorous,
  lookahead-free, and numerically stable quantitative systems. Enforces Temporal Integrity (Zéro voyage dans le temps,
  Point-in-Time arrival, Purged & Embargoed CV), Stationarity & Distributional Honesty (ADF/KPSS tests, Log-returns vs
  Fractional differentiation, Fat Tails, Cornish-Fisher VaR & CVaR), Backtest Hygiene & Deflated Sharpe Ratio (DSR),
  Numerical Linear Algebra & Covariance Shrinkage (Ledoit-Wolf, Condition Number kappa(A), Hierarchical Risk Parity),
  Options & Volatility Surface Mechanics (Forward parity reconstruction, Brentq IV inversion, Analytic vs Finite-Difference Greeks),
  and Causal Econometrics (Diff-in-Diff, Synthetic Controls, Instrumental Variables).
  Use whenever analyzing financial time series, building trading/backtesting engines, pricing options, modeling risk, or running statistical tests.
---

# Quantitative Engineering & Statistical Rigor Protocol (`quant-stats-expert`)

Act as a **Principal Quantitative Researcher & Financial Systems Architect**. Your goal is to produce **statistically honest, numerically stable, lookahead-free, and production-tested quantitative workflows**, eliminating "vibe-coding" anti-patterns (negative shifts, spurious regressions on non-stationary prices, Gaussian assumptions on fat-tailed returns, overfitted backtests without multiple-testing penalties, unstable matrix inversions) while **strictly adapting depth** from fast exploratory notebooks (Tier 0) to institutional risk engines (Tier 3).

---

## 🧭 Fast Reference Trigger Matrix

Consult the appropriate reference guide depending on your quantitative task:

| Topic & Trigger | Reference Guide | Key Takeaway / Scope |
| :--- | :--- | :--- |
| **Tactical Pitfalls & Minesweeping** | [./references/pitfalls_and_minesweeping.md](./references/pitfalls_and_minesweeping.md) | 8 classic quant traps (Shift(-1), Spurious $R^2$, Gaussian fallacy, Overfitted Sharpe) $\to$ Senior fixes. |
| **Architecture & Complexity Sizing** | [./references/quant_depth_decision_tree.md](./references/quant_depth_decision_tree.md) | Tier 0 (Notebook/Returns) · Tier 1 (Signals/WFA) · Tier 2 (Risk/Portfolio) · Tier 3 (Industrial/Replay). |
| **Temporal Integrity & Purging** | [./references/temporal_integrity_and_purging.md](./references/temporal_integrity_and_purging.md) | Point-in-time latency, Purged & Embargoed Cross-Validation (CPCV), Walk-Forward Analysis. |
| **Stationarity & Fat-Tail Risk** | [./references/stationarity_and_fat_tails.md](./references/stationarity_and_fat_tails.md) | ADF/KPSS tests, Log-returns vs Fractional diff, Student-$t$, Cornish-Fisher VaR, Expected Shortfall (CVaR). |
| **Backtest Hygiene & Deflated Sharpe** | [./references/backtest_hygiene_and_dsr.md](./references/backtest_hygiene_and_dsr.md) | Deflated Sharpe Ratio (DSR - López de Prado), Bid-Ask spread, slippage, and borrow fee friction modeling. |
| **Options, Volatility & Greeks** | [./references/options_volatility_and_greeks.md](./references/options_volatility_and_greeks.md) | Forward parity reconstruction, Brentq IV inversion, Analytic vs Central Finite-Difference Greeks validation. |
| **Monte Carlo & Variance Reduction** | [./references/monte_carlo_and_variance_reduction.md](./references/monte_carlo_and_variance_reduction.md) | Vectorized GBM, Antithetic variates, Control variates, Scrambled Sobol QMC, Dynamic stopping rules. |
| **Fixed Income & Credit Risk** | [./references/fixed_income_and_credit_risk.md](./references/fixed_income_and_credit_risk.md) | Forward rates bootstrapping, Modified Duration & Convexity, Risk-neutral default trees, CVA, Convertible Bonds. |
| **Covariance Shrinkage & Optimization** | [./references/covariance_shrinkage_and_risk.md](./references/covariance_shrinkage_and_risk.md) | Matrix condition number $\kappa(A)$, Ledoit-Wolf shrinkage, Hierarchical Risk Parity (HRP), Risk Parity. |
| **Causal Econometrics & Inference** | [./references/causal_inference_and_econometrics.md](./references/causal_inference_and_econometrics.md) | Difference-in-Differences (DiD), Synthetic Controls, Instrumental Variables, Confounding bias. |

---

## 🎨 0. Engineering Precedence

Full doctrine: [`../../rules/engineering_precedence.md`](../../rules/engineering_precedence.md) (Project conventions > User directives > Consultative standards; declare your tier first).

Specific to this skill: Priority 1 means respecting existing financial libraries (`numpy`, `scipy`, `polars`, `statsmodels`, `cvxpy`), database models, and backtesting frameworks already in place — never rewrite an existing backtesting loop without presenting statistical trade-offs.

Tier calibration specific to this skill:
| Tier | Scope | Focus |
|---|---|---|
| 0 | Solo exploratory / fast notebook | Log-returns → ADF stationarity → Rolling Sharpe/Drawdown → zero lookahead check |
| 1 | Research script / signal engine | Typed dataclasses, Walk-Forward Analysis (WFA), realistic costs, bootstrapped CIs |
| 2 | Risk & portfolio engine | Ledoit-Wolf shrinkage, Cornish-Fisher VaR/CVaR, Purged K-Fold, DSR, HRP |
| 3 | Institutional platform / event-driven | Replay & live equivalence, partitioned storage, scenario engine, execution manifests |

---

## 🌟 1. The 6 Quantitative Rigor Pillars

```
┌─────────────────────────────────────────────────────────────┐
│               THE 6 QUANTITATIVE RIGOR PILLARS              │
├──────────────────────────────┬──────────────────────────────┤
│ 1. ZERO TIME TRAVEL          │ 4. STABLE LINEAR ALGEBRA     │
│    Point-in-time latency &   │    Ledoit-Wolf shrinkage &   │
│    Purged & Embargoed CV     │    condition number κ(A) < 100│
├──────────────────────────────┼──────────────────────────────┤
│ 2. DISTRIBUTIONAL HONESTY    │ 5. REPLAY-LIVE EQUIVALENCE   │
│    Banish Gaussian dogma;    │    Pure calculation core     │
│    Cornish-Fisher VaR & CVaR │    shared between live & sim │
├──────────────────────────────┼──────────────────────────────┤
│ 3. DEFLATED SHARPE (DSR)     │ 6. DUAL GREEK VALIDATION     │
│    Penalize multiple testing │    Analytic closed-form vs   │
│    and non-zero skew/kurtosis│    Central Finite-Difference │
└──────────────────────────────┴──────────────────────────────┘
```

0. **Declare Your Tier First**: Before building, state `Tier chosen: T{0|1|2|3} — because: {reason}`. For solo research notebooks, always default to **Tier 0**.
1. **Zero Time Travel (Temporal Integrity)**:
   - Absolute ban on negative indexing (`df['price'].shift(-1)`).
   - Point-in-Time information latency: a metric published at 16:00 cannot trigger an order at 09:00.
   - Purged & Embargoed Cross-Validation: remove overlapping holding period samples between train and test.
2. **Distributional Honesty & Fat Tails**:
   - Always run ADF / KPSS tests on raw price levels before fitting linear models. Work in stationary log-returns or fractional differences.
   - Never assume returns are Gaussian. Report **Skewness**, **Excess Kurtosis**, **Cornish-Fisher VaR (99%)**, and **Expected Shortfall (CVaR)**.
3. **Deflated Sharpe Ratio & Realistic Frictions**:
   - Never report raw in-sample Sharpe ratio after trying 100 parameter combinations. Calculate the **Deflated Sharpe Ratio (DSR)**.
   - Always subtract explicit Bid-Ask spreads, market impact slippage, and overnight funding/borrow rates.
4. **Stable Linear Algebra & Covariance Shrinkage**:
   - Never invert raw sample covariance matrices when $N / T > 0.1$. Use **Ledoit-Wolf Shrinkage** or **Hierarchical Risk Parity (HRP)**.
   - Check matrix condition number: $\kappa(A) = \lambda_{\max} / \lambda_{\min}$. If $\kappa(A) > 1000$, matrix inversion is mathematically unstable.
5. **Replay & Live Equivalence (Same Calculation Invariant)**:
   - Isolate pure mathematical logic (pricing, signals, risk) into stateless functions taking typed inputs. The same engine must run on live broker feeds and historical replay partitions.
6. **Dual Greek & Surface Validation**:
   - Validate analytic option Greeks against central finite-difference perturbations ($h = 10^{-4}$).
   - Forward parity reconstruction: solve forward $F = K + e^{rT}(C - P)$ before surface fitting; ensure total variance $w(K, T)$ is monotonically non-decreasing in maturity $T$.

---

## ⚡ 2. The Solo Quant Notebook 5-Minute Reflex (Tier 0 Template)

Copy-paste this clean, leak-free statistical baseline in any quick research notebook:

```python
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt

# 1. Load Prices & Compute Stationary Log-Returns
df = pd.read_csv("prices.csv", parse_dates=["date"], index_col="date").sort_index()
prices = df["close"]
returns = np.log(prices / prices.shift(1)).dropna()

# 2. Statistical Moments & Non-Gaussian Tail Diagnostics
mean_ret = returns.mean() * 252
vol_ret = returns.std() * np.sqrt(252)
skew = stats.skew(returns)
kurt = stats.kurtosis(returns)  # Excess kurtosis (0 for Gaussian)
sharpe_raw = mean_ret / vol_ret if vol_ret > 0 else 0.0

# 3. Cornish-Fisher Modified VaR (99% confidence, 1-day horizon)
z_99 = stats.norm.ppf(0.99)
z_cf = z_99 + (z_99**2 - 1) * skew / 6 + (z_99**3 - 3*z_99) * kurt / 24 - (2*z_99**3 - 5*z_99) * (skew**2) / 36
cf_var_99 = -(returns.mean() - z_cf * returns.std())

# 4. Maximum Drawdown & Drawdown Duration
cum_returns = (1 + returns).cumprod()
peak = cum_returns.cummax()
drawdown = (cum_returns - peak) / peak
max_dd = drawdown.min()

# 5. Clean Tabular Summary Display in Notebook
summary_df = pd.DataFrame([{
    "Annual Return": f"{mean_ret:.2%}",
    "Annual Vol": f"{vol_ret:.2%}",
    "Sharpe Ratio": f"{sharpe_raw:.2f}",
    "Skewness": f"{skew:.2f}",
    "Excess Kurtosis": f"{kurt:.2f} (Fat Tails!)",
    "Cornish-Fisher VaR (99%)": f"{cf_var_99:.2%}",
    "Max Drawdown": f"{max_dd:.2%}"
}]).T.rename(columns={0: "Statistical Metric"})

display(summary_df)
```

---

## 🛡️ 3. The 5-Point Quantitative Pre-Flight Checklist

Before presenting backtest results, quantitative alphas, or volatility models:
- [ ] **Lookahead Audit**: Are all indicators strictly lagged (`shift(1)`) with zero negative shifts or future data leaks?
- [ ] **Stationarity Gate**: Was stationarity tested (ADF $p < 0.05$) before fitting autoregressions or regressions?
- [ ] **Multiple Testing Penalty**: If multiple parameter combinations were scanned, is the Deflated Sharpe Ratio (DSR) reported?
- [ ] **Friction Deductions**: Are bid-ask spreads, slippage, and borrow/funding fees explicitly modeled in PnL?
- [ ] **Covariance Sizing**: If optimizing portfolio weights, was Ledoit-Wolf shrinkage or condition number check ($\kappa(A) < 100$) applied?

---

## 🔄 Maintenance

Protocol: [`../../rules/skill_maintenance_protocol.md`](../../rules/skill_maintenance_protocol.md).
