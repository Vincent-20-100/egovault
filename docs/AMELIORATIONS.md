# Améliorations du vault — Architecture et chantiers

_Document de travail — pas une note PKM, pas soumis aux conventions de nommage du vault_
_Dernière mise à jour : 2026-03-22_

---

## TODO — À faire maintenant (validé, prioritaire)

### [x] T1. Finir les corrections d'audit Python/Sécurité

Corrections restantes à appliquer (session 2026-03-22 interrompue) :

| Fichier | Fix |
|---|---|
| `scripts/ingest/youtube.py` | Ajouter `print(warning)` dans `except Exception` de `get_metadata` |
| `capture.py` | Importer `YOUTUBE_PATTERN`, `AUDIO_EXTENSIONS`, `VIDEO_EXTENSIONS` depuis `_core.py` au lieu de les redéfinir |
| `scripts/queue.py` | Même import centralisé depuis `_core.py` + type hint `list[str]` sur `handle_queue_command` |
| `scripts/clean_sources.py` | Déplacer `import shutil` en tête de fichier |
| `scripts/_config.py` | Gérer le cas `vault: null` dans config.yaml (évite AttributeError cryptique) |

Déjà fait :
- [x] `_core.py` : `get_vault_path()`, assertion path traversal, `yaml.dump`, `set_status` validation, `find_duplicate` ancrée
- [x] `audio.py` : suppression `import re` + `build_folder_name` (code mort)
- [x] `video.py` : `timeout=3600` sur `subprocess.run`

---

### [x] T2. Migration — supprimer la date des noms de fichiers existants

**Décision validée** : `titre-kebab-case.md` au lieu de `YYYY-MM-DD-titre-kebab-case.md`
La date est metadata → frontmatter `date_creation:` uniquement.

Script de migration à créer : `scripts/migrate_rename.py`
- Renomme tous les fichiers `notes/` et `sources/` (supprimer le préfixe `YYYY-MM-DD-`)
- En cas de doublon de slug → ajouter suffixe `-2`, `-3`
- Met à jour tous les wikilinks `[[YYYY-MM-DD-slug]]` → `[[slug]]` dans les notes
- Met à jour les champs `note_creee:` dans les `source.md` concernés
- Dry-run par défaut, `--apply` pour exécuter

Après migration :
- Mettre à jour la convention dans `LLM.md`
- Mettre à jour `_core.py` (`make_drop_off` — slug sans date en préfixe)
- Mettre à jour `update_index.py` si patterns date-dépendants

---

### [x] T3. Numérotation automatique + script de résolution de doublons

**Deux mécanismes distincts :**

**Mécanisme 1 — Auto-numérotation à la création** (dans `_core.py` / `make_drop_off`) :
- Si `titre.md` existe déjà → créer `titre-2.md` automatiquement, sans intervention humaine
- Transparent pour l'utilisateur, aucune friction à la capture

**Mécanisme 2 — Script de résolution** (`scripts/check_duplicates.py`) :
- Détecte les notes déjà numérotées (`titre.md` + `titre-2.md`) ou très proches en slug
- Compare tags + docstring pour évaluer si c'est le même sujet ou un angle différent
- Propose pour chaque paire : **renommage plus précis** (deux sujets distincts) ou **fusion** (même sujet, angles complémentaires)
- Output interactif — l'humain décide toujours

Prérequis de T2 (dates supprimées d'abord pour que les slugs soient comparables).

---

### [x] T4. Système de notes-concept (clustering émergent)

**Problème** : les tags seuls créent un graphe plat — pas de hubs intermédiaires entre les notes atomiques et le vault entier. Des thèmes larges prédéfinis (art, philosophie...) ne fonctionnent pas : trop généraux, sans rapport avec le contenu réel du vault.

**Décision validée** : les clusters émergent via des **notes-concept** (`note_type: concept`), pas via une taxonomie prédéfinie.
- Une note-concept est une note à part entière, qui décrit un concept transversal et linke vers les notes qui l'instancient
- Elle émerge naturellement quand l'utilisateur a accumulé assez de matière sur un sujet
- Bon niveau : assez large pour être un carrefour (5+ notes), assez précis pour être cohérent (`decentralisation` oui, `philosophie` non)
- `update_index.py` détecte déjà les candidats (tags avec 4+ notes) — c'est une suggestion, pas automatique

**Limites actuelles (connues) :**
- Détection purement quantitative — pas de signal qualitatif
- Seuil de 4 notes arbitraire, à calibrer selon densité du vault
- Aucune vérification que la note-concept créée est bien connectée aux bonnes notes
- Pas de format standardisé pour les notes-concept (liens entrants vs sortants, structure)

**Pistes d'amélioration futures :**
- Générer automatiquement un brouillon de note-concept à partir des notes candidates (LLM)
- Calculer la "densité de cluster" pour suggérir quand une note-concept est mûre
- Détecter les notes-concept devenues obsolètes (plus que 2 notes liées)
- Permettre au LLM de proposer de nouveaux `note_type` / `depth` / `source_type` si aucune valeur existante ne convient — avec validation utilisateur obligatoire avant usage. Attention : les listes courtes sont plus utiles que les listes exhaustives, donc la barre doit être haute pour créer une nouvelle valeur.

---

### [x] T5. Finaliser la séparation app / data

**Problème restant** : `notes/` et `sources/` existent encore physiquement dans `Notes_générales/` (résidu de l'ancienne architecture). Le `.gitignore` les exclut, mais ces dossiers ne devraient pas exister dans le repo app.

Actions :
- Vérifier que toutes les données sont dans `pkm-vault-data/`
- Supprimer physiquement `notes/` et `sources/` du repo app (après vérification)
- Mettre à jour les scripts qui auraient des paths codés en dur

---

### [x] T6. Nommer l'app + restructurer les dossiers data

**Nom choisi : EgoVault**

- Repo app (public) : `egovault`
- Repo data (privé) : `egovault-data`
- Dossier vault local renommé : `pkm-vault-data/` → `egovault-data/`
- `config.yaml` mis à jour : `data_path: "../egovault-data"`
- `pyproject.toml`, `README.md`, `DOCUMENTATION.md`, `FOUNDATION.md` rebrandisés

**Reste à faire (T7) :**
- Renommer le dossier local `Notes_générales/` → `egovault/` (à faire au moment du push GitHub)
- Créer le repo GitHub public `egovault` + repo privé `egovault-data`

---

### [ ] T7. Pousser sur GitHub

Prérequis : T1 terminé + repo app propre (T4 au moins partiellement)

- Créer repo GitHub public pour l'app (template pour autres utilisateurs)
- Créer repo GitHub privé pour le vault (données personnelles)
- Configurer les remotes et pousser les deux repos

Le repo app ne doit contenir **zéro** donnée utilisateur au moment du push.

---

## Chantiers prochains — Backlog détaillé

### 1. MCP server custom — connexion LLM ↔ vault

**Problème** : Claude lit les fichiers manuellement à la demande. Pas de recherche sémantique.

**Solution** : MCP server Python (~200 lignes) exposant 3 outils :
- `search_semantic(query, k=5)` — retourne les k notes les plus proches (embeddings locaux)
- `search_tags(tags[])` — filtre par tags / note_type / source_type
- `get_note(path)` — récupère une note par chemin

Modèle d'embedding : `sentence-transformers` multilingue (local, CPU, pas de cloud).
Index vectoriel : ChromaDB (simple, zéro infra) ou pgvector si migration DB.

**Bénéfice** : n'importe quel LLM avec support MCP peut interroger toute la connaissance du vault. Contexte ciblé (RAG), pas de saturation.

**Cas d'usage prioritaire — batch de sources liées** : traiter plusieurs sources en séquence et détecter les connexions entre elles. Aujourd'hui possible manuellement (session explicite "traite ces N sources ensemble"), mais limité par le contexte window (~3-4 sources courtes max). Avec le MCP, le LLM peut chercher sémantiquement "quelles notes résonnent avec ce passage ?" sans charger tous les transcripts — déblocage réel du workflow batch + proposition automatique de concepts cross-sources.

**Cas d'usage secondaire — suggestion sémantique de tags et liens** : aujourd'hui le LLM lit `_index.md` entier pour choisir des tags/liens pertinents lors de la création de notes. Ça fonctionne jusqu'à ~quelques centaines de notes. Au-delà, `search_semantic()` remplace la lecture exhaustive : on envoie le contenu de la nouvelle note, on récupère les 5-10 notes les plus proches, et on en dérive tags et liens candidats. Pas urgent maintenant.

---

### 2. Nouveaux handlers d'ingestion

`capture.py` gère YouTube, audio et vidéo. Manquent :

| Handler | Dépendance | Priorité |
|---------|-----------|----------|
| `ingest/pdf.py` | pdfminer ou pymupdf | Haute |
| `ingest/web.py` | requests + beautifulsoup | Moyenne |
| `ingest/livre.py` | pymupdf + découpage par chapitres | Basse |

Chaque handler suit le même pattern que `youtube.py` et `audio.py` : crée un drop-off dans `raw-sources/` avec `status: pending → ready/failed`.

---

### 3. Workflows LLM supplémentaires

Actuellement : Workflow A (sources externes), B (idées/réflexions), C (concepts).

Manquent pour le scope datalake :
- **Workflow D** — fiche de lecture livre (structure différente : chapitres, thèses, citations)
- **Workflow E** — note de cours technique (résumé structuré, exercices, points clés)
- **Workflow F** — documentation (description d'outil, cas d'usage, exemples)

Question ouverte : auto-sélection du workflow selon `source_type` détecté, ou human-in-the-loop ?
→ Recommandation : auto-suggestion avec confirmation humaine pour les cas ambigus.

---

### 4. Corrections mineures scripts — état post-audit 2026-03-22

| Statut | Fichier | Problème |
|--------|---------|----------|
| ✅ fait | `ingest/audio.py` | `build_folder_name()` supprimée (code mort) |
| ✅ fait | `ingest/audio.py` | `import re` supprimé (inutilisé) |
| ✅ fait | `ingest/audio.py` | `title: str = None` → `title: str \| None = None` |
| ✅ fait | `ingest/_core.py` | Sérialisation YAML manuelle → `yaml.dump` |
| ✅ fait | `ingest/_core.py` | `find_duplicate` anchored sur valeur YAML exacte |
| ✅ fait | `ingest/video.py` | `timeout=3600` sur `subprocess.run` |
| [ ] T1 | `ingest/youtube.py` | `get_metadata` avale l'exception silencieusement |
| [ ] T1 | `capture.py` + `queue.py` | Constantes dupliquées → centraliser dans `_core.py` |
| [ ] T1 | `clean_sources.py` | `import shutil` à déplacer en tête de fichier |
| [ ] T1 | `_config.py` | Cas `vault: null` → AttributeError cryptique |

Note : `parse_frontmatter()` et `NOTE_FOLDERS` dupliqués entre `update_index.py` et `check_consistency.py` — à consolider dans `scripts/_config.py` ou un futur `scripts/_vault_utils.py`.

---

### 5. `scripts/vault/` — réorganisation à faire

L'architecture cible prévoyait `scripts/vault/` pour grouper les scripts de maintenance. Non encore fait — les scripts sont à plat dans `scripts/`. À faire quand on touche ces scripts pour une autre raison.

---

### 6. Couche outil déterministe pour les workflows LLM

**Problème** : les étapes systématiques des workflows (déplacer un raw-source, mettre à jour `note_creee` dans source.md, écrire le fichier note) sont actuellement faites par le LLM en mode génératif — risque d'erreur, pas reproductible.

**Principe** : dans un système agentic, ces opérations devraient être des **tool calls déterministes**, pas du texte généré. Le LLM ne fait que le travail de jugement (analyser, rédiger, proposer) ; les effets de bord sont délégués à des outils.

**Outils cibles** (à exposer via MCP ou scripts directs) :
- `finalize_source(slug, note_path, destination)` — met à jour `note_creee`, déplace le dossier vers `sources/` ou `_archive/`
- `create_note(path, content)` — écrit le fichier note dans `notes/`
- `rebuild_index()` — wrappe `update_index.py`

**Stratégie** : implémenter au moment du MCP server (chantier 1) — les mêmes outils MCP exposés à Claude servent aussi à automatiser les effets de bord des workflows.

---

## Chantiers futurs intéressants (pas urgents)

### F0. Modes d'exécution alternatifs

**Problème** : actuellement le système nécessite Claude (API Anthropic) pour la partie agentique (reformulation, création de notes, workflows) et faster-whisper en local pour la transcription. Deux axes d'évolution :

**Version light (priorité moyenne)** — transcription via API (OpenAI Whisper API, Deepgram) à la place de faster-whisper local. Élimine le besoin de ressources CPU/GPU pour la transcription. Utile pour machines légères ou usage mobile futur.

**Version full local/open source (long terme)** — remplacer Claude par un LLM local (Ollama, Hugging Face) pour toute la partie agentique. Nécessaire pour un produit complet sans dépendance cloud et sans coût par token. Techniquement faisable mais la qualité des modèles locaux vs Claude est encore un écart significatif aujourd'hui.

**Architecture cible via MCP (plus élégante)** — le MCP server rend le système LLM-agnostique par design : l'utilisateur utilise le LLM qu'il a déjà (Claude, GPT, modèle local Ollama...) comme moteur agentique, le MCP expose les outils vault. Zéro lock-in, zéro coût LLM supplémentaire. La transcription reste un service séparé : API (Whisper, Deepgram) ou faster-whisper local selon le setup de l'utilisateur.

Actuellement : Claude API + faster-whisper local = bon équilibre qualité/simplicité.

---

### F1. IDs stables pour les sources

**Problème** : si `sources/` déménage sur un disque externe, tous les wikilinks cassent.
**Solution** : les notes référencent un `source_id` stable, pas un path. Script `resolve_source.py` fait le lien.
**Quand** : lors de la migration vers PostgreSQL.

---

### F2. Système MOC — clustering organique par tags

**Approche validée** :
1. Script calcule co-occurrence de tags (signal de cluster)
2. LLM reçoit tags + titres des notes candidates (pas le contenu)
3. LLM propose thème large + ébauche de note MOC
4. LLM peut remettre en question les thèmes existants périodiquement

**Quand** : ~50-100 notes (volume suffisant).

---

### F3. Queue d'ingestion — mode batch

La queue séquentielle existe (implémentée). Évolution future : parallélisme, priorités, retry automatique.

---

### F4. Handler PDF

`ingest/pdf.py` — dépendance `pdfminer` ou `pymupdf`. Priorité haute parmi les futurs handlers.

---

### F5. Handler web/article

`ingest/web.py` — `requests` + `beautifulsoup`. Priorité moyenne.

---

### F6. MCP server custom — connexion LLM ↔ vault

MCP server Python exposant :
- `search_semantic(query, k=5)` — embeddings locaux (sentence-transformers + ChromaDB)
- `search_tags(tags[])` — filtre par tags/note_type
- `get_note(path)` — récupère une note

Débloque : batch de sources liées, suggestion automatique de tags/liens, RAG sur tout le vault.

---

### F7. Couche outil déterministe pour les workflows LLM

Les effets de bord des workflows (déplacer raw-source, écrire note, mettre à jour source.md) devraient être des tool calls déterministes, pas du texte généré. À implémenter au moment du MCP server.

---

### F8. Recherche — projets LLM memory existants

Ce système est autant une mémoire long-terme pour LLM qu'un PKM humain. Investiguer : MemGPT/Letta, Mem0, Zep, Cognee, Graphiti. Challenger les choix architecturaux depuis `FOUNDATION.md`.

---

## En brainstorm (questions ouvertes)

- **Nom de l'app** : Anthill Memory, Elmer (ref éléphant, mémoire), autres
- **MOC** : auto-détection vs création manuelle, fréquence du scan, format de la note MOC
- **Tags thématiques larges** (`finance`, `ethique`, `histoire`) vs sous-thèmes atomiques — hybridation
- **`.elmer/`** dans le vault pour les fichiers système (queue.yaml, _index.md, _status.md) — séparation propre des métadonnées système et des notes utilisateur
- **LLM memory vs PKM** — repenser certains choix depuis l'angle "mémoire pour IA" plutôt que "notes pour humain"

---

## Architecture actuelle (état réel 2026-03-22)

### Deux repos séparés

```
Notes_générales/          ← app (code Python, public, futur GitHub template)
├── capture.py            ← point d'entrée unique
├── config.yaml           ← pointe vers pkm-vault-data (gitignored)
├── config.yaml.example
├── FOUNDATION.md         ← philosophie et axiomes
├── AMELIORATIONS.md      ← ce fichier
├── LLM.md                ← protocole complet pour le LLM
├── README.md
├── scripts/
│   ├── _config.py        ← lecture config.yaml
│   ├── ingest/
│   │   ├── _core.py      ← utilitaires partagés + constantes de détection
│   │   ├── youtube.py
│   │   ├── audio.py
│   │   └── video.py      ← nouveau
│   ├── queue.py          ← nouveau
│   ├── vault_status.py
│   ├── update_index.py
│   ├── check_consistency.py
│   └── clean_sources.py
└── tests/                ← 49/49 passing

pkm-vault-data/           ← données utilisateur (privé, futur GitHub privé)
├── .obsidian/            ← config Obsidian (sources + _* désindexés du graph)
├── notes/                ← toutes les notes
├── sources/
│   ├── raw-sources/      ← drop-offs en attente
│   │   └── _archive/
│   └── YYYY-MM-DD-slug/  ← sources permanentes
├── _index.md
└── _status.md
```

### Pipeline

```
SOURCE → capture.py → scripts/ingest/ → raw-sources/SLUG/ [status: pending→ready]
                                                  ↓
                                        LLM + Workflows A/B/C
                                                  ↓
                                        notes/slug.md  (après migration T2)
```

### Corrections d'audit appliquées (2026-03-22)

| Fichier | Correction |
|---|---|
| `_core.py` | `RAW_SOURCES` via `get_vault_path()` (fin fuite app→vault) |
| `_core.py` | Assertion path traversal sur `make_drop_off` |
| `_core.py` | `yaml.dump` remplace sérialisation YAML manuelle |
| `_core.py` | `set_status` valide les valeurs autorisées |
| `_core.py` | `find_duplicate` parse le frontmatter YAML (plus de sous-chaîne brute) |
| `_core.py` | Constantes `YOUTUBE_PATTERN/AUDIO/VIDEO_EXTENSIONS` centralisées |
| `audio.py` | Suppression `import re` + `build_folder_name` (code mort) |
| `video.py` | `timeout=3600` sur `subprocess.run` |

---

## Vision long terme — Architecture gold

**Objectif** : Personal Knowledge API exposée via MCP, accessible à n'importe quel LLM, multi-utilisateur, avec interface graphique.

```
OBJECT STORAGE (local fs ou S3-compatible)
  PDFs, audio, vidéo — fichiers lourds, non versionnés
         ↓ référence
PostgreSQL + pgvector
  notes, sources, tags (vraies relations SQL), embeddings
         ↓
FastAPI  →  /ingest  /search  /notes  /sources
         ↓                ↓
    MCP server        GUI (React ou autre)
```

**Pourquoi PostgreSQL + pgvector** : embeddings dans la même transaction que la note (cohérence native), tags comme relations SQL (intégrité), multi-user via `user_id`.

**Stratégie** : construire en parallèle du système Markdown actuel. Migration = script d'import depuis `pkm-vault-data/`. Le vault Markdown reste utilisable pendant toute la transition.

**FastAPI plutôt que LangChain** : LangChain change trop vite, overhead inutile pour le scope actuel. FastAPI wraps les scripts Python existants + appelle Claude API directement. LangChain seulement si besoin de multi-LLM ou d'orchestration complexe avérée.

**Liens inter-notes et graph view** : la migration DB résout le problème des liens exponentiels — les connexions deviennent des relations SQL filtrables (par thème, par groupe, par date). Le graph view (actuellement natif Obsidian depuis `## Liens`) peut être régénéré par script depuis la DB en exportant les paires `(note_source, note_cible)` au format attendu par l'outil de visualisation. Quand les connexions deviendront trop denses : les limiter par thème/cluster plutôt qu'en full mesh. Pas un problème actuel.

---

## Drop-offs en attente de traitement

19 notes Décentralisation dans `pkm-vault-data/sources/raw-sources/` depuis juillet 2025. À traiter via Workflow A.

Notes prioritaires :
- `intelligence-collective` — Woolley, Page, Wikipédia, Ushahidi
- `methode-scientifique` — relativité, plaques tectoniques, biais publication
- `definition-et-interet-des-desir-paths` — auto-organisation urbaine
- `resilience-systemes-decentralises` — COVID, Allemagne vs France

Après traitement individuel → candidat Workflow C : note `concept` sur la Décentralisation.
