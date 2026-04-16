# Plan: OpenTimestamps — Prouver l'antériorité des idées EgoVault

**Date:** 2026-04-16
**Spec:** Aucune spec formelle nécessaire — c'est de l'outillage, pas une feature produit.
**Objectif:** Chaque commit important est timestampé dans la blockchain Bitcoin.

---

## Contexte

OpenTimestamps (OTS) enregistre le hash SHA256 d'un fichier dans la blockchain Bitcoin
via un arbre de Merkle. Gratuit, open source, sans tiers de confiance. Preuve vérifiable
par n'importe qui, pour toujours.

- Stamp initial : ~1 seconde (serveur calendrier)
- Confirmation blockchain : 1-2 heures (agrégation en batch)
- Coût : 0 (fractions de satoshi amorties sur ~10k hashes par transaction)

---

## Step 1 — Installer le client OTS

**Fichiers:** aucun fichier projet modifié
**Do:**
```bash
pip install opentimestamps-client
ots --version  # vérifier
```
**Test:** `echo "test" > /tmp/test.txt && ots stamp /tmp/test.txt && ls /tmp/test.txt.ots`

---

## Step 2 — Timestamper les documents clés existants

**Fichiers:** génère des `.ots` à côté des fichiers source
**Do:**
```bash
# Documents fondateurs
ots stamp docs/FUTURE-WORK.md
ots stamp docs/VISION.md
ots stamp CLAUDE.md
ots stamp docs/architecture/ARCHITECTURE.md

# Specs clés
ots stamp .meta/specs/2026-03-31-unified-ingest-architecture.md
ots stamp .meta/specs/2026-03-31-development-workflow.md
```
**Test:** `ots info docs/FUTURE-WORK.md.ots` — doit montrer le hash et le calendrier

---

## Step 3 — Décider du stockage des .ots

**Option A (recommandée) : committer les .ots dans le repo**
- Avantage : la preuve voyage avec le code, n'importe qui peut vérifier
- Inconvénient : fichiers binaires dans git

**Option B : dossier séparé**
```
.timestamps/
├── FUTURE-WORK.md.ots
├── VISION.md.ots
└── ...
```

**Do:** Créer `.timestamps/` dans le repo, y stocker tous les .ots.
Ajouter une entrée dans CLAUDE.md §3 (structure) pour le documenter.

**Commit message:** `chore: add OpenTimestamps proofs for key documents`

---

## Step 4 — Automatiser via hook post-commit

**Fichiers:** `.git/hooks/post-commit` (ou settings.json Claude Code hook)
**Do:**

Créer le script de timestamping :

```bash
#!/bin/bash
# scripts/timestamp.sh — timestamp key files after each commit
# Only stamps if ots is installed and files changed in this commit

command -v ots >/dev/null 2>&1 || exit 0

TIMESTAMP_DIR=".timestamps"
mkdir -p "$TIMESTAMP_DIR"

# Files to timestamp (key documents only — not every file)
KEY_FILES=(
    "docs/FUTURE-WORK.md"
    "docs/VISION.md"
    "CLAUDE.md"
    "docs/architecture/ARCHITECTURE.md"
    "SESSION-CONTEXT.md"
    "PROJECT-STATUS.md"
)

CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)

for file in "${KEY_FILES[@]}"; do
    if echo "$CHANGED_FILES" | grep -q "^${file}$"; then
        ots stamp "$file" -O "$TIMESTAMP_DIR/$(basename $file).ots" 2>/dev/null
        echo "[OTS] Timestamped: $file"
    fi
done
```

Rendre exécutable : `chmod +x scripts/timestamp.sh`

**Intégration :** Deux options :
- Git hook : `.git/hooks/post-commit` qui appelle `scripts/timestamp.sh`
- Claude Code hook : PostPush event dans settings.json

**Test:** Modifier FUTURE-WORK.md, committer, vérifier que `.timestamps/FUTURE-WORK.md.ots` existe.

---

## Step 5 — Vérification et documentation

**Fichiers:** `docs/TIMESTAMPS.md` (nouveau)
**Do:**

Créer un petit guide de vérification :

```markdown
# Vérification des timestamps

## Vérifier un fichier
ots verify .timestamps/FUTURE-WORK.md.ots docs/FUTURE-WORK.md

## Inspecter un timestamp
ots info .timestamps/FUTURE-WORK.md.ots

## Ce que ça prouve
Le hash SHA256 du fichier a été enregistré dans la blockchain Bitcoin
à la date indiquée. Cela prouve que le contenu existait à cette date.
```

**Commit message:** `docs: add timestamp verification guide`

---

## Step 6 — Timestamper le commit actuel rétroactivement

**Do:**
```bash
# Timestamper le hash du commit qui contient la vision Knowledge Compiler
COMMIT_HASH=$(git log --oneline --all --grep="knowledge compiler" | head -1 | cut -d' ' -f1)
echo "$COMMIT_HASH" | ots stamp /dev/stdin -O .timestamps/knowledge-compiler-commit.ots
```

**Test:** `ots info .timestamps/knowledge-compiler-commit.ots`

---

## Résumé

| Step | Quoi | Temps estimé |
|------|------|-------------|
| 1 | Installer ots | 1 min |
| 2 | Timestamper les docs existants | 2 min |
| 3 | Créer .timestamps/ et committer | 2 min |
| 4 | Script d'automatisation | 5 min |
| 5 | Guide de vérification | 3 min |
| 6 | Timestamp rétroactif du commit vision | 1 min |
| **Total** | | **~15 min** |

Après ça, chaque commit qui touche un document clé est automatiquement timestampé.
