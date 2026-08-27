# Baseline-First Protocol, 3-Way Split & Senior Scikit-Learn Pipelines (`baseline_and_leakage_shield.md`)

> **The Golden Law of Applied ML**:
> *« You do not have a Machine Learning model until you have beaten a Dummy Baseline, and you do not have a trustworthy score unless all transformations are isolated inside an end-to-end Pipeline evaluated across a strict Train / Validation / Test protocol. »*

---

## 🏛️ 1. The 3-Way Split Protocol (Train / Validation / Test)

Never evaluate multiple models or tune hyperparameters directly on your final test set. Always establish a strict 3-way partition:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               TOTAL DATASET (100%)                                     │
├──────────────────────────────────────────────────────┬─────────────────────────────────┤
│            DEVELOPMENT SET (80% – 85%)               │     FINAL TEST HOLDOUT (15%)    │
│  (Used for iterative modeling, CV & tuning)          │ (VAULTED: Evaluated ONCE at end)│
├──────────────────────────┬───────────────────────────┤                                 │
│    TRAIN SET (70% dev)   │   VALIDATION SET (30% dev)│                                 │
│ (Fit model & transforms) │ (Select model & threshold)│                                 │
└──────────────────────────┴───────────────────────────┴─────────────────────────────────┘
```

### The Inviolable Vault Rule
* **Train**: Used to `fit()` transformers and estimators.
* **Validation / CV Folds**: Used to tune hyperparameters, compare models against the Dummy baseline, and calibrate decision thresholds ($\theta^*$).
* **Test Holdout**: Evaluated **EXACTLY ONCE** on the final champion model. If you adjust hyperparameters after looking at Test scores, your test set is contaminated (*Data Snooping*).

---

## 🛡️ 2. The Senior Scikit-Learn Pipeline Blueprint (Pandas Output + ColumnTransformer)

Modern scikit-learn (v1.2+) natively supports DataFrame outputs and interactive HTML pipeline diagrams. Follow this production-grade template:

```python
import pandas as pd
import numpy as np
import sklearn
from sklearn import set_config
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder, TargetEncoder
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    ConfusionMatrixDisplay,
    PrecisionRecallDisplay
)

# 1. Enable Pandas DataFrame output and rich interactive HTML diagrams in notebooks
set_config(transform_output="pandas", display="diagram")

# 2. Strict 3-Way Split (Holdout Test Vaulted)
X = df.drop(columns=["target", "user_id"], errors="ignore")
y = df["target"]

# Split 1: Isolate pure final test set (15%)
X_dev, X_test, y_dev, y_test = train_test_split(
    X, y, test_size=0.15, stratify=y, random_state=42
)

# Split 2: Split dev into train and validation (or use 5-fold CV on X_dev)
X_train, X_val, y_train, y_val = train_test_split(
    X_dev, y_dev, test_size=0.20, stratify=y_dev, random_state=42
)

# 3. Categorize Feature Types
num_features = ["age", "income", "tenure", "transaction_count"]
cat_low_card = ["country", "device_type", "subscription_tier"]
cat_high_card = ["postal_code", "merchant_category"]

# 4. Modular Preprocessing Sub-Pipelines
numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", RobustScaler())  # RobustScaler handles outliers better than StandardScaler
])

cat_low_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
    ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])

cat_high_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
    ("target_enc", TargetEncoder(cv=5, smooth="auto", random_state=42))  # Out-of-fold target encoding
])

preprocessor = ColumnTransformer(
    transformers=[
        ("num", numeric_transformer, num_features),
        ("cat_low", cat_low_transformer, cat_low_card),
        ("cat_high", cat_high_transformer, cat_high_card)
    ],
    remainder="drop"
)
```

---

## 📊 3. Fluid Notebook Comparison & Display Patterns

In Jupyter or Marimo notebooks, present model benchmarks with structured summary DataFrames and visual diagnostic displays:

```python
# 5. Define Candidate Pipelines
dummy_pipe = make_pipeline(preprocessor, DummyClassifier(strategy="most_frequent"))
linear_pipe = make_pipeline(preprocessor, LogisticRegression(class_weight="balanced", max_iter=1000))
gbdt_pipe = make_pipeline(preprocessor, HistGradientBoostingClassifier(class_weight="balanced", random_state=42))

models = {
    "0. Dummy (Most Frequent)": dummy_pipe,
    "1. Benchmark (Logistic Reg)": linear_pipe,
    "2. Non-Linear (HistGBDT)": gbdt_pipe
}

# 6. Evaluate all candidates on Validation Set
results = []
for name, model in models.items():
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_val)[:, 1]
    preds = (probs >= 0.5).astype(int)
    
    results.append({
        "Model": name,
        "PR-AUC (Primary)": average_precision_score(y_val, probs),
        "Brier Score": brier_score_loss(y_val, probs),
        "Recall (Class 1)": (preds[y_val == 1] == 1).mean()
    })

# 7. Render Clean Comparison Table in Notebook
results_df = pd.DataFrame(results).set_index("Model")
display(results_df.style.highlight_max(color="#d1fae5", subset=["PR-AUC (Primary)", "Recall (Class 1)"])
                        .highlight_min(color="#dbeafe", subset=["Brier Score"])
                        .format("{:.4f}"))

# 8. Visual Diagnostic Displays (Confusion Matrix & PR Curve)
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
ConfusionMatrixDisplay.from_estimator(gbdt_pipe, X_val, y_val, ax=ax1, cmap="Blues", colorbar=False)
ax1.set_title("Validation Confusion Matrix (GBDT)")

PrecisionRecallDisplay.from_estimator(gbdt_pipe, X_val, y_val, ax=ax2, name="GBDT")
PrecisionRecallDisplay.from_estimator(linear_pipe, X_val, y_val, ax=ax2, name="LogisticReg")
ax2.set_title("Precision-Recall Curve Comparison")
plt.tight_layout()
plt.show()

# 9. FINAL STEP: Evaluate the Selected Champion ONCE on Test Holdout
print("=" * 60)
print("🏆 FINAL CHAMPION EVALUATION ON VAULTED TEST HOLDOUT")
print("=" * 60)
test_probs = gbdt_pipe.predict_proba(X_test)[:, 1]
print(f"Final Test PR-AUC: {average_precision_score(y_test, test_probs):.4f}")
print(f"Final Test Brier:  {brier_score_loss(y_test, test_probs):.4f}")
print("\n" + classification_report(y_test, gbdt_pipe.predict(X_test)))
```

---

## 🧭 4. Split Strategy Decision Tree

```
                   What is the structure of your data?
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ INDEPENDENT I.I.D│       │ TIME-SERIES /    │       │ GROUPED ENTITIES │
│ SAMPLES          │       │ TEMPORAL ORDER   │       │ (Users / Stores) │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ StratifiedKFold  │       │ TimeSeriesSplit  │       │ GroupKFold       │
│ • Preserves class│       │ • Expanding or   │       │ • All rows of a  │
│   ratios in each │         rolling windows  │         group stay in    │
│   fold           │       │ • Never look into│         train OR val     │
│ • Shuffle = True │         the future       │       │ • Prevents group │
│                  │       │ • Shuffle = False│         memorization     │
└──────────────────┘       └──────────────────┘       └──────────────────┘
```
