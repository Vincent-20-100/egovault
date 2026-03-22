# EgoVault

## C'est quoi EgoVault ?

Tu consommes des infos en permanence — podcasts, vidéos, lectures, réflexions. Deux semaines plus tard, t'en rappelles plus grand-chose. Et tes LLMs ? Ils ne savent rien de toi. Chaque conversation repart de zéro.

EgoVault construit le pont entre les deux : une base de connaissance personnelle que tu alimentes au fil du temps, structurée pour être exploitable autant par toi que par un LLM.

**Ce que ça change concrètement :**

- **Capturer sans friction** — une commande suffit pour transformer une vidéo YouTube, un podcast ou un enregistrement audio en source prête à traiter. Transcription locale, rien n'est envoyé ailleurs.
- **Structurer ses idées avec le LLM** — plutôt que de prendre des notes à la volée, tu travailles avec Claude pour reformuler, distiller et cadrer chaque source en une note propre, bien ancrée dans ta façon de penser.
- **Réutiliser comme contexte LLM** — tes notes deviennent du contexte réutilisable. Au lieu de tout réexpliquer à chaque session, tu fournis des notes existantes : le LLM travaille *avec ta connaissance accumulée*, pas avec sa culture générale.
- **Fouiller dans sa propre pensée** — tu peux demander au LLM de croiser des notes de sources différentes, détecter des patterns, proposer des connexions que tu n'aurais pas vues.
- **Interconnexion par tags et liens** — chaque note est taguée et liée aux autres. Des clusters thématiques émergent naturellement de l'accumulation, sans taxonomie imposée au départ.

**Ce qui est en place :**
Ingestion YouTube / audio / vidéo, structuration en notes Markdown, index automatique des tags, queue d'ingestion, protocole Claude complet pour créer et explorer les notes.

**Ce qui manque encore :**
Handler PDF et web, recherche sémantique (RAG) sur le vault.

**La vision :**
Pouvoir synthétiser, stocker et explorer sa connaissance de la façon la plus fluide possible — recherche sémantique RAG, exploration en graphe 3D par thèmes et groupes, similarité sémantique entre notes, émergence naturelle de clusters, propositions de thèmes transversaux depuis l'accumulation. Le vault connecté à n'importe quel LLM via MCP — LLM-agnostique par design, tu branches le LLM que tu utilises déjà et il travaille depuis *ce que tu sais*, pas depuis ce qu'il sait.

---

Deux repos distincts :
- **egovault** (ce repo) — code, scripts, protocole Claude
- **egovault-data** — données personnelles (notes, sources) — repo privé par utilisateur

## Prérequis

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) — gestionnaire de paquets Python
- ffmpeg dans le PATH (requis pour audio et vidéo)

## Installation

```bash
# 1. Cloner l'app
git clone <repo>
cd egovault

# Linux/macOS
bash setup.sh

# Windows (PowerShell)
.\setup.ps1
```

Le script installe uv si nécessaire, crée le venv, installe les dépendances et copie `config.yaml.example` → `config.yaml`.

```bash
# 2. Pointer l'app vers votre vault data
# Éditer config.yaml :
# vault:
#   data_path: "../egovault-data"   ← chemin vers votre dossier vault

# 3. Initialiser la structure du vault (crée le dossier, git, .obsidian, etc.)
uv run python scripts/init_vault.py

# 4. Vérifier
uv run python scripts/vault_status.py
```

## Usage

```bash
# Ingestion directe
uv run python capture.py "https://youtube.com/watch?v=..."
uv run python capture.py video.mp4 --title "Titre" --lang fr
uv run python capture.py enregistrement.mp3 --title "Titre" --lang fr --fast

# Queue d'ingestion
uv run python capture.py queue add "https://youtube.com/watch?v=..."
uv run python capture.py queue add video.mp4 --title "Titre"
uv run python capture.py queue run
uv run python capture.py queue status

# Maintenance vault
uv run python scripts/vault_status.py       # état des drop-offs
uv run python scripts/update_index.py       # reconstruire _index.md
uv run python scripts/check_consistency.py  # audit qualité

# Tests
uv run pytest
```

## Structure

```
egovault/
├── capture.py              ← point d'entrée ingestion
├── config.yaml             ← paramètres locaux (gitignored)
├── config.yaml.example     ← template
├── pyproject.toml          ← dépendances (uv)
├── setup.sh / setup.ps1    ← installation
├── FOUNDATION.md           ← philosophie et axiomes du projet
├── DOCUMENTATION.md        ← architecture et décisions techniques
├── AMELIORATIONS.md        ← backlog et roadmap
├── LLM.md                  ← protocole Claude (workflows, conventions)
├── scripts/
│   ├── _config.py          ← lecture config.yaml
│   ├── queue.py            ← gestion queue d'ingestion
│   ├── ingest/
│   │   ├── _core.py        ← utilitaires partagés + constantes
│   │   ├── youtube.py      ← handler YouTube
│   │   ├── audio.py        ← handler audio (mp3, wav, m4a...)
│   │   └── video.py        ← handler vidéo (mp4, mkv...)
│   ├── vault_status.py
│   ├── update_index.py
│   ├── check_consistency.py
│   └── clean_sources.py
└── tests/

egovault-data/             ← repo privé (non inclus)
├── .obsidian/              ← config Obsidian
├── notes/                  ← toutes les notes
└── sources/                ← sources permanentes + raw-sources/
```

## Format des notes

```yaml
---
date_creation: YYYY-MM-DD
date_modification: YYYY-MM-DD
note_type: synthese        # idee | synthese | reflexion | concept
source_type: youtube       # youtube | audio | video | pdf | web | livre | cours | personnel
depth: note                # atomique | note | approfondi
tags: [theme-large, sous-theme]
source: "[[sources/slug/source.md]]"  # optionnel
url: "https://..."                     # optionnel
---
```

## Claude Code

Ce repo inclut une configuration `.claude/settings.json` avec les permissions recommandées. Pour utiliser Claude Code avec ce projet :

```bash
claude  # dans le répertoire du projet
```

Les protocoles LLM (workflows A/B/C, conventions de nommage, gestion des sessions) sont dans `LLM.md`.

Voir `FOUNDATION.md` pour la philosophie du projet et `DOCUMENTATION.md` pour les décisions architecturales.
