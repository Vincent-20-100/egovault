# Frugal Training, Hardware Sizing & Interpretability (`frugal_training_and_interpretability.md`)

> **Guiding Principle**: *« High-performance machine learning is not about training the largest possible model on the biggest GPU; it is about finding the minimal necessary complexity that solves the business objective transparently. »*

---

## ⚡ 1. Computational Complexity & Hardware Sizing (IBM Best Practices)

Understanding computational complexity in Big-O notation prevents runaway memory allocation and training hangs:

| Algorithm Class | Training Complexity | Inference Latency | Hardware Recommendation | Max Recommended $N$ on Single CPU |
| :--- | :--- | :--- | :--- | :--- |
| **Linear / Logistic Reg** | $O(N \cdot d)$ | $< 0.1\text{ ms}$ | Standard CPU | Millions of rows |
| **Decision Trees** | $O(d \cdot N \log N)$ | $< 0.1\text{ ms}$ | Standard CPU | Hundreds of thousands |
| **Random Forest** | $O(T \cdot d \cdot N \log N)$ | $1\text{–}10\text{ ms}$ | Multi-core CPU | $\sim 500,000$ rows |
| **GBDT (LightGBM/XGBoost)** | $O(T \cdot K \cdot N \cdot d_{\text{bins}})$ | $0.5\text{–}5\text{ ms}$ | Multi-core CPU (GPU for $N > 1\text{M}$) | Millions of rows |
| **Kernel SVM** | $O(d \cdot N^2)$ to $O(d \cdot N^3)$ | $O(N_{\text{sv}} \cdot d)$ | Multi-core CPU | **$N < 50,000$ ONLY** (Do not use on large $N$) |
| **Deep Neural Networks** | $O(\text{Epochs} \cdot N \cdot \text{FLOPs})$ | $5\text{–}100\text{ ms}$ | GPU / TPU | Tabular: prefer GBDT unless tabular embeddings required |

---

## 🔍 2. Glassbox Models vs Blackbox Explainers

Before reaching for an uninterpretable deep ensemble, consider an **intrinsically interpretable Glassbox model**:

### Option A: Explainable Boosting Machines (`interpret.glassbox.ExplainableBoostingClassifier`)
EBMs (from Microsoft InterpretML) provide accuracy competitive with LightGBM/XGBoost while producing exact, additive feature curves and pairwise interactions:

```python
# pip install interpret
from interpret.glassbox import ExplainableBoostingClassifier

ebm = ExplainableBoostingClassifier(random_state=42)
ebm.fit(X_train, y_train)

# EBM provides exact glassbox explanations without approximation
ebm_global = ebm.explain_global()
# ebm_global.show() # Interactive visualization of feature curves
```

### Option B: Fast TreeSHAP for GBDT Models
For LightGBM / XGBoost, use `TreeSHAP` to inspect local and global contributions:

```python
import shap
import lightgbm as lgb

model = lgb.LGBMClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# TreeExplainer runs in exact polynomial time for tree models
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_val)

# Quick summary bar plot of top driver features
# shap.summary_plot(shap_values, X_val, plot_type="bar")
```

---

## ✂️ 3. The 3 Rules of Frugal ML

1. **Prune Redundant Features First**: A 15-feature model that captures 98% of the signal is vastly superior to a 200-feature model that memorizes noise.
2. **Early Stopping is Mandatory**: Always use `early_stopping_rounds=20` to prevent wasted compute and overfitting.
3. **Limit Tree Depth**: In tabular GBDT, `max_depth=4` to `6` and `num_leaves=15` to `31` almost always matches deep trees while being $3\times$ faster and less prone to overfitting.
