# Plan: OpenTimestamps — Prouver l'antériorité des idées EgoVault

**Date:** 2026-04-16
**Objectif:** Chaque milestone majeur (v0.X.0) est timestampé dans la blockchain Bitcoin.

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

Si un changement mérite un timestamp, il mérite d'être un v0.X.0.
Si c'est juste une feature ou un fix, c'est un commit normal sans timestamp.

---

## Step 1 — Installer le client OTS

**Do:**
```bash
pip install opentimestamps-client
ots --version
```
**Test:** `echo "test" | ots stamp /dev/stdin && echo "OK"`

---

## Step 2 — Créer le script de timestamping

**Fichier:** `scripts/timestamp-release.sh`

```bash
#!/bin/bash
# scripts/timestamp-release.sh — timestamp a version tag
# Usage: bash scripts/timestamp-release.sh v0.3.0

set -e
command -v ots >/dev/null 2>&1 || { echo "ERROR: ots not installed (pip install opentimestamps-client)"; exit 1; }

TAG="${1:?Usage: $0 <tag>}"

# Verify tag exists
git rev-parse "$TAG" >/dev/null 2>&1 || { echo "ERROR: tag $TAG does not exist"; exit 1; }

# Only allow v0.X.0 tags
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.0$ ]] || { echo "ERROR: only v0.X.0 tags are timestamped"; exit 1; }

TIMESTAMP_DIR=".timestamps"
mkdir -p "$TIMESTAMP_DIR"

COMMIT_HASH=$(git rev-parse "$TAG")
OTS_FILE="$TIMESTAMP_DIR/$TAG.ots"

[ -f "$OTS_FILE" ] && { echo "$TAG already timestamped"; exit 0; }

echo -n "$COMMIT_HASH" | ots stamp /dev/stdin -O "$OTS_FILE"
echo "[OTS] Timestamped $TAG ($COMMIT_HASH) → $OTS_FILE"
echo ""
echo "Next steps:"
echo "  1. git add $OTS_FILE && git commit -m 'chore: add OTS proof for $TAG'"
echo "  2. Wait 1-2 hours for Bitcoin confirmation"
echo "  3. Verify: ots verify $OTS_FILE"
```

`chmod +x scripts/timestamp-release.sh`

---

## Step 3 — Créer les tags rétroactifs et timestamper

**Do:**
```bash
# Tag the key milestones
git tag -a v0.1.0 <commit-hash-architecture> -m "Hexagonal architecture, 3 ingest workflows, MCP server"
git tag -a v0.2.0 <commit-hash-vaultcontext> -m "VaultContext refactoring, unified ingest, G4 compliant"
git tag -a v0.3.0 HEAD -m "Knowledge compiler vision, librarian agent pattern, context engineering"

# Timestamp each
bash scripts/timestamp-release.sh v0.1.0
bash scripts/timestamp-release.sh v0.2.0
bash scripts/timestamp-release.sh v0.3.0

# Commit the proofs
git add .timestamps/ && git commit -m "chore: add OTS proofs for v0.1.0, v0.2.0, v0.3.0"
```

---

## Step 4 — Documentation

**Fichier:** `docs/TIMESTAMPS.md`

```markdown
# Timestamp verification

Major releases (v0.X.0) of this repository are timestamped in the Bitcoin
blockchain via OpenTimestamps.

## Verify a release
bash scripts/timestamp-release.sh v0.3.0   # create (if not done)
ots verify .timestamps/v0.3.0.ots           # verify

## What this proves
The SHA256 hash of the git commit tagged v0.X.0 was registered in the
Bitcoin blockchain. This proves the entire repository state at that
version existed at the indicated date.

## Timestamped releases
| Tag | Description |
|-----|-------------|
| v0.1.0 | Hexagonal architecture, 3 ingest workflows, MCP server |
| v0.2.0 | VaultContext, unified ingest, G4 compliant |
| v0.3.0 | Knowledge compiler vision, librarian agent pattern |
```

---

## Step 5 — Intégrer dans le workflow Phase 7 (SHIP)

Ajouter dans `docs/superpowers/specs/2026-03-31-development-workflow.md` Phase 7 :

> If this milestone warrants a new v0.X.0 tag:
> `git tag -a v0.X.0 -m "description" && bash scripts/timestamp-release.sh v0.X.0`

---

## Résumé

| Step | Quoi | Temps |
|------|------|-------|
| 1 | Installer ots | 1 min |
| 2 | Script timestamp-release.sh | 3 min |
| 3 | Tags rétroactifs + timestamps | 3 min |
| 4 | Documentation | 3 min |
| 5 | Intégrer dans workflow SHIP | 1 min |
| **Total** | | **~11 min** |

Après ça : quand un milestone v0.X.0 est atteint, une commande suffit pour le prouver dans la blockchain.
