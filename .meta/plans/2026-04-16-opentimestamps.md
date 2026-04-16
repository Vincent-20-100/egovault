# Plan: OpenTimestamps — Prouver l'antériorité des idées EgoVault

**Date:** 2026-04-16
**Spec:** Aucune spec formelle nécessaire — c'est de l'outillage, pas une feature produit.
**Objectif:** Chaque commit est timestampé dans la blockchain Bitcoin.

---

## Contexte

OpenTimestamps (OTS) enregistre un hash SHA256 dans la blockchain Bitcoin via un arbre
de Merkle. Gratuit, open source, sans tiers de confiance.

- Stamp initial : ~1 seconde (serveur calendrier)
- Confirmation blockchain : 1-2 heures (agrégation en batch)
- Coût : 0

**Approche : timestamper le hash du commit git, pas les fichiers individuels.**
Un commit git EST un hash de tout son contenu (fichiers, message, parenté, auteur, date).
Timestamper 1 hash de commit = prouver l'état complet du repo à cette date.

---

## Step 1 — Installer le client OTS

**Do:**
```bash
pip install opentimestamps-client
ots --version
```
**Test:** `echo "test" | ots stamp /dev/stdin && echo "OK"`

---

## Step 2 — Créer le dossier et le script

**Fichiers:** `.timestamps/` (dossier), `scripts/timestamp-commit.sh`
**Do:**

```bash
#!/bin/bash
# scripts/timestamp-commit.sh — timestamp the latest commit hash
# Called by post-commit hook or manually

command -v ots >/dev/null 2>&1 || { echo "[OTS] ots not installed, skipping"; exit 0; }

TIMESTAMP_DIR=".timestamps"
mkdir -p "$TIMESTAMP_DIR"

COMMIT_HASH=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)
OTS_FILE="$TIMESTAMP_DIR/$COMMIT_HASH.ots"

# Don't re-stamp if already timestamped
[ -f "$OTS_FILE" ] && exit 0

echo -n "$COMMIT_HASH" | ots stamp /dev/stdin -O "$OTS_FILE" 2>/dev/null
echo "[OTS] Timestamped commit $SHORT_HASH → $OTS_FILE"
```

**Test:** `bash scripts/timestamp-commit.sh && ls .timestamps/`

---

## Step 3 — Automatiser via post-commit hook

**Fichiers:** `.git/hooks/post-commit`
**Do:**

```bash
#!/bin/bash
# Auto-timestamp every commit
bash scripts/timestamp-commit.sh
```

`chmod +x .git/hooks/post-commit scripts/timestamp-commit.sh`

**Alternative Claude Code:** Ajouter dans settings.json un PostCommit hook.

---

## Step 4 — Timestamper les commits historiques clés

**Do:**
```bash
# Tous les commits de main (rétroactif)
for hash in $(git log --format=%H main); do
    echo -n "$hash" | ots stamp /dev/stdin -O ".timestamps/$hash.ots" 2>/dev/null
    echo "[OTS] Stamped $hash"
done
```

Ou sélectivement — seulement les commits importants (vision, architecture, etc.).

**Commit:** `chore: add OTS proofs for historical commits`

---

## Step 5 — Vérification et documentation

**Fichier:** `docs/TIMESTAMPS.md`

```markdown
# Timestamp verification

Every commit in this repository is timestamped in the Bitcoin blockchain
via OpenTimestamps.

## Verify a commit
COMMIT_HASH=$(git rev-parse HEAD)
ots verify .timestamps/$COMMIT_HASH.ots

## What this proves
The SHA256 hash of the git commit was registered in the Bitcoin blockchain
at the indicated date. This proves the entire repository state (all files,
all history up to that point) existed at that date.

## How it works
- Post-commit hook runs `scripts/timestamp-commit.sh`
- Generates `.timestamps/<commit-hash>.ots` proof file
- Proof is confirmed on-chain within 1-2 hours
- Verification works offline with a Bitcoin node, or online via calendar servers
```

---

## Step 6 — .gitignore update

Les `.ots` sont commités (la preuve doit voyager avec le repo).
Vérifier que `.timestamps/` n'est PAS dans `.gitignore`.

---

## Résumé

| Step | Quoi | Temps |
|------|------|-------|
| 1 | Installer ots | 1 min |
| 2 | Script de timestamping | 3 min |
| 3 | Hook post-commit | 2 min |
| 4 | Timestamps rétroactifs | 2 min |
| 5 | Documentation | 3 min |
| 6 | Gitignore check | 1 min |
| **Total** | | **~12 min** |

Après ça, chaque commit est automatiquement et gratuitement prouvé dans la blockchain.
