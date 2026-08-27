# ML Depth Decision Tree (Anti-Overengineering vs Anti-Vibecoding)

> **Core Philosophy**: Match machine learning engineering depth to problem lifespan, sample size, and business criticality. Never build a multi-stage distributed MLOps platform for an afternoon exploratory notebook, and never deploy an unmonitored bare script into a high-stakes regulated production loop.

---

## 🧭 The 4-Tier Machine Learning Matrix

```
                    ┌──────────────────────────────────────────────┐
                    │ What is the estimated lifecycle, audience,   │
                    │       and risk level of this ML task?        │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌───────────────────┬─────────────┴───────┬───────────────────┐
         ▼                   ▼                     ▼                   ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│ TIER 0 (NOTEBOOK)││ TIER 1 (SCRIPT)  ││ TIER 2 (MODULAR) ││ TIER 3 (PLATFORM)│
│ Solo / Exploratory││ Reusable / Tool ││ Team / Service   ││ Enterprise / AI  │
│ (1 cell / script)││ (100–300 lines)  ││ (300–1500 lines) ││ (Regulated / SLA)│
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
• Single `.ipynb` / `.py`• Clean `.py` functions • `src/` modular layout • Feature Store / dbt
• Zero ceremony     • `sklearn.pipeline`• MLflow tracking   • Formal Model Cards
• EDA sanity gate   • Stratified/Time CV• Error slice audits• Conformal Prediction
• Dummy baseline    • `RandomizedSearchCV`• Probability calib • Automated drift (PSI)
• Simple benchmark  • `joblib.dump`     • Conformal interval• Fairlearn / EU AI Act
```

---

## 📊 Detailed Comparison by Dimension

| Dimension | Tier 0: Solo / Exploratory Notebook | Tier 1: Modular Script / Reusable | Tier 2: Production Package / Team | Tier 3: Regulated / Enterprise Platform |
| :--- | :--- | :--- | :--- | :--- |
| **Typical Target** | Fast dataset dig, Kaggle exploration, quick hypothesis test | Scheduled batch scoring script, internal feature prototype | Microservice endpoint (FastAPI), team-shared model package | High-risk scoring (Credit, Health, Fraud), multi-tenant SLA |
| **File Structure** | `notebook.ipynb` or `explore.py` | `train.py` + `predict.py` | `src/ml_service/{data, features, models, eval}` | Monorepo / Lakehouse integration + CI/CD MLOps |
| **Data Validation** | Manual EDA (`shape`, `value_counts`, `isna`) | Assertions on input schema & null counts | Pandera / Pydantic schema validation contracts | Automated data quality gates + Great Expectations |
| **Baseline Protocol** | Dummy (Mean / Majority) + Logistic / Ridge | Dummy + 2-3 benchmarks across $K$-folds | Baseline registry + automated regression tests | Production champion/challenger shadow deployments |
| **Leakage Defense** | Manual split before any feature scaling | Strict `sklearn.pipeline.Pipeline` | Modular pipeline with strict frozen artifacts | Immutable feature snapshots + point-in-time joins |
| **Experiment Tracking**| In-memory dict / printed metrics | Run summaries saved to JSON / CSV | Local MLflow / Weights & Biases tracking | Central MLflow / S3 model registry + DVC hashes |
| **Interpretability** | Global feature importances / correlations | Top 10 coefficients or simple decision tree | `TreeSHAP` / `InterpretML` (EBM) + Error slices | Full Model Card + Fairlearn bias audit + EU AI Act |

---

## 🚫 The Anti-Pattern Traps

### Trap A: The "Vibe-Coding Slop" (Under-engineering)
* **Symptoms**:
  - Training LightGBM or a Neural Net without ever computing what a trivial dummy baseline (majority class) scores.
  - Calling `scaler.fit_transform(X)` on the *entire* dataset before `train_test_split()`.
  - Reporting 98% accuracy on a dataset where 98% of cases are negative.
  - Ignoring obvious UUIDs or IDs that leak 100% correlation with target.
* **Remedy**: Follow the **Tier 0 Sanity Reflex** (EDA $\to$ Split $\to$ Dummy $\to$ Simple Pipeline $\to$ PR-AUC).

### Trap B: The "MLOps Astronaut" (Premature Overengineering)
* **Symptoms**:
  - Setting up Kubernetes clusters, Kubeflow DAGs, Feast Feature Stores, and 10 microservices for a 500-row CSV analysis.
  - Spending 3 days tuning Optuna hyperparameters on a noisy dataset with $N < 200$.
  - Refusing to write a simple 30-line script because "it doesn't have hexagonal layer abstraction".
* **Remedy**: Downgrade immediately to **Tier 0** or **Tier 1**. Solve the business question first with clean, lightweight Python before adding platform scaffolding.

---

## 🎯 When to Graduate Tiers

```
[Tier 0: Notebook] ──▶ When script runs > 3 times or shared with peer ──▶ [Tier 1: Clean Script]
[Tier 1: Clean Script] ──▶ When serving predictions via API / automated cron ──▶ [Tier 2: Modular Service]
[Tier 2: Modular Service] ──▶ When decisions impact human rights / regulated finances ──▶ [Tier 3: Regulated Platform]
```
