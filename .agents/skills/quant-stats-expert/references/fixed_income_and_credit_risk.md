# Fixed Income, Term Structure & Credit Risk (`fixed_income_and_credit_risk.md`)

> **Fixed Income Core Principle**:
> *« A bond is a series of deterministic or floating cash flows whose present value reflects both the term structure of interest rates and the market price of credit default risk. »*

---

## 🧭 1. Term Structure & Forward Rates Bootstrapping

The relationship between spot zero-coupon rates $r(T)$ and the instantaneous forward rate $f(t_1, t_2)$ is defined by no-arbitrage:

$$(1 + r(t_2))^{t_2} = (1 + r(t_1))^{t_1} \cdot (1 + f(t_1, t_2 - t_1))^{t_2 - t_1}$$

```python
import numpy as np
import pandas as pd

def compute_forward_rate(r_t1: float, t1: float, r_t2: float, t2: float) -> float:
    """Compute forward rate f(t1, t2 - t1) from spot rates."""
    assert t2 > t1, "t2 must be strictly greater than t1"
    f = (((1.0 + r_t2)**t2) / ((1.0 + r_t1)**t1))**(1.0 / (t2 - t1)) - 1.0
    return float(f)
```

---

## 📉 2. Duration, Modified Duration & Convexity

A second-order Taylor expansion approximates bond price changes with respect to yield changes $\Delta y$:

$$\frac{\Delta P}{P} \approx - D_{\text{mod}} \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2$$

Where Modified Duration $D_{\text{mod}} = \frac{D_{\text{mac}}}{1 + y}$ and Convexity $C = \frac{1}{P} \frac{\partial^2 P}{\partial y^2}$.

```python
def compute_bond_sensitivities(cash_flows: np.ndarray, times: np.ndarray, y: float) -> dict:
    """Calculate clean price, Macaulay duration, Modified duration, and Convexity.
    
    cash_flows: Array of coupons and principal at each payment time.
    times: Array of payment times in years (e.g. [1, 2, 3, 4, 5]).
    y: Annual yield to maturity (e.g. 0.045).
    """
    discount_factors = (1.0 + y)**(-times)
    pv_cf = cash_flows * discount_factors
    price = np.sum(pv_cf)
    
    # Macaulay & Modified Duration
    mac_duration = np.sum(times * pv_cf) / price
    mod_duration = mac_duration / (1.0 + y)
    
    # Convexity
    convexity = np.sum(times * (times + 1.0) * cash_flows * (1.0 + y)**(-(times + 2.0))) / price
    
    return {
        "price": float(price),
        "macaulay_duration": float(mac_duration),
        "modified_duration": float(mod_duration),
        "convexity": float(convexity),
        "dv01": float(price * mod_duration * 0.0001)  # Dollar value of 1 basis point
    }
```

---

## 🏦 3. Credit Risk: Risk-Neutral Default Trees & CVA

Under the risk-neutral measure $\mathbb{Q}$, with annual default probability $q$ and Recovery Rate $R = 1 - \text{LGD}$:

$$\text{Bond Price} = \sum_{t=1}^T \text{CF}_t (1 - q)^t e^{-r t} + \sum_{t=1}^T R \cdot \text{FaceValue} \cdot (1 - q)^{t-1} q e^{-r t}$$

```python
from scipy.optimize import brentq

def price_risky_bond_with_cva(
    coupon_rate: float,
    maturity: int,
    risk_free_rate: float,
    annual_default_prob: float,
    recovery_rate: float = 0.40,
    face_value: float = 100.0
) -> dict:
    """Price a credit-risky bond and decompose Credit Value Adjustment (CVA)."""
    coupon = coupon_rate * face_value
    cash_flows = [(t, coupon if t < maturity else coupon + face_value) for t in range(1, maturity + 1)]
    risk_free_price = 0.0
    risky_price = 0.0
    
    # Cumulative survival probability
    surv_prob = 1.0
    
    for t, cf in cash_flows:
        df = np.exp(-risk_free_rate * t)
        
        # Risk-free cash flow
        risk_free_price += cf * df
        
        # Marginal default in year t
        prob_default_t = surv_prob * annual_default_prob
        prob_survive_t = surv_prob * (1.0 - annual_default_prob)
        
        # Expected cash flow under risk-neutral credit tree
        expected_cf = prob_survive_t * cf + prob_default_t * (recovery_rate * face_value)
        risky_price += expected_cf * df
        
        surv_prob = prob_survive_t
        
    cva = risk_free_price - risky_price
    
    # Implied credit spread: solve flat yield y_risky matching cash flows to risky_price
    def _pv_at_yield(y: float) -> float:
        return sum(cf * np.exp(-y * t) for t, cf in cash_flows) - risky_price

    y_risky = brentq(_pv_at_yield, -0.50, 5.0, xtol=1e-8)
    credit_spread = y_risky - risk_free_rate
    
    return {
        "risk_free_price": float(risk_free_price),
        "risky_price": float(risky_price),
        "cva": float(cva),
        "implied_credit_spread_bps": float(max(0.0, credit_spread * 10000.0))
    }
```

---

## 🔀 4. Convertible Bond Decomposition & Greeks

A **Convertible Bond (CB)** gives the investor the right to convert debt into common stock at conversion price $K_{\text{conv}}$:

$$\text{CB Price} \approx \text{Straight Bond Floor} + \text{Forward-Start Equity Call Option}$$

Key Greek Sensitivities:
* **$\Delta$ (Delta)**: Sensitivity to underlying stock price changes ($\Delta \to 1$ when deep in-the-money).
* **$\Gamma$ (Gamma)**: Curvature of conversion value (maximum around ATM conversion price).
* **$O$ (Omicron)**: Sensitivity to widening credit spreads ($\frac{\partial \text{CB}}{\partial s_{\text{credit}}} < 0$, affecting the bond floor).
* **Convertible Arbitrage**: Long CB + Short $\Delta$ Shares of equity + Buy CDS (Credit Default Swap) to isolate pure volatility mispricing.
