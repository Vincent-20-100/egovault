# Honest Evaluation, Metrics & Error Slicing (`evaluation_and_metrics_guide.md`)

> **Core Axiom**: *« A single global accuracy metric hides 90% of model failure modes. Always pair your primary metric with error slice analysis and probability calibration. »*

---

## 🎯 1. The Metric Selection Decision Matrix

### Classification Tasks

| Scenario | Recommended Primary Metric | Secondary / Diagnostic Metric | Why? |
| :--- | :--- | :--- | :--- |
| **Imbalanced Classification** ($< 10\%$ positive) | **PR-AUC** (*Average Precision*) | F-beta ($F_2$ or $F_{0.5}$), Recall@K | Accuracy is deceptive ($99\%$ negative $\implies 99\%$ accuracy with zero skill). PR-AUC focuses on minority class. |
| **Cost-Asymmetric Decisions** (Fraud, Health) | **Cost-Weighted Utility** / Expected Loss | Precision-Recall curve at operating threshold | False Negatives often cost $10\times$ more than False Positives. Optimize the financial cost matrix. |
| **Risk Scoring & Decision Support** | **Brier Score** + Log-Loss | Expected Calibration Error (ECE) | Predictions represent probabilities ($p=0.70$ must mean $70\%$ occurrence). |
| **Balanced Multi-Class** | **Macro-averaged F1** | Confusion Matrix heatmaps | Macro-F1 weights every class equally, preventing dominant classes from masking failures. |

### Regression Tasks

| Scenario | Recommended Primary Metric | Secondary Metric | Why? |
| :--- | :--- | :--- | :--- |
| **Presence of Outliers** | **MAE** (*Mean Absolute Error*) | Median Absolute Error | MAE is linear and robust to extreme tail events. |
| **Penalize Large Errors Heavily** | **RMSE** (*Root Mean Squared Error*) | MAE | Square penalty highlights severe mispredictions. |
| **Business / Executive Reporting** | **WAPE** (*Weighted Absolute % Error*) | MAPE (banned if $y=0$) | $\text{WAPE} = \frac{\sum |y - \hat{y}|}{\sum y}$. Scale-independent and stable with zeros. |

---

## ⚖️ 2. Probability Calibration (`CalibratedClassifierCV`)

Default tree-based models (LightGBM, Random Forest, XGBoost) produce distorted probability distributions clustered away from 0 and 1. If output scores are used for decision thresholds, calibrate them:

```python
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss

# Calibrate a trained tree or linear model using Isotonic Regression or Sigmoid (Platt)
calibrated_model = CalibratedClassifierCV(
    estimator=clf_pipeline,
    method="isotonic",  # Use "sigmoid" if sample size N < 1,000
    cv="prefit"         # Or pass cv=5 if calibrating during CV
)
calibrated_model.fit(X_calib, y_calib)

# Measure calibration quality
probs = calibrated_model.predict_proba(X_test)[:, 1]
brier = brier_score_loss(y_test, probs)
print(f"Brier Score (lower is better): {brier:.4f}")
```

---

## 🔍 3. Error Slice Analysis (The 5-Minute Failure Audit)

Never stop at a single scalar metric. Inspect *where* your model fails:

```python
import pandas as pd
import numpy as np

def audit_model_errors(X_val: pd.DataFrame, y_val: pd.Series, y_pred: np.ndarray, y_proba: np.ndarray) -> None:
    results = X_val.copy()
    results["actual"] = y_val.values
    results["predicted"] = y_pred
    results["prob_pos"] = y_proba
    results["is_error"] = results["actual"] != results["predicted"]
    
    print(f"📉 Overall Error Rate: {results['is_error'].mean():.2%}")
    
    # Analyze error rate by sub-cohorts (e.g. categorical feature)
    for col in results.select_dtypes(include=["object", "category"]).columns:
        slice_perf = results.groupby(col)["is_error"].agg(["count", "mean"]).rename(columns={"mean": "error_rate"})
        high_risk_slices = slice_perf[slice_perf["count"] >= 20].sort_values(by="error_rate", ascending=False)
        if not high_risk_slices.empty and high_risk_slices["error_rate"].iloc[0] > results['is_error'].mean() * 1.5:
            print(f"\n⚠️  High-Error Slice Detected on feature '{col}':\n{high_risk_slices.head(3)}")
```
