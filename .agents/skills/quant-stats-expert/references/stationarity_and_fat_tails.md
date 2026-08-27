# Stationarity, Fractional Differentiation & Fat-Tail Risk (`stationarity_and_fat_tails.md`)

> **Statistical Axiom**:
> *« Standard linear statistical models assume stationarity ($I(0)$), and standard risk models assume Gaussian normality. In financial markets, both assumptions are false until proven otherwise. »*

---

## 📈 1. Stationarity Testing Protocol (ADF vs KPSS)

Always test time series with both ADF and KPSS tests:

| ADF ($H_0$: Unit Root / Non-stationary) | KPSS ($H_0$: Stationary) | Diagnostic / Conclusion | Action Required |
| :--- | :--- | :--- | :--- |
| $p > 0.05$ (Fail to reject) | $p < 0.05$ (Reject) | **Strictly Non-Stationary ($I(1)$)** | Differentiate or log-return before modeling. |
| $p < 0.05$ (Reject) | $p > 0.05$ (Fail to reject) | **Strictly Stationary ($I(0)$)** | Safe for standard statistical / ML models. |
| $p < 0.05$ (Reject) | $p < 0.05$ (Reject) | **Trend-Stationary / Struct. Break** | De-trend or split regimes before fitting. |

```python
from statsmodels.tsa.stattools import adfuller, kpss

def check_series_stationarity(series: pd.Series) -> dict:
    """Run dual ADF & KPSS stationarity tests on a financial series."""
    clean_s = series.dropna()
    adf_res = adfuller(clean_s)
    kpss_res = kpss(clean_s, regression="c", nlags="auto")
    
    is_stationary = (adf_res[1] < 0.05) and (kpss_res[1] >= 0.05)
    return {
        "adf_pvalue": float(adf_res[1]),
        "kpss_pvalue": float(kpss_res[1]),
        "is_stationary": is_stationary,
        "recommendation": "Stationary I(0)" if is_stationary else "Differentiate / Return transformation required"
    }
```

---

## 🧠 2. Fractional Differentiation (Preserving Memory)

Integer differentiation ($d=1$, standard returns) completely destroys long-term price memory. **Fractional differentiation** achieves stationarity while retaining maximum memory:

$$(1 - B)^d = \sum_{k=0}^{\infty} (-1)^k \binom{d}{k} B^k = 1 - d B + \frac{d(d-1)}{2!} B^2 - \dots$$

```python
def get_fractional_weights(d: float, size: int) -> np.ndarray:
    """Generate memory weights for fractional differentiation."""
    w = [1.0]
    for k in range(1, size):
        w.append(-w[-1] / k * (d - k + 1))
    return np.array(w[::-1])


def fractional_differentiation(series: pd.Series, d: float, threshold: float = 1e-4) -> pd.Series:
    """Apply fractional differentiation to preserve memory while achieving stationarity."""
    weights = get_fractional_weights(d, len(series))
    weights = weights[abs(weights) > threshold]
    res = np.convolve(series.values, weights, mode="valid")
    return pd.Series(res, index=series.index[len(series) - len(res):])
```

---

## 🌪️ 3. Fat-Tail Risk Metrics (Cornish-Fisher VaR & Expected Shortfall)

Under a Gaussian distribution, a 5-sigma daily drawdown occurs once every 14,000 years. In reality, markets experience 5-sigma moves every few years.

```python
import numpy as np
import scipy.stats as stats

def compute_tail_risk_metrics(returns: pd.Series, alpha: float = 0.01) -> dict:
    """Compute non-Gaussian tail risk metrics (Cornish-Fisher VaR and Expected Shortfall)."""
    mu = returns.mean()
    sigma = returns.std()
    s = stats.skew(returns)
    k = stats.kurtosis(returns) # Excess kurtosis
    
    # 1. Standard Gaussian VaR
    z_norm = stats.norm.ppf(1 - alpha)
    var_gaussian = -(mu - z_norm * sigma)
    
    # 2. Cornish-Fisher Modified VaR (Accounts for skewness & fat tails)
    z_cf = z_norm + (z_norm**2 - 1)*s/6 + (z_norm**3 - 3*z_norm)*k/24 - (2*z_norm**3 - 5*z_norm)*(s**2)/36
    var_cf = -(mu - z_cf * sigma)
    
    # 3. Expected Shortfall (CVaR) - Average loss beyond VaR threshold
    tail_losses = returns[returns <= -var_cf]
    cvar = -tail_losses.mean() if not tail_losses.empty else var_cf
    
    return {
        "Skewness": float(s),
        "Excess Kurtosis": float(k),
        "Gaussian VaR (99%)": float(var_gaussian),
        "Cornish-Fisher VaR (99%)": float(var_cf),
        "Expected Shortfall (CVaR 99%)": float(cvar)
    }
```
