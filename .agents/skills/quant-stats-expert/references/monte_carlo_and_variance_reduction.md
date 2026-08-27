# Monte Carlo Simulation, Variance Reduction & QMC (`monte_carlo_and_variance_reduction.md`)

> **Monte Carlo Golden Axiom**:
> *« Standard pseudo-random Monte Carlo converges at $\mathcal{O}(N^{-1/2})$. Senior quants and scientific engineers use Variance Reduction (Antithetic, Control Variates) and Quasi-Monte Carlo (Sobol, Latin Hypercube) to achieve $\mathcal{O}(N^{-1})$ precision with 100x fewer simulation paths. »*

---

## 🧭 1. Sampling Method Decision Matrix

| Method | Convergence Rate | Best Use Case | Implementation in Python |
| :--- | :---: | :--- | :--- |
| **Standard Monte Carlo (MC)** | $\mathcal{O}(N^{-1/2})$ | General baseline, high-dimensional irregular domains | `np.random.default_rng(seed).normal()` |
| **Antithetic Variates** | $\mathcal{O}(N^{-1/2})$ *(lower variance constant)* | Monotonic payoffs (European/Asian calls/puts) | Pair $+Z$ with $-Z$ in simulation array |
| **Control Variates** | $\mathcal{O}(N^{-1/2})$ *(drastically reduced variance)* | Payoffs with close analytical twins (e.g. Geometric Asian) | $Y^* = Y - c(X - \mathbb{E}[X])$ |
| **Latin Hypercube (LHS)** | Stratified | Multi-parameter uncertainty & sensitivity analysis | `scipy.stats.qmc.LatinHypercube` |
| **Quasi-Monte Carlo (Sobol)** | $\mathcal{O}(N^{-1})$ | Smooth financial payoffs, pricing options ($d < 20$) | `scipy.stats.qmc.Sobol(d, scramble=True)` |

---

## ⚡ 2. Modern Vectorized Geometric Brownian Motion (GBM)

Use `np.random.default_rng` (never legacy `np.random.seed`) and simulate entire path matrices vectorially:

$$S_{t+\Delta t} = S_t \exp\left( \left( r - \frac{1}{2}\sigma^2 \right)\Delta t + \sigma \sqrt{\Delta t} Z \right)$$

```python
import numpy as np

def simulate_gbm_paths(
    s0: float,
    r: float,
    sigma: float,
    t_years: float,
    n_steps: int,
    n_paths: int,
    rng: np.random.Generator | None = None
) -> np.ndarray:
    """Vectorized simulation of Geometric Brownian Motion asset paths.
    
    Returns:
        Array of shape (n_steps + 1, n_paths) containing simulated price paths.
    """
    if rng is None:
        rng = np.random.default_rng(seed=42)
        
    dt = t_years / n_steps
    drift = (r - 0.5 * sigma**2) * dt
    vol = sigma * np.sqrt(dt)
    
    # Generate all random standard normal shocks in a single contiguous block
    shocks = rng.normal(loc=0.0, scale=1.0, size=(n_steps, n_paths))
    
    # Vectorized log increments
    log_increments = drift + vol * shocks
    
    # Cumulative sum for path dynamics
    log_paths = np.vstack([np.zeros(n_paths), np.cumsum(log_increments, axis=0)])
    
    return s0 * np.exp(log_paths)
```

---

## 🛡️ 3. Variance Reduction Techniques (Production Code)

### A. Antithetic Variates (Halving Variance at Zero Cost)
```python
def price_european_call_antithetic(
    s0: float, k: float, r: float, sigma: float, t_years: float, n_paths: int = 100_000
) -> dict:
    """Price European call using antithetic shocks (Z and -Z)."""
    rng = np.random.default_rng(seed=42)
    half_paths = n_paths // 2
    
    z = rng.normal(size=half_paths)
    z_antithetic = -z
    z_full = np.concatenate([z, z_antithetic])
    
    # Terminal prices
    st = s0 * np.exp((r - 0.5 * sigma**2) * t_years + sigma * np.sqrt(t_years) * z_full)
    payoffs = np.maximum(0.0, st - k) * np.exp(-r * t_years)
    
    # Combine antithetic pairs
    paired_payoffs = 0.5 * (payoffs[:half_paths] + payoffs[half_paths:])
    price = float(np.mean(paired_payoffs))
    std_err = float(np.std(paired_payoffs, ddof=1) / np.sqrt(half_paths))
    
    return {"price": price, "std_error": std_err, "ci_95": (price - 1.96 * std_err, price + 1.96 * std_err)}
```

### B. Control Variates (Pricing Arithmetic Asian via Geometric Twin)
```python
def price_asian_call_control_variate(
    s0: float, k: float, r: float, sigma: float, t_years: float, n_steps: int = 50, n_paths: int = 50_000
) -> dict:
    """Price arithmetic Asian call using analytical geometric Asian as control variate."""
    paths = simulate_gbm_paths(s0, r, sigma, t_years, n_steps, n_paths)
    
    # Target payoff: Arithmetic average Asian option
    arith_avg = np.mean(paths[1:], axis=0)
    y = np.maximum(0.0, arith_avg - k) * np.exp(-r * t_years)
    
    # Control payoff: Geometric average Asian option (exact closed form exists)
    geom_avg = np.exp(np.mean(np.log(paths[1:]), axis=0))
    x = np.maximum(0.0, geom_avg - k) * np.exp(-r * t_years)
    
    # Analytical expected value of Geometric Asian (Black-Scholes with adjusted parameters)
    sig_adj = sigma * np.sqrt((2 * n_steps + 1) / (6 * (n_steps + 1)))
    mu_adj = 0.5 * (r - 0.5 * sigma**2) + 0.5 * sig_adj**2
    d1 = (np.log(s0 / k) + (mu_adj + 0.5 * sig_adj**2) * t_years) / (sig_adj * np.sqrt(t_years))
    d2 = d1 - sig_adj * np.sqrt(t_years)
    import scipy.stats as stats
    exp_x = np.exp(-r * t_years) * (s0 * np.exp(mu_adj * t_years) * stats.norm.cdf(d1) - k * stats.norm.cdf(d2))
    
    # Optimal control coefficient c* = Cov(Y, X) / Var(X)
    cov_matrix = np.cov(y, x)
    c_star = cov_matrix[0, 1] / cov_matrix[1, 1]
    
    # Controlled estimator
    y_controlled = y - c_star * (x - exp_x)
    price = float(np.mean(y_controlled))
    std_err = float(np.std(y_controlled, ddof=1) / np.sqrt(n_paths))
    
    return {"price": price, "std_error": std_err, "variance_reduction_ratio": float(cov_matrix[0, 0] / np.var(y_controlled))}
```

---

## 🔬 4. Quasi-Monte Carlo (Scrambled Sobol Sequences)

Low-discrepancy Sobol sequences distribute points uniformly in the unit hypercube $[0, 1]^d$, eliminating stochastic clumps and voids:

```python
from scipy.stats import qmc, norm

def price_european_option_sobol(
    s0: float, k: float, r: float, sigma: float, t_years: float, n_paths_pow2: int = 16  # 2^16 = 65,536
) -> float:
    """Quasi-Monte Carlo pricing using Scrambled Sobol sequence."""
    n_samples = 2**n_paths_pow2
    sampler = qmc.Sobol(d=1, scramble=True, seed=42)
    uniform_points = sampler.random_base2(m=n_paths_pow2)
    
    # Transform uniform (0, 1) to standard normal quantiles
    z = norm.ppf(np.clip(uniform_points, 1e-7, 1 - 1e-7)).flatten()
    
    st = s0 * np.exp((r - 0.5 * sigma**2) * t_years + sigma * np.sqrt(t_years) * z)
    payoffs = np.maximum(0.0, st - k) * np.exp(-r * t_years)
    
    return float(np.mean(payoffs))
```

---

## 🛑 5. Dynamic Stopping Rules (Convergence Monitor)

Never hardcode arbitrary iteration loops without error monitoring:

```python
def run_monte_carlo_with_stopping_rule(
    simulator_func, target_precision_pct: float = 0.005, batch_size: int = 10_000, max_batches: int = 50
) -> dict:
    """Run simulation incrementally until Relative Standard Error (SE / Mean) < target_precision."""
    accumulated_samples = []
    
    for b in range(1, max_batches + 1):
        batch = simulator_func(batch_size)
        accumulated_samples.extend(batch)
        
        arr = np.array(accumulated_samples)
        mean_est = np.mean(arr)
        std_err = np.std(arr, ddof=1) / np.sqrt(len(arr))
        rel_err = (std_err / abs(mean_est)) if abs(mean_est) > 1e-8 else np.inf
        
        if rel_err <= target_precision_pct:
            return {
                "converged": True,
                "total_samples": len(arr),
                "batches": b,
                "estimate": float(mean_est),
                "std_error": float(std_err),
                "relative_error": float(rel_err)
            }
            
    return {"converged": False, "total_samples": len(accumulated_samples), "estimate": float(np.mean(accumulated_samples))}
```
