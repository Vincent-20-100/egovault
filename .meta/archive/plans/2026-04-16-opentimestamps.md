# Plan: OpenTimestamps — Prouver l'antériorité des idées EgoVault

**Date:** 2026-04-16 (updated 2026-04-24)
**Objectif:** Chaque milestone majeur (v0.X.0) est timestampé dans la blockchain Bitcoin.
**Status:** Script réécrit en Python pur (v2). Tags créés, en attente de stamp.

---

## Contexte

OpenTimestamps (OTS) enregistre un hash SHA256 dans la blockchain Bitcoin via un arbre
de Merkle. Gratuit, open source, sans tiers de confiance.

- Stamp initial : ~1 seconde (serveur calendrier)
- Confirmation blockchain : 1-2 heures (agrégation en batch)
- Coût : 0

## Règle de timestamping

**Seuls les tags v0.X.0 sont timestampés. Pas de v0.X.Y, pas de commits individuels.**

Un tag git pointe vers un commit. Le commit EST un hash de tout le repo (fichiers, message,
parenté, auteur, date). Timestamper le tag = prouver l'état complet du repo à cette date.

---

## Step 1 — Script de timestamping (Python pur)

**Fichier:** `scripts/timestamp-release.py`

Python pur, zéro dépendance externe. Appelle directement l'API HTTP des serveurs
calendrier OTS. Fonctionne sur Windows, Mac, Linux.

```bash
python scripts/timestamp-release.py v0.3.0
```

V1 (bash + `ots` CLI) abandonnée : `opentimestamps-client` incompatible Python 3.13/Windows.

---

## Step 2 — Créer les tags et timestamper

```bash
# Tags déjà créés (v0.1.0→6f31f28, v0.2.0→9817b51, v0.3.0→0a5aa9c)
# Timestamp each
python scripts/timestamp-release.py v0.1.0
python scripts/timestamp-release.py v0.2.0
python scripts/timestamp-release.py v0.3.0

# Commit the proofs
git add .timestamps/ && git commit -m "chore: add OTS proofs for v0.1.0, v0.2.0, v0.3.0"
git push origin --tags
```

---

## Step 3 — Vérification

Upload `.ots` + `.hash` sur https://opentimestamps.org/ (après 1-2h pour confirmation Bitcoin).

---

## Workflow futur (Phase 7 — SHIP)

Quand un milestone v0.X.0 est atteint :
```bash
git tag -a v0.X.0 -m "description"
python scripts/timestamp-release.py v0.X.0
git add .timestamps/ && git commit -m "chore: add OTS proof for v0.X.0"
git push origin --tags
```
