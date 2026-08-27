# Causal Inference & Econometrics in Finance (`causal_inference_and_econometrics.md`)

> **Econometric Law**:
> *« Granger Causality is merely temporal predictability, not causal mechanism. To evaluate market interventions, regulatory changes, or macroeconomic policy shifts, use quasi-experimental causal designs. »*

---

## 🧭 1. Causal Taxonomy for Financial Econometrics

```
┌─────────────────────────────────────────────────────────────┐
│                 CAUSAL INFERENCE TAXONOMY                   │
├──────────────────────────────┬──────────────────────────────┤
│ 1. DIFFERENCE-IN-DIFF (DiD)  │ 3. SYNTHETIC CONTROLS        │
│    Treatment vs Control with │    Weighted donor pool for a │
│    parallel trends test      │    single treated entity     │
├──────────────────────────────┼──────────────────────────────┤
│ 2. INSTRUMENTAL VARS (2SLS)  │ 4. REGRESSION DISCONTINUITY  │
│    Exogenous instrument $Z$  │    Sharp cutoff thresholds   │
│    uncorrelated with error   │    (e.g. index reconstitution│
└──────────────────────────────┴──────────────────────────────┘
```

---

## ⚖️ 2. Difference-in-Differences (DiD with Two-Way Fixed Effects)

To evaluate the effect of an event (e.g. tax change, new regulation) on treated assets vs control assets:

$$Y_{it} = \alpha_i + \gamma_t + \beta \left( \text{Treated}_i \times \text{Post}_t \right) + \epsilon_{it}$$

```python
import statsmodels.api as sm
import statsmodels.formula.api as smf

def estimate_two_way_fixed_effects_did(df: pd.DataFrame) -> dict:
    """Estimate Two-Way Fixed Effects Difference-in-Differences with entity and time clustering.
    
    df must contain: ['outcome', 'treated', 'post', 'entity_id', 'date']
    """
    df['treatment_post'] = df['treated'] * df['post']
    
    # Fit panel model with entity and time fixed effects
    model = smf.ols("outcome ~ treatment_post + C(entity_id) + C(date)", data=df)
    results = model.fit(cov_type="cluster", cov_kwds={"groups": df["entity_id"]})
    
    treatment_effect = results.params["treatment_post"]
    p_value = results.pvalues["treatment_post"]
    
    return {
        "treatment_effect (beta)": float(treatment_effect),
        "std_error": float(results.bse["treatment_post"]),
        "p_value": float(p_value),
        "is_significant_95": p_value < 0.05
    }
```

---

## 🪞 3. Synthetic Control Method (Abadie et al.)

When a single entity is treated (e.g. a country adopting a central bank digital currency, or a major exchange rule change), construct a **Synthetic Twin** from a donor pool of untreated entities using constrained quadratic programming:

$$\min_{W} \| X_1 - X_0 W \|_2^2 \quad \text{s.t.} \quad \sum w_i = 1, \quad w_i \ge 0$$

```python
from scipy.optimize import minimize

def fit_synthetic_control(X_treated: np.ndarray, X_donors: np.ndarray) -> np.ndarray:
    """Find optimal non-negative weights summing to 1 that match pre-treatment characteristics.
    
    X_treated: (k,) vector of pre-treatment characteristics for treated entity.
    X_donors: (k, N_donors) matrix of pre-treatment characteristics for donor pool.
    """
    n_donors = X_donors.shape[1]
    
    def loss(w):
        diff = X_treated - np.dot(X_donors, w)
        return np.sum(diff**2)
    
    bounds = [(0.0, 1.0) for _ in range(n_donors)]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    init_w = np.ones(n_donors) / n_donors
    
    res = minimize(loss, init_w, bounds=bounds, constraints=constraints, method="SLSQP")
    return res.x
```
