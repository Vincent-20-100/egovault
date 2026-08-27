# Covariance Shrinkage, Matrix Stability & Risk Parity (`covariance_shrinkage_and_risk.md`)

> **Linear Algebra Axiom**:
> *« When the number of assets $N$ approaches the number of time observations $T$ ($N/T > 0.1$), the sample covariance matrix becomes mathematically ill-conditioned ($\kappa(A) > 1,000$). Inverting it creates wild, unstable portfolio allocations. »*

---

## 🧮 1. Matrix Condition Number & Stability Check

The **Condition Number** $\kappa(A) = \frac{\lambda_{\max}}{\lambda_{\min}}$ measures how sensitive a linear system or matrix inversion is to numerical errors and small data perturbations:

```python
import numpy as np

def check_covariance_stability(cov_matrix: np.ndarray) -> dict:
    """Inspect eigenvalues and condition number of a covariance matrix."""
    eigenvalues = np.linalg.eigvalsh(cov_matrix)
    min_eig = np.min(eigenvalues)
    max_eig = np.max(eigenvalues)
    
    is_pos_def = min_eig > 1e-8
    cond_number = (max_eig / min_eig) if is_pos_def else np.inf
    
    return {
        "min_eigenvalue": float(min_eig),
        "max_eigenvalue": float(max_eig),
        "condition_number": float(cond_number),
        "is_positive_definite": is_pos_def,
        "is_stable": cond_number < 100.0
    }
```

---

## 🛡️ 2. Ledoit-Wolf Covariance Shrinkage

The **Ledoit-Wolf Estimator** computes the optimal shrinkage intensity $\delta^* \in [0, 1]$ between the noisy sample covariance $S$ and a well-conditioned structured target $F$ (e.g. constant correlation or diagonal variance):

$$\Sigma_{\text{shrunk}} = (1 - \delta^*) S + \delta^* F$$

```python
from sklearn.covariance import LedoitWolf

def compute_shrunk_covariance(returns_df: pd.DataFrame) -> np.ndarray:
    """Fit Ledoit-Wolf optimal shrinkage on asset return matrix."""
    lw = LedoitWolf()
    shrunk_cov = lw.fit(returns_df.values).covariance_
    print(f"Optimal Shrinkage Intensity (delta*): {lw.shrinkage_:.4f}")
    return shrunk_cov
```

---

## 🌳 3. Hierarchical Risk Parity (HRP - No Matrix Inversion)

**Hierarchical Risk Parity (HRP)** by Marcos López de Prado eliminates the need for matrix inversion entirely by using tree clustering (Single Linkage) on the correlation matrix, followed by recursive bisection:

```python
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform

def get_quasi_diag(link: np.ndarray) -> list:
    """Sort clustered items by distance matrix hierarchy."""
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    num_items = link[-1, 3]
    while sort_ix.max() >= num_items:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
        df0 = sort_ix[sort_ix >= num_items]
        i = df0.index
        j = df0.values - num_items
        sort_ix[i] = link[j, 0]
        df0 = pd.Series(link[j, 1], index=i + 1)
        sort_ix = pd.concat([sort_ix, df0]).sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    return sort_ix.tolist()


def compute_hrp_weights(cov: np.ndarray, corr: np.ndarray) -> np.ndarray:
    """Compute Hierarchical Risk Parity portfolio weights without matrix inversion."""
    # 1. Tree Clustering based on correlation distance
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0, 1.0))
    link = sch.linkage(squareform(dist), method="single")
    sort_ix = get_quasi_diag(link)
    
    # 2. Recursive Bisection (Equal Risk allocation across clusters)
    weights = pd.Series(1.0, index=sort_ix)
    c_items = [sort_ix]
    while len(c_items) > 0:
        c_items = [i[j:k] for i in c_items for j, k in ((0, len(i) // 2), (len(i) // 2, len(i))) if len(i) > 1]
        for i in range(0, len(c_items), 2):
            c_items_0 = c_items[i]
            c_items_1 = c_items[i + 1]
            cov_0 = cov[np.ix_(c_items_0, c_items_0)]
            cov_1 = cov[np.ix_(c_items_1, c_items_1)]
            
            # Inverse variance allocation between sub-clusters
            w_0 = 1.0 / np.diag(cov_0)
            w_0 /= w_0.sum()
            v_0 = np.dot(np.dot(w_0, cov_0), w_0)
            
            w_1 = 1.0 / np.diag(cov_1)
            w_1 /= w_1.sum()
            v_1 = np.dot(np.dot(w_1, cov_1), w_1)
            
            alpha_0 = 1.0 - v_0 / (v_0 + v_1)
            weights[c_items_0] *= alpha_0
            weights[c_items_1] *= (1.0 - alpha_0)
            
    return weights.sort_index().values
```
