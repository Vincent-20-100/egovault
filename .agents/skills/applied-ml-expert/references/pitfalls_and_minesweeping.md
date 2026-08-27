# Tactical ML Pitfalls & Senior Minesweeping Guide (`pitfalls_and_minesweeping.md`)

> **Field Motto**: *« A bug in data science rarely crashes with a traceback—it quietly yields an illusory 0.99 score on validation that completely collapses in real-world deployment. »*

---

## 🧭 The 9 Classic Pitfalls vs Senior Demining Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    TACTICAL DATA SCIENCE & ML MINESWEEPING MATRIX                               │
├────────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│ 1. FIT AVANT SPLIT (LEAKAGE)   │ 2. TARGET ENCODING NAÏF        │ 3. GROUP LEAKAGE (USERS/ENT)  │
│ ⚠️ Fit scaler/imputer sur tout │ ⚠️ Moyenne globale de la cible │ ⚠️ Découpage aléatoire d'un   │
│ 🛡️ Pipeline & Split AVANT fit  │ 🛡️ Out-of-Fold (OOF) TargetEnc │    même utilisateur dans train│
├────────────────────────────────┼────────────────────────────────┼───────────────────────────────┤
│ 4. TEMPORAL LOOKAHEAD LEAK     │ 5. L'ILLUSION DU 98% ACCURACY  │ 6. SEUIL 0.5 AVEUGLE          │
│ ⚠️ Random split sur séries     │ ⚠️ 98% classe 0 sur déséquilibre│ ⚠️ Ignorer les coûts FP vs FN│
│ 🛡️ TimeSeriesSplit chronologique│ 🛡️ PR-AUC & Brier score       │ 🛡️ Seuil optimisé sur matrice│
├────────────────────────────────┼────────────────────────────────┼───────────────────────────────┤
│ 7. ID / UUID DANS LES ARBRES   │ 8. SEED FISHING & SUR-TUNING   │ 9. INTERPRÉTATION FANTÔME     │
│ ⚠️ Mémorisation des clés prim. │ ⚠️ 500 itérations sur N < 500  │ ⚠️ Conclure avant l'output    │
│ 🛡️ Drop automatique des IDs    │ 🛡️ RepeatedCV & Règle des 2%   │ 🛡️ Fait observé ➔ Conclusion  │
└────────────────────────────────┴────────────────────────────────┴───────────────────────────────┘
```

---

## 💣 1. Fuite de Données Classique (Fit avant Split)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR FATALE : Le scaler et l'imputer apprennent la moyenne et la variance du TEST set !
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X) # <-- Fuite globale !
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2)
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Le split s'effectue TOUJOURS avant tout calcul de moyenne/variance
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# Ou idéalement via un Pipeline scikit-learn (étanche pendant la Cross-Validation) :
pipeline = make_pipeline(
    SimpleImputer(strategy="median"),
    StandardScaler(),
    LogisticRegression()
)
pipeline.fit(X_train, y_train)
```

---

## 💣 2. Target Encoding Naïf (Fuite de Cible Catastrophique)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR FATALE : Calculer la moyenne de la cible directement sur la colonne !
# Si une catégorie n'a qu'une seule ligne, la feature devient égale à la cible exacte !
category_means = df.groupby('city')['target'].mean()
df['city_encoded'] = df['city'].map(category_means) # <-- Target Leakage absolu
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Utiliser le TargetEncoder scikit-learn avec Out-of-Fold (OOF) et lissage (smoothing)
from sklearn.preprocessing import TargetEncoder

# Le TargetEncoder de sklearn découpe en sous-folds internes pour ne jamais encoder
# une ligne avec sa propre valeur de cible.
target_encoder = TargetEncoder(cv=5, smooth="auto", random_state=42)

pipeline = make_pipeline(
    target_encoder,
    LogisticRegression()
)
pipeline.fit(X_train, y_train)
```

---

## 💣 3. Group Leakage (Mémorisation de l'Entité / Utilisateur)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Si un client a 10 transactions, un split aléatoire met 8 transactions dans le train
# et 2 dans le test. Le modèle apprend l'ID ou le comportement spécifique du client, pas le signal général.
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : GroupKFold ou GroupShuffleSplit pour garantir qu'un utilisateur
# est SOIT à 100% dans le train, SOIT à 100% dans le test/val.
from sklearn.model_selection import GroupShuffleSplit

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=df["user_id"]))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
```

---

## 💣 4. Temporal Lookahead Leak (Voyage dans le Temps)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Découper aléatoirement une série temporelle (on utilise le futur pour prédire le passé)
# ou calculer une moyenne mobile centrée incluant t+1, t+2.
df['future_avg'] = df['price'].rolling(window=5, center=True).mean() # <-- Voyage dans le temps
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Découpage chronologique strict + TimeSeriesSplit
from sklearn.model_selection import TimeSeriesSplit

# 1. Tri chronologique obligatoire
df = df.sort_values("timestamp")

# 2. Features uniquement basées sur le passé
df['past_avg'] = df['price'].shift(1).rolling(window=5).mean()

# 3. Validation par fenêtres glissantes ou expansives
tscv = TimeSeriesSplit(n_splits=5)
```

---

## 💣 5. L'Illusion du 98% Accuracy sur Données Déséquilibrées

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Sur un dataset de fraude à 99% non-fraude (0) et 1% fraude (1)
score = accuracy_score(y_true, y_pred)
# Affiche 0.9900 alors que le modèle n'a détecté AUCUNE fraude !
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : PR-AUC (Average Precision), F-beta, Score de Brier et Matrice de Confusion
from sklearn.metrics import average_precision_score, classification_report, brier_score_loss

pr_auc = average_precision_score(y_test, y_pred_proba)
brier = brier_score_loss(y_test, y_pred_proba)

print(f"PR-AUC (Focus minoritaire) : {pr_auc:.4f}")
print(f"Brier Score (Calibration)  : {brier:.4f}")
print(classification_report(y_test, (y_pred_proba >= 0.5).astype(int)))
```

---

## 💣 6. Le Seuil 0.5 Aveugle (Ignorer les Coûts Métier FP vs FN)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Prendre le seuil par défaut à 0.5 alors qu'un Faux Négatif (fraude manquée)
# coûte 500 € et qu'un Faux Positif (alerte manuelle) ne coûte que 10 €.
preds = model.predict(X_test) # <-- Applique bêtement 0.5
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Optimiser le seuil sur les probabilités prédites selon la matrice de coût
import numpy as np

probs = model.predict_proba(X_val)[:, 1]
thresholds = np.linspace(0.01, 0.99, 100)

cost_fn = 500.0  # Coût d'un Faux Négatif
cost_fp = 10.0   # Coût d'un Faux Positif

best_threshold = 0.5
min_total_cost = float("inf")

for t in thresholds:
    preds_t = (probs >= t).astype(int)
    fp = np.sum((preds_t == 1) & (y_val == 0))
    fn = np.sum((preds_t == 0) & (y_val == 1))
    total_cost = (fp * cost_fp) + (fn * cost_fn)
    
    if total_cost < min_total_cost:
        min_total_cost = total_cost
        best_threshold = t

print(f"🎯 Seuil métier optimal : {best_threshold:.2f} (Coût total : {min_total_cost:,.0f} €)")
```

---

## 💣 7. Injecter des ID / UUID dans les Arbres de Décision

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Laisser 'customer_id', 'transaction_uuid' ou des timestamps bruts dans X
lgb_model.fit(X_with_ids, y) # <-- L'arbre mémorise les IDs individuels (overfitting parfait)
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Bannir et supprimer toutes les colonnes à cardinalité 100% ou d'identification
id_cols = [c for c in X.columns if X[c].nunique() == len(X) or "id" in c.lower() or "uuid" in c.lower()]
X_clean = X.drop(columns=id_cols, errors="ignore")
```

---

## 💣 8. Le "Seed Fishing" & Sur-Tuning sur Petit Échantillon ($N < 500$)

### ⚠️ Le Piège (Vibe-Coder)
```python
# ❌ ERREUR : Lancer 1000 essais Optuna sur 200 lignes pour trouver un "bon" score
# ou changer le random_state jusqu'à ce que le score monte à 0.88.
```

### 🛡️ Le Déminage Senior
```python
# ✅ SOLUTION : Validation croisée répétée + Régularisation forte (L2 / Ridge) + Baseline
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression

# Sur N < 500, préférer un modèle simple avec forte régularisation (C petit)
model = LogisticRegression(C=0.1, penalty="l2", class_weight="balanced")
rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42)

scores = cross_val_score(model, X, y, cv=rskf, scoring="average_precision")
print(f"Score robuste 5x5 CV : {scores.mean():.4f} (± {scores.std():.4f})")
# 📏 RÈGLE DES 2% : Si XGBoost ne fait que 0.01 de plus avec une variance 3x plus forte, garder LogReg !
```

---

## 💣 9. L'Interprétation Fantôme dans les Notebooks

### ⚠️ Le Piège (Vibe-Coder)
Écrire dans le markdown :
> *"Comme on peut le constater ci-dessous, la variable revenu est le principal prédicteur avec une relation strictement linéaire."*  
*(Alors que le code n'a pas encore tourné ou que le graphique montre une relation en cloche !)*

### 🛡️ Le Déminage Senior (La Règle Séquentielle Inviolable)
1. **Étape 1 (Markdown)** : Poser la question ou l'hypothèse (*« Question : Quelle est la distribution des erreurs selon l'âge ? »*).
2. **Étape 2 (Code)** : Exécuter la cellule et afficher la sortie/graphique.
3. **Étape 3 (Markdown ou print)** : Constater **strictement** ce que montre l'output réel (*« Constat : 70% des faux négatifs sont concentrés sur la tranche 18-25 ans. »*).
4. **Étape 4** : Décider de l'action corrective (*« Action : Ajuster le sous-échantillonnage de cette tranche. »*).
