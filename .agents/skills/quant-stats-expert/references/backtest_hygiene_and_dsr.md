# Backtest Hygiene, Deflated Sharpe (DSR) & Frictions (`backtest_hygiene_and_dsr.md`)

> **Quantitative Reality**:
> *« If you test 1,000 random parameter combinations on 5 years of historical data, by pure chance several will produce a Sharpe ratio > 2.0. The Deflated Sharpe Ratio measures whether your alpha is skill or multiple testing noise. »*

---

## 📉 1. The Deflated Sharpe Ratio (DSR Protocol)

The **Deflated Sharpe Ratio** (Bailey & López de Prado, 2014) adjusts the observed Sharpe ratio for:
1. Non-normality (skewness and kurtosis of returns).
2. Sample length $T$.
3. **Number of independent trials / backtest iterations ($N_{\text{trials}}$)**.
4. Variance of Sharpe ratios across all tested trials ($\sigma^2_{\text{trials}}$).

```python
import numpy as np
import scipy.stats as stats

def compute_deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    var_trials: float,
    sample_length_days: int,
    skew: float,
    kurt: float
) -> float:
    """Compute the Deflated Sharpe Ratio (DSR) probability.
    
    Returns:
        p-value (CDF probability). A value >= 0.95 indicates the Sharpe ratio
        is statistically significant and not an artifact of data snooping.
    """
    gamma = 0.5772156649015328606  # Euler-Mascheroni constant
    
    # Expected maximum Sharpe ratio under the null hypothesis of zero true alpha
    if n_trials > 1:
        z_1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
        z_2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
        exp_max_sr = np.sqrt(var_trials) * ((1.0 - gamma) * z_1 + gamma * z_2)
    else:
        exp_max_sr = 0.0
    
    # Asymptotic standard error of Sharpe ratio under non-Gaussian returns
    # (kurt is EXCESS kurtosis, Gaussian = 0 -> denom reduces to sqrt((1 + 0.5*SR^2) / T))
    denom_se = np.sqrt((1.0 + 0.5 * observed_sharpe**2 - skew * observed_sharpe + (kurt / 4.0) * observed_sharpe**2) / sample_length_days)
    
    if denom_se <= 0:
        return 0.0
    
    dsr_stat = (observed_sharpe - exp_max_sr) / denom_se
    return float(stats.norm.cdf(dsr_stat))
```

---

## 💸 2. Realistic Market Frictions Modeling

Never evaluate strategy returns with naive `pnl = position * returns`. Apply three layers of friction:

```python
def compute_net_strategy_returns(
    position: pd.Series,
    prices: pd.Series,
    half_spread_bps: float = 2.5,   # 2.5 bps per side (0.00025)
    slippage_bps: float = 1.5,      # 1.5 bps execution slippage
    annual_borrow_rate: float = 0.02 # 2% annual cost on short positions
) -> pd.DataFrame:
    """Calculate clean net returns after bid-ask spread, slippage, and borrow costs."""
    log_ret = np.log(prices / prices.shift(1)).fillna(0.0)
    
    # Execution lag: position at t is determined by signal at t-1
    active_position = position.shift(1).fillna(0.0)
    gross_ret = active_position * log_ret
    
    # 1. Turnover & Transaction Costs
    turnover = active_position.diff().abs().fillna(0.0)
    friction_rate = (half_spread_bps + slippage_bps) / 10000.0
    trans_costs = turnover * friction_rate
    
    # 2. Short Borrow Fees
    daily_borrow = (annual_borrow_rate / 252.0)
    borrow_costs = np.where(active_position < 0, np.abs(active_position) * daily_borrow, 0.0)
    
    # 3. Net Returns
    net_ret = gross_ret - trans_costs - borrow_costs
    
    return pd.DataFrame({
        "gross_returns": gross_ret,
        "transaction_costs": trans_costs,
        "borrow_costs": borrow_costs,
        "net_returns": net_ret
    })
```
