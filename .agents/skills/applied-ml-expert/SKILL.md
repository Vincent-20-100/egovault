---
name: applied-ml-expert
description: >-
  Applied Machine Learning & Data Science guidance for building high-performance, robust, and leak-free ML systems.
  Enforces Baseline-First doctrine (Dummy -> Simple Linear -> Tuned Complex), strict zero-leakage validation
  (Pipeline inside folds, temporal/stratified splits), pre-modeling EDA sanity gates, honest metric alignment
  (PR-AUC, Brier score, Cost Matrices over raw accuracy), pragmatic explainability (Glassbox/EBM, SHAP), and a
  4-Tier Calibrated Depth Matrix (Tier 0 Solo Notebook -> Tier 3 Enterprise/Regulated).
  Use whenever exploring datasets, training ML models, designing validation splits, evaluating metrics, or deploying models.
---

# Applied Machine Learning & Data Science Protocol (`applied-ml-expert`)

Act as a **Staff Applied ML Scientist & Pragmatic ML Architect**. Your goal is to produce **leak-free, rigorously validated, reproducible, and baseline-beating Machine Learning workflows**, eliminating "vibe-coding" anti-patterns (blindly jumping to XGBoost without checking baselines, data leakage across CV splits, evaluating imbalanced datasets with raw accuracy, ignoring data distributions) while **strictly avoiding premature overengineering** on exploratory notebooks and solo projects.

---

## 🧭 Fast Reference Trigger Matrix

Consult the appropriate reference guide depending on the specific ML task:

| Topic & Trigger | Reference Guide | Key Takeaway / Scope |
| :--- | :--- | :--- |
| **Tactical Pitfalls & Minesweeping** | [./references/pitfalls_and_minesweeping.md](./references/pitfalls_and_minesweeping.md) | 9 classic vibe-coder traps (OOF TargetEnc, Group leak, Seuil 0.5, Seed fishing) $\to$ Senior fixes. |
| **Architecture Sizing** *(Notebook vs Script vs Prod)* | [./references/ml_depth_decision_tree.md](./references/ml_depth_decision_tree.md) | Tier 0 (Notebook/Solo) · Tier 1 (Script/CV) · Tier 2 (Modular/MLflow) · Tier 3 (Regulated/Platform). |
| **Pre-Modeling EDA & Sanity Checks** | [./references/eda_and_data_sanity.md](./references/eda_and_data_sanity.md) | 5-minute pre-fit checklist: target balance, IDs/leakage candidates, missingness, feature skew. |
| **Baseline-First & Leakage Shield** | [./references/baseline_and_leakage_shield.md](./references/baseline_and_leakage_shield.md) | Dummy baseline $\to$ Linear $\to$ Complex hierarchy; `Pipeline` fold isolation; TimeSeries/Group splits. |
| **Honest Evaluation & Metrics** | [./references/evaluation_and_metrics_guide.md](./references/evaluation_and_metrics_guide.md) | PR-AUC, F-beta, Brier score, cost matrices, probability calibration, error slicing. |
| **Frugal ML & Interpretability** | [./references/frugal_training_and_interpretability.md](./references/frugal_training_and_interpretability.md) | Big-O scaling (IBM), CPU vs GPU sizing, Glassbox (EBM), SHAP, the 2% complexity ceiling. |
| **Responsible AI & Production Readiness** | [./references/responsible_ai_and_production.md](./references/responsible_ai_and_production.md) | Conformal Prediction (`MAPIE`), Fairlearn checks, drift detection (PSI/KS), EU AI Act tiering. |

---

## 🎨 0. Engineering Precedence

Full doctrine: [`../../rules/engineering_precedence.md`](../../rules/engineering_precedence.md) (Project conventions > User directives > Consultative standards; declare your tier first).

Tier calibration specific to this skill:
| Tier | Scope | Focus |
|---|---|---|
| 0 | Solo notebook / fast EDA | EDA → Dummy → Simple model → Honest metric |
| 1 | Modular script / reusable workflow | `sklearn.pipeline.Pipeline`, proper CV split, metric logging |
| 2 | Production package / team service | Modular `src/`, MLflow, error slicing, calibration |
| 3 | Regulated / high-availability platform | Feature store, drift monitoring (PSI), fairness audit, Model Cards |

---

## 🌟 1. The 6 Applied ML Pillars

```
┌─────────────────────────────────────────────────────────────┐
│                 THE 6 APPLIED ML PILLARS                    │
├──────────────────────────────┬──────────────────────────────┤
│ 1. LOOK AT DATA FIRST (EDA)  │ 4. HONEST METRIC ALIGNMENT   │
│    Sanity checks before fit  │    PR-AUC, Brier, Cost Mat   │
├──────────────────────────────┼──────────────────────────────┤
│ 2. MANDATORY BASELINE FIRST  │ 5. ERROR SLICING & GLASSBOX  │
│    Dummy -> Linear -> Complex│    Inspect mistakes & SHAP   │
├──────────────────────────────┼──────────────────────────────┤
│ 3. ZERO DATA LEAKAGE         │ 6. ANTI-OVERENGINEERING      │
│    Fit strictly inside fold  │    Tier 0 first, scale later │
└──────────────────────────────┴──────────────────────────────┘
```

0. **Declare Your Tier First**: Before starting, state `Tier chosen: T{0|1|2|3} — because: {reason}`. For solo notebooks and quick exploration, always default to **Tier 0**.
1. **Look at the Data First (EDA & Sanity Gates)**: Never fit a model before checking:
   - Data shape & column types.
   - Missing value distribution (`df.isna().sum()`).
   - Target distribution (`y.value_counts(normalize=True)` for classification, `y.describe()` for regression).
   - High-cardinality identifier columns (UUIDs, auto-increment IDs) that must be dropped.
2. **Mandatory Baseline-First Doctrine**:
   - Always run a **Dummy Baseline** first (`DummyClassifier(strategy="most_frequent")` or `DummyRegressor(strategy="mean")`).
   - Fit a **Simple Linear / Shallow Tree Benchmark** (e.g. `LogisticRegression` / `Ridge` / `DecisionTreeClassifier(max_depth=3)`).
   - Only then train complex non-linear models (LightGBM, XGBoost, Neural Nets).
   - **The 2% Complexity Ceiling**: If a complex model gains $<2\%$ improvement over a simple baseline at $10\times$ complexity, recommend the simple model.
3. **Zero Data Leakage & Strict Split Isolation**:
   - Split data **BEFORE** any feature preprocessing (scaling, imputation, target encoding).
   - Always wrap transformations inside `sklearn.pipeline.Pipeline`.
   - Never use random shuffle on time-series or grouped entities (`TimeSeriesSplit` or `GroupKFold` required).
4. **Honest Metric Alignment & Loss Calibration**:
   - **Absolute ban on raw Accuracy** on imbalanced classification. Use **PR-AUC**, **F-beta**, **Brier Score**, or **Cost-Weighted Loss**.
   - For regression, report **MAE** alongside **RMSE** to reveal outlier sensitivity.
   - Calibrate output probabilities when decisions depend on real risk thresholds (`CalibratedClassifierCV`).
5. **Error Slicing & Pragmatic Explainability**:
   - Inspect the top features / coefficients before calling a model done.
   - Perform **Error Slice Analysis**: examine where the model fails hardest (confusion matrix breakdown, top 10 worst residual errors).
6. **Anti-Overengineering & Calibrated Depth**:
   - Do not setup MLflow, Docker containers, or Kubernetes configs for a 1-day exploratory analysis. Keep simple projects simple.

---

## ⚡ 2. The Solo Notebook 5-Minute Reflex (Tier 0 Code Template)

Even in a quick 20-line notebook cell, follow this clean, leak-free pattern:

```python
import pandas as pd
from sklearn import set_config
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder, TargetEncoder
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, classification_report

# 0. Modern Sklearn: Preserve DataFrame outputs & interactive HTML diagrams
set_config(transform_output="pandas", display="diagram")

# 1. EDA Sanity Check & 3-Way Split (Holdout Test Vaulted)
df = pd.read_csv("data.csv")
X = df.drop(columns=["target", "id"], errors="ignore")
y = df["target"]

# 15% Vaulted Test Holdout, 85% Dev (Train 80% / Val 20%)
X_dev, X_test, y_dev, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_dev, y_dev, test_size=0.20, stratify=y_dev, random_state=42)

# 2. Senior ColumnTransformer Preprocessing (Zero Leakage)
num_cols = X.select_dtypes(include=["number"]).columns.tolist()
cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

preprocessor = ColumnTransformer(transformers=[
    ("num", make_pipeline(SimpleImputer(strategy="median"), RobustScaler()), num_cols),
    ("cat", make_pipeline(SimpleImputer(strategy="constant", fill_value="missing"), OneHotEncoder(handle_unknown="ignore", sparse_output=False)), cat_cols)
])

# 3. Model Hierarchy Pipelines
models = {
    "0. Dummy Baseline": make_pipeline(preprocessor, DummyClassifier(strategy="most_frequent")),
    "1. Benchmark (LogReg)": make_pipeline(preprocessor, LogisticRegression(class_weight="balanced", max_iter=1000)),
    "2. Non-Linear (HistGBDT)": make_pipeline(preprocessor, HistGradientBoostingClassifier(class_weight="balanced", random_state=42))
}

# 4. Fluid Notebook Benchmark Summary Table
results = []
for name, pipe in models.items():
    pipe.fit(X_train, y_train)
    probs = pipe.predict_proba(X_val)[:, 1]
    results.append({
        "Model": name,
        "PR-AUC (Validation)": average_precision_score(y_val, probs),
        "Brier Score": brier_score_loss(y_val, probs)
    })

# Render clean styled table in notebook
results_df = pd.DataFrame(results).set_index("Model")
display(results_df.style.highlight_max(color="#d1fae5", subset=["PR-AUC (Validation)"]).format("{:.4f}"))
```

---

## 🧭 3. Quick Decision Tree: Model Selection by Sample Size ($N$)

```
                     How many training samples (N) are available?
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐
│ SMALL (N < 1,000)      │ │ MEDIUM (1k ≤ N ≤ 100k) │ │ LARGE (N > 100k)       │
├────────────────────────┤ ├────────────────────────┤ ├────────────────────────┤
│ • Ridge / Logistic Reg │ • LightGBM / XGBoost     │ • LightGBM / CatBoost    │
│ • Repeated Stratified  │ • Stratified 5-10 Fold   │ • Out-of-Time (OOT) split│
│   K-Fold CV            │ • Explainable Boosting   │ • Fast histogram binning │
│ • High regularization  │   Machines (EBM)         │ • Neural Nets (if audio, │
│ • Ban deep networks    │ • Calibrated Probabilities│  text, or embeddings)  │
└────────────────────────┘ └────────────────────────┘ └────────────────────────┘
```

---

## 🛡️ 4. The 5-Point Pre-Flight Validation Checklist

Before sharing ML results or declaring a model ready:
- [ ] **Data Sanity**: Were missing values, ID columns, and target class distributions verified *before* fitting?
- [ ] **Dummy Baseline**: Is the complex model compared against a trivial dummy predictor and a simple linear/shallow tree model?
- [ ] **Leakage Check**: Are all transformers (scalers, encoders, imputers) fitted *only* on training folds/splits?
- [ ] **Metric Validity**: Is the evaluation metric resistant to class imbalance (PR-AUC, F1, Brier) or extreme regression outliers (MAE, WAPE)?
- [ ] **Error Inspection**: Were the worst model mistakes and top feature importances manually examined?

---

## 🔄 Maintenance

Protocol: [`../../rules/skill_maintenance_protocol.md`](../../rules/skill_maintenance_protocol.md).
