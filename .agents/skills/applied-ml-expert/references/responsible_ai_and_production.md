# Responsible AI, Uncertainty & Production Readiness (`responsible_ai_and_production.md`)

> **Context Scope**: This reference applies primarily to **Tier 2 (Production Package / Team Service)** and **Tier 3 (Regulated / High-Availability)** deployments. For Tier 0 solo notebooks, consult this only when uncertainty guarantees or fairness audits are explicit business requirements.

---

## 🎯 1. Uncertainty Quantification & Conformal Prediction (`MAPIE`)

Point predictions provide no guarantee of confidence. Use **Conformal Prediction** via `MAPIE` to obtain mathematically guaranteed prediction sets or intervals at any chosen confidence level $(1 - \alpha)$:

```python
# pip install mapie
from mapie.regression import MapieRegressor
from mapie.classification import MapieClassifier
from sklearn.linear_model import Ridge

# Wrap any scikit-learn estimator with conformal prediction intervals
base_reg = Ridge(alpha=1.0)
mapie = MapieRegressor(estimator=base_reg, cv="prefit")
mapie.fit(X_calib, y_calib)

# Predict with a 90% confidence guarantee (alpha=0.10)
y_pred, y_pis = mapie.predict(X_test, alpha=0.10)
# y_pis contains: [lower_bound, upper_bound] guaranteed to cover ground truth >= 90%
```

### The Reject Option (Abstention Rule)
If the conformal prediction set contains multiple conflicting classes or the regression interval is wider than a business tolerance $\Delta_{\max}$, flag the sample for **human-in-the-loop review** rather than making an unconfident automated decision.

---

## ⚖️ 2. Fairness & Non-Discrimination (`Fairlearn` / EU AI Act)

When building models that impact individuals (credit scoring, hiring, insurance, admissions), evaluate performance across protected attributes (gender, age group, geography):

```python
# pip install fairlearn
from fairlearn.metrics import MetricFrame, selection_rate, true_positive_rate
from sklearn.metrics import accuracy_score

# Evaluate metric parity across demographic slices
metric_frame = MetricFrame(
    metrics={"accuracy": accuracy_score, "selection_rate": selection_rate, "tpr": true_positive_rate},
    y_true=y_val,
    y_pred=y_pred,
    sensitive_features=X_val["age_group"]
)

print(metric_frame.by_group)
# Check for Disparate Impact: selection_rate(group_A) / selection_rate(group_B) >= 0.80 (4/5ths rule)
```

---

## 📡 3. Data & Concept Drift Monitoring (PSI & KS-Test)

### Population Stability Index (PSI)
Use PSI to measure feature distribution shift between baseline training data and production inference batches:

$$\text{PSI} = \sum \left( \% \text{Actual}_i - \% \text{Expected}_i \right) \times \ln\left( \frac{\% \text{Actual}_i}{\% \text{Expected}_i} \right)$$

* $\text{PSI} < 0.10$ : **No significant shift** — model remains stable.
* $0.10 \le \text{PSI} \le 0.25$ : **Moderate shift** — flag for investigation.
* $\text{PSI} > 0.25$ : **Significant drift** — trigger model retraining or fallback baseline.

---

## 📜 4. Minimal Production Model Card Checklist

For Tier 2/3 production deployments, document:
1. **Intended Use**: Target population, business objective, and out-of-scope edge cases.
2. **Baseline Comparison**: Demonstrated lift over trivial Dummy Baseline and Simple Linear model.
3. **Data Provenance**: Training snapshot hash, date range, and sampling strategy.
4. **Failure Modes**: Worst-performing sub-cohorts and known blind spots.
5. **Fallback Plan**: Fallback heuristic or human review queue when inputs are out-of-distribution.
