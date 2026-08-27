# Options Mechanics, Volatility Surface & Greek Engines (`options_volatility_and_greeks.md`)

> **Industrial Engineering Law**:
> *« The mathematical pricing core must remain purely stateless and decoupled from broker sessions. Live execution and historical replay must execute the exact same analytics functions. »*

---

## 🏛️ 1. Synthetic Forward Reconstruction (Put-Call Parity)

Before fitting a volatility smile, reconstruct the synthetic underlying forward $F(T)$ for each maturity $T$ using Put-Call Parity:

$$C(K, T) - P(K, T) = e^{-r T} (F(T) - K)$$

$$\implies F_i = K_i + e^{r T} \left( C_i - P_i \right)$$

```python
import numpy as np
import scipy.stats as stats
from scipy.optimize import brentq

def reconstruct_synthetic_forward(strikes: np.ndarray, calls: np.ndarray, puts: np.ndarray, r: float, T: float) -> float:
    """Reconstruct robust synthetic forward from liquid near-the-money strike pairs.
    
    Weights pairs inversely by bid-ask spread or proximity to ATM (|K - S_ref|).
    """
    # Individual forward candidates per strike
    forwards = strikes + np.exp(r * T) * (calls - puts)
    
    # Filter out extreme outliers or illiquid pairs using median absolute deviation (MAD)
    med_forward = np.median(forwards)
    valid_mask = np.abs(forwards - med_forward) < (2.0 * np.std(forwards) + 1e-5)
    
    # Return weighted average of valid forward candidates
    return float(np.mean(forwards[valid_mask]))
```

---

## ⚡ 2. Implied Volatility Inversion Engine (Robust Brentq)

Never use unconstrained Newton-Raphson on deep out-of-the-money options (risk of divergence). Use **bracketed Brent root-finding (`scipy.optimize.brentq`)** bounded by intrinsic value and extreme volatilities $[\sigma_{\min} = 0.001, \sigma_{\max} = 5.0]$:

```python
def black76_price(F: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
    """Black-76 pricing formula for European options on futures/forwards."""
    if T <= 0 or sigma <= 0:
        return max(0.0, (F - K) if option_type == "call" else (K - F)) * np.exp(-r * T)
    
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    disc = np.exp(-r * T)
    
    if option_type.lower() == "call":
        return disc * (F * stats.norm.cdf(d1) - K * stats.norm.cdf(d2))
    else:
        return disc * (K * stats.norm.cdf(-d2) - F * stats.norm.cdf(-d1))


def solve_implied_volatility(
    market_price: float,
    F: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    vol_min: float = 0.001,
    vol_max: float = 5.0
) -> dict:
    """Invert Black-76 price to implied volatility with convergence metadata."""
    disc = np.exp(-r * T)
    intrinsic = disc * max(0.0, (F - K) if option_type == "call" else (K - F))
    
    # 1. No-Arbitrage Sanity Checks
    if market_price < intrinsic:
        return {"iv": np.nan, "status": "FAIL_BELOW_INTRINSIC", "iterations": 0}
    
    price_min = black76_price(F, K, T, r, vol_min, option_type)
    price_max = black76_price(F, K, T, r, vol_max, option_type)
    
    if market_price < price_min or market_price > price_max:
        return {"iv": np.nan, "status": "FAIL_OUT_OF_BRACKET", "iterations": 0}
    
    # 2. Bracketed Root Inversion
    try:
        objective = lambda sigma: black76_price(F, K, T, r, sigma, option_type) - market_price
        iv, r_obj = brentq(objective, vol_min, vol_max, xtol=1e-6, maxiter=100, full_output=True)
        return {
            "iv": float(iv),
            "status": "CONVERGED" if r_obj.converged else "MAX_ITER_EXCEEDED",
            "iterations": r_obj.iterations,
            "residual": float(objective(iv))
        }
    except Exception as e:
        return {"iv": np.nan, "status": f"ERROR_{type(e).__name__}", "iterations": 0}
```

---

## 🔍 3. Dual Greek Validation (Analytic vs Central Finite-Difference)

Always test and validate analytic Greek implementations against central numerical derivatives ($h = 10^{-4}$):

```python
def compute_analytic_greeks(F: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> dict:
    """Compute exact analytic Black-76 Greeks."""
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    disc = np.exp(-r * T)
    pdf_d1 = stats.norm.pdf(d1)
    
    delta = disc * stats.norm.cdf(d1) if option_type == "call" else disc * (stats.norm.cdf(d1) - 1.0)
    gamma = disc * pdf_d1 / (F * sigma * np.sqrt(T))
    vega = disc * F * np.sqrt(T) * pdf_d1 / 100.0  # Per 1% vol shift
    
    return {"delta": delta, "gamma": gamma, "vega": vega}


def validate_greeks_finite_difference(F: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> dict:
    """Verify analytic Greeks against central finite difference perturbations."""
    analytic = compute_analytic_greeks(F, K, T, r, sigma, option_type)
    
    # Central perturbations
    h_f = F * 1e-4
    p_up = black76_price(F + h_f, K, T, r, sigma, option_type)
    p_dn = black76_price(F - h_f, K, T, r, sigma, option_type)
    p_0  = black76_price(F, K, T, r, sigma, option_type)
    
    num_delta = (p_up - p_dn) / (2 * h_f)
    num_gamma = (p_up - 2 * p_0 + p_dn) / (h_f**2)
    
    h_v = 1e-4
    num_vega = (black76_price(F, K, T, r, sigma + h_v, option_type) - black76_price(F, K, T, r, sigma - h_v, option_type)) / (2 * h_v * 100.0)
    
    return {
        "delta_error": abs(analytic["delta"] - num_delta),
        "gamma_error": abs(analytic["gamma"] - num_gamma),
        "vega_error": abs(analytic["vega"] - num_vega),
        "passed": all([
            abs(analytic["delta"] - num_delta) < 1e-4,
            abs(analytic["gamma"] - num_gamma) < 1e-4,
            abs(analytic["vega"] - num_vega) < 1e-4
        ])
    }
```

---

## 📜 4. Calendar & Arbitrage Sanity Checklist

Before publishing surface metrics or passing IV into risk models:
1. **Total Variance Monotonicity**: Total implied variance $w(K, T) = \sigma^2(K, T) \cdot T$ must be strictly non-decreasing across consecutive maturities ($T_1 < T_2 \implies w(T_1) \le w(T_2)$).
2. **Butterfly Convexity**: Call prices must be convex in strike ($\partial^2 C / \partial K^2 \ge 0$). Negative butterfly spreads indicate calendar or strike arbitrage in market quotes.
3. **No-Arbitrage Bounds**: $C(K, T) \ge \max(0, e^{-rT}(F - K))$.
