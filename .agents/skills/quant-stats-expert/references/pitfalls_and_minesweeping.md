# Tactical Quantitative Pitfalls & Senior Minesweeping Guide (`pitfalls_and_minesweeping.md`)

> **Quantitative Golden Rule**:
> *« In statistical finance, a bug does not crash with a SyntaxError—it rewards you with a Sharpe ratio of 4.5 that evaporates into immediate drawdown in live trading. »*

---

## 🧭 The 8 Classic Quant Traps vs Senior Demining Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                   TACTICAL QUANTITATIVE & STATISTICAL MINESWEEPING MATRIX                       │
├────────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│ 1. SAME-BAR LOOKAHEAD (SHIFT)  │ 2. RÉGRESSION SPURIEUSE (ADF)  │ 3. LE PIÈGE GAUSSIEN (TAILS)  │
│ ⚠️ Signal à t calcule avec t   │ ⚠️ Regresser des prix bruts I(1│ ⚠️ VaR gaussienne (Z-score)   │
│ 🛡️ Shift(1) & execution delay  │ 🛡️ ADF test & log-returns I(0) │ 🛡️ Cornish-Fisher VaR & CVaR │
├────────────────────────────────┼────────────────────────────────┼───────────────────────────────┤
│ 4. SHARPE SUR-AJUSTÉ (DSR)     │ 5. CV NON PURGÉE (CPCV)        │ 6. MONDE SANS FRICTION        │
│ ⚠️ Tester 1000 params, garder 1│ ⚠️ Fuite sérielle entre folds  │ ⚠️ PnL = returns * position   │
│ 🛡️ Deflated Sharpe Ratio (DSR) │ 🛡️ Purged & Embargoed K-Fold   │ 🛡️ Spread + Slippage + Borrow │
├────────────────────────────────┼────────────────────────────────┼───────────────────────────────┤
│ 7. MARKOWITZ EXPLOSIF (κ(A))   │ 8. CAUSALITÉ vs CORRÉLATION    │                               │
│ ⚠️ Inverser covariance brute   │ ⚠️ Granger = vraie causalité   │                               │
│ 🛡️ Shrinkage Ledoit-Wolf & HRP │ 🛡️ Diff-in-Diff / Synth Ctrl   │                               │
└────────────────────────────────┴────────────────────────────────┴───────────────────────────────┘
```

---

## 💣 1. Le Piège du Lookahead Bias (Exécution Même Barre)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR FATALE : Le signal à la bougie t est calculé avec le 'close' de t,
# et le trade est exécuté au 'close' de t (ou pire, au 'open' de t) !
df['signal'] = np.where(df['close'] > df['close'].rolling(20).mean(), 1, -1)
df['strategy_returns'] = df['signal'] * df['close'].pct_change() # <-- Voyage dans le temps
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Le signal calculé à t ne peut être exécuté qu'à t+1 (au open de t+1 ou au close de t+1)
df['signal'] = np.where(df['close'] > df['close'].rolling(20).mean(), 1, -1)
# Exécution réaliste : la position effective à t+1 est le signal issu de t
df['position'] = df['signal'].shift(1)
df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
df['strategy_returns'] = df['position'] * df['log_returns']
```

---

## 💣 2. La Régression Spurieuse sur Prix Non-Stationnaires

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Régresser deux marches aléatoires I(1) indépendantes (ex: Prix BTC vs Prix CAC40)
# Donne un R² de 0.95 et une p-value de 0.00001 : corrélation purement illusoire !
import statsmodels.api as sm
model = sm.OLS(df['btc_price'], sm.add_constant(df['cac_price'])).fit()
print(f"R² illusoire : {model.rsquared:.4f}")
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Tester la stationnarité (ADF test). Si non-stationnaire, travailler en rendements stationnaires I(0)
from statsmodels.tsa.stattools import adfuller

# 1. Test ADF sur les niveaux
adf_pval_btc = adfuller(df['btc_price'].dropna())[1]
adf_pval_cac = adfuller(df['cac_price'].dropna())[1]

# Si p-value > 0.05 -> Non-stationnaire -> Différenciation obligatoire
ret_btc = np.log(df['btc_price'] / df['btc_price'].shift(1)).dropna()
ret_cac = np.log(df['cac_price'] / df['cac_price'].shift(1)).dropna()

real_model = sm.OLS(ret_btc, sm.add_constant(ret_cac)).fit()
print(f"R² réel stationnaire : {real_model.rsquared:.4f} (p-val: {real_model.pvalues.iloc[1]:.4f})")
```

---

## 💣 3. Le Piège Gaussien (Fat Tails & Risque Extrême Ignorés)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Calculer la VaR 99% avec la formule normale Z * sigma
# Sous-estime massivement les crashs de marché (kurtosis >> 3)
var_99_gaussian = -(returns.mean() - 2.326 * returns.std())
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Utiliser la Value-at-Risk de Cornish-Fisher (qui ajuste le quantile selon Skewness et Kurtosis)
import scipy.stats as stats

z = stats.norm.ppf(0.99) # 2.326
s = stats.skew(returns)
k = stats.kurtosis(returns) # Excess kurtosis

# Expansion polynomiale de Cornish-Fisher
z_cf = z + (z**2 - 1)*s/6 + (z**3 - 3*z)*k/24 - (2*z**3 - 5*z)*(s**2)/36
cf_var_99 = -(returns.mean() - z_cf * returns.std())

# Expected Shortfall (CVaR) : moyenne des pertes au-delà de la VaR
cvar_99 = -returns[returns <= -cf_var_99].mean()
print(f"VaR 99% Gaussienne      : {var_99_gaussian:.2%}")
print(f"VaR 99% Cornish-Fisher  : {cf_var_99:.2%} (Prend en compte les queues épaisses)")
print(f"CVaR 99% (Pertes crash) : {cvar_99:.2%}")
```

---

## 💣 4. Le Sharpe Ratio Sur-Ajusté (Biais d'Essais Multiples)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Tester 500 combinaisons de moyennes mobiles sur 2 ans d'historique,
# sélectionner la meilleure avec Sharpe = 2.1 et affirmer qu'elle battra le marché.
```

### 🛡️ Le Déminage Senior (Deflated Sharpe Ratio - Marcos López de Prado)
```python
# ✅ SOLUTION : Calculer le Deflated Sharpe Ratio (DSR) qui pénalise le nombre d'essais N_trials
def deflated_sharpe_ratio(estimated_sharpe, n_trials, var_sharpe_trials, sample_length_t, skew, kurt):
    """Calcule la probabilité que le Sharpe observé dépasse le seuil d'espérance nulle après N essais."""
    # Espérance du Sharpe maximum sous l'hypothèse nulle (Euler-Mascheroni approximation)
    gamma = 0.5772156649
    exp_max_sharpe = np.sqrt(var_sharpe_trials) * ((1 - gamma) * stats.norm.ppf(1 - 1/n_trials) + gamma * stats.norm.ppf(1 - 1/(n_trials * np.e)))
    
    # Variance asymptotique du Sharpe sous asymétrie et kurtosis
    sigma_sr = np.sqrt((1 + 0.5 * estimated_sharpe**2 - skew * estimated_sharpe + ((kurt)/4) * estimated_sharpe**2) / sample_length_t)
    
    dsr_stat = (estimated_sharpe - exp_max_sharpe) / sigma_sr
    dsr_prob = stats.norm.cdf(dsr_stat)
    return dsr_prob # Doit être > 0.95 pour être statistiquement significatif

# Si DSR < 0.95, la stratégie est du pur bruit statistique overfitté !
```

---

## 💣 5. La Cross-Validation Temporelle Non Purgée

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Si une position est tenue pendant 5 jours (labels qui se chevauchent),
# un split K-Fold classique fait fuiter le futur immédiat du train dans le validation fold.
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Purged & Embargoed Cross-Validation
# On élimine (purge) toutes les observations du train dont la fenêtre de détention chevauche le test,
# et on ajoute un embargo (ex: 5 jours) après le test pour éliminer l'autocorrélation résiduelle.
```

---

## 💣 6. Le Monde Sans Friction (Spread, Slippage & Borrow)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Backtester une stratégie qui fait 20 allers-retours par jour sans frais
pnl = position * returns # <-- Rendement brut irréaliste
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Modéliser le coût de transaction à chaque changement de position
trades = position.diff().abs() # Volume tradé
half_spread = 0.0005 # 5 bps de demi-spread
slippage = 0.0003    # 3 bps de slippage estimé
borrow_fee = 0.02 / 252 # 2% annuel pour les positions courtes

transaction_costs = trades * (half_spread + slippage)
borrow_costs = np.where(position < 0, abs(position) * borrow_fee, 0.0)

net_returns = (position * returns) - transaction_costs - borrow_costs
```

---

## 💣 7. L'Inversion de Covariance Explosive (Markowitz Mal Conditionné)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Inverser directement la matrice de covariance empirique sur 50 actifs avec 100 jours de données
cov = df_returns.cov().values
inv_cov = np.linalg.inv(cov) # Condition number kappa > 10^4 -> Poids aberrants (+800% / -750%)
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Shrinkage de Ledoit-Wolf ou Hierarchical Risk Parity (HRP)
from sklearn.covariance import LedoitWolf

lw = LedoitWolf()
shrunk_cov = lw.fit(df_returns).covariance_

kappa = np.linalg.cond(shrunk_cov)
print(f"Condition Number Ledoit-Wolf : {kappa:.2f} (Bien conditionné si < 100)")
```

---

## 💣 8. La Confusion Causalité vs Corrélation (Granger vs Vraie Causalité)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Utiliser le test de causalité de Granger pour affirmer qu'une variable X
# "cause" économiquement une variable Y lors d'une intervention ou décision politique.
from statsmodels.tsa.stattools import grangercausalitytests
grangercausalitytests(df[['y', 'x']], maxlag=3) # Ne mesure que la précédence temporelle prédictive !
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Pour évaluer l'impact causal d'un événement / politique,
# utiliser un design quasi-expérimental : Difference-in-Differences (DiD) avec Two-Way Fixed Effects (TWFE)
# ou un Contrôle Synthétique (voir references/causal_inference_and_econometrics.md)
import statsmodels.formula.api as smf

df['did_interaction'] = df['treated_group'] * df['post_event']
did_model = smf.ols("outcome ~ did_interaction + C(entity_id) + C(time_period)", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["entity_id"]}
)
print(f"Effet causal net : {did_model.params['did_interaction']:.4f} (p-val: {did_model.pvalues['did_interaction']:.4f})")
```
