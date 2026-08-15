# Spec : Découpage des sources en notes par noyau sémantique

**Date :** 2026-08-14 (Mis à jour : 2026-08-15)  
**Brainstorm :** conversation des 2026-08-14 & 2026-08-15 (premier test end2end réel, cadrage neurosciences, validation du cycle de vie unifié).  
**Statut :** Validé — Prêt pour plan d'implémentation (Plan-Ready)  
**Supersedes :** `.meta/archive/specs/2026-04-06-large-source-synthesis-spec.md` — entièrement remplacée par ce design déterministe par segmentation de chunks.

---

## 1. Contexte

### 1.1 Le problème découvert

Premier test end2end réel (2026-08-14) : 4 sources ingérées (texte, web, YouTube, PDF), 4 notes créées par un sous-agent (1 note par source, prompt ad hoc), notes embeddées et testées en recherche sémantique dans les deux espaces (chunks et notes).

**Constat empirique reproductible sur 2 sources multi-thèmes :**

| Source | Notes créées | Requête sur thème dominant | Requête sur thème niche |
|---|---|---|---|
| Antifragile (7 sous-thèmes réels) | 1 | #1, distance 0.417, marge nette | **#2**, dépassée par une note sans rapport |
| Masterclass ECM/DCM (6 chapitres) | 1 | (non testé isolément) | **absente du top-5** |
| Keynote Jack Mallers (1 thème réel) | 1 | #1, marge nette (0.303 vs 0.343) | #1, marge nette |
| Blog Ayn Rand (1 thème réel) | 1 | #1 | #1 |

### 1.2 La cause racine

`tools/text/embed_note.py` confirme : une note = **un seul vecteur** (title + docstring + body concaténés, aucun chunking interne). Une note multi-thèmes produit donc un vecteur qui moyenne des sujets distincts — il retrouve le thème dominant par chance statistique, mais perd tout rappel sur les thèmes secondaires.

**Principe qui en découle :** un chunk est une coupe **mécanique** (position dans le texte) ; une note doit être une coupe **sémantique** (un noyau de sens = un vecteur). La couche notes n'a de raison d'exister (cf. `docs/VISION-KNOWLEDGE-COMPILER.md`, Tier 2) que si elle respecte ce principe. **1 source → 1 note** est correct uniquement quand la source est déjà mono-thème ; sinon, **1 source → N notes**.

### 1.3 Ce que cette spec couvre

Le découpage automatique et déterministe d'une source `rag_ready` en un ensemble de candidats-notes cohérents par le sens, prêts à être rédigés (par un humain ou un agent). La rédaction elle-même utilise le contrat `create_note` existant enrichi du statut de relecture `review_status`.

---

## 2. Architecture

### 2.1 Vue d'ensemble

```
Ingestion (inchangé)
  → extraction → chunk → embed (chunks_vec)      [déterministe, existant]
  ↓ source atteint rag_ready
Segmentation thématique (NOUVEAU)                  [déterministe, Tier 0]
  → topic segmentation sur les chunks ordonnés (creux cosinus)
  → fusion budgétée (garde-fous, pas de cible)
  → N candidats-notes écrits en base (note_candidates: queued)
Rédaction (découplée, humain OU agent, à tout moment)
  → lit un candidat → écrit la note → create_note(candidate_uid=...)
  → candidat marqué 'converted'
  → note créée (review_status: 'unreviewed' si agent, 'reviewed' si humain)
  → note immédiatement active, embeddée et interrogeable dans notes_vec
```

Unification importante : **il n'y a plus de branche "petite source = 1 note directe" vs "grosse source = cascade"**. Le pipeline est uniforme — une source courte et mono-thème produit naturellement 1 seul candidat (aucune rupture détectée), ce qui reproduit exactement le comportement sans code spécial.

### 2.2 Étape 1 — Topic segmentation (déterministe, pas de LLM)

Sur les chunks d'une source, **dans leur ordre d'origine** :

1. Calculer la similarité cosinus entre chaque paire de chunks **consécutifs** (les embeddings existent déjà dans `chunks_vec`).
2. Détecter les ruptures : minima locaux de similarité (creux dans la courbe similarité(i, i+1) le long de la source) — technique standard de topic segmentation (apparentée à TextTiling), aucune dépendance nouvelle.
3. Chaque plage entre deux ruptures = un **segment brut**, toujours un passage **continu** de la source (jamais un patchwork de positions disjointes).

Le nombre de segments bruts $M$ est **entièrement émergent** : piloté par la variance sémantique réelle du contenu, indépendant de la longueur de la source.

### 2.3 Étape 2 — Fusion budgétée (garde-fous, pas de cible)

Les segments bruts sont fusionnés par un algorithme glouton (fusionner d'abord la paire de segments adjacents la plus proche sémantiquement), **uniquement** pour respecter deux garde-fous :

- **Plancher `min_chunks_per_note` (défaut : 3)** : un segment plus petit que ce seuil est fusionné avec son voisin le plus proche. Remède au bruit de mesure sur les sources courtes.
- **Plafond `max_notes_per_source` (défaut : 30)** : filet de sécurité si la segmentation dérape (source chaotique).

### 2.4 File d'attente de candidats & Labeling Déterministe

Chaque candidat = un segment final (post-fusion), persisté dans la table `note_candidates` :

- `uid` (UUID4)
- `source_uid` (UUID4)
- `chunk_uids` (TEXT / JSON list ordonnée)
- `sequence_index` (INTEGER, position parmi les candidats de la source)
- `label` (TEXT déterministe) :
  - **Priorité 1 :** Premier titre Markdown (`#`, `##`, `###`) détecté dans le premier chunk du segment s'il existe (ex: `"Chapitre 3 : L'asymétrie de payoff"`).
  - **Fallback :** `"chunks {start_idx}-{end_idx} ({premiers_mots}...)"`.
- `status` (TEXT) : `queued` | `converted` | `skipped`

### 2.5 Traçabilité, Localisateurs et Lecture d'un Candidat

Le texte à lire pour rédiger la note est **concaténé à la demande** depuis les chunks référencés (immuables après ingestion → zéro risque de désynchronisation). Aucun fichier intermédiaire dupliqué sur le disque.

**Indicateurs d'ordre et localisateurs de passage :**
Lors de la lecture d'un candidat (`get_note_candidate(uid)`), le texte est préfixé d'un en-tête de repérage contextuel :
```markdown
[SOURCE: {source_slug} | CHUNKS: {start_pos}-{end_pos} | LOCATOR: {timestamps_ou_pages_ou_lignes}]
---
{texte_concatene_des_chunks}
```
- **Pour l'audio/vidéo :** Intervalle de temps (ex: `00:14:23 - 00:22:15`, calculé par `min(start)` $\to$ `max(end)`).
- **Pour les livres/PDFs :** Intervalle de pages (ex: `p. 42-55`).
- **Pour le texte brut/web :** Lignes du markdown original (ex: `L120-L245`).

**Traçabilité bidirectionnelle Note ↔ Chunks (La chaîne de preuve) :**
- La table `notes` enregistre la colonne `candidate_uid` (clé étrangère optionnelle vers `note_candidates`).
- Dans le **YAML Frontmatter Obsidian** de la note générée :
  ```yaml
  ---
  uid: note_20260815_antifragile_convexity
  source: src_taleb_antifragile
  locator: "00:14:20 - 00:22:05"
  chunks: [chk_12, chk_13, chk_14]
  ---
  ```
- Les outils `get_note(uid)` et `search_notes(...)` renvoient un bloc structuré `provenance` :
  ```json
  {
    "uid": "note_xyz",
    "title": "L'asymétrie de payoff et l'antifragilité",
    "provenance": {
      "source_uid": "src_taleb_antifragile",
      "chunk_uids": ["chk_12", "chk_13", "chk_14"],
      "locator": "00:14:20 - 00:22:05"
    }
  }
  ```
- L'outil MCP **`get_chunks(chunk_uids=[...])`** permet à l'humain ou à l'agent de forer instantanément (*drill-down*) vers le verbatim exact sans relire toute la source.

---

## 3. Composants à créer/modifier

### 3.1 Nouveaux Composants

| Composant | Rôle |
|---|---|
| `tools/text/segment.py` | Topic segmentation + fusion budgétée sur les chunks d'une source $\to$ `list[CandidateSegment]` |
| `infrastructure/db.py::note_candidates` (table) | `uid, source_uid, chunk_uids, sequence_index, label, locator, status` |
| `mcp` tool `list_note_candidates(source_uid=None, status='queued')` | Parcourir la file des candidats |
| `mcp` tool `get_note_candidate(uid)` | Concatène et retourne le texte intégral du candidat avec localisateurs |
| `mcp` tool `skip_note_candidate(uid)` | Marque un candidat comme `skipped` (ex: transition ou intro ignorée) |
| `mcp` tool `get_chunks(chunk_uids: list[str])` | Récupère directement les chunks bruts complets par UIDs pour inspection/drill-down |

### 3.2 Composants Modifiés

| Composant | Modification |
|---|---|
| `workflows/ingest.py` | Déclenche la segmentation dès qu'une source atteint `rag_ready` et peuple `note_candidates` |
| `tools/vault/create_note.py` | Accepte un `candidate_uid` optionnel (persiste le lien sur la note et marque le candidat `converted`) et un `review_status` (`'unreviewed'` si agent, `'reviewed'` si humain) |
| `infrastructure/db.py` | Ajout de la table `note_candidates`, colonnes `candidate_uid` et `review_status` sur `notes`, méthodes CRUD associées |
| `core/config.py` & `config/system.yaml` | Section `note_segmentation` |
| `docs/architecture/DATABASES.md` | Documenter `note_candidates`, `notes.candidate_uid` et `notes.review_status` |
| `docs/user-guide/` | Expliquer le flux candidat $\to$ note dans le chapitre notes |

---

## 4. Cycle de Vie des Notes & Statuts Unifiés

Cette spec résout formellement l'ancienne dette de statut (#151) :

```
1. Candidat (note_candidates.status) :
   queued ──► converted (si note créée via create_note)
          └──► skipped   (si jugé non pertinent par humain/agent)

2. Note (notes.review_status) :
   unreviewed ──► reviewed (dès que validée ou éditée par un humain)
```

**Règle d'or :** Une note créée avec `review_status="unreviewed"` est **immédiatement active, embeddée et interrogeable dans `notes_vec` par `curate()`**. Elle n'est pas masquée ou désactivée ; elle porte simplement l'information claire qu'elle est issue d'une synthèse IA non encore relue par l'humain.

---

## 5. Configuration (`config/system.yaml`)

```yaml
# system.yaml
note_segmentation:
  similarity_break_threshold: null   # seuil de détection de rupture (null = heuristique adaptative par défaut)
  min_chunks_per_note: 3             # plancher — fusionne les segments plus petits
  max_notes_per_source: 30           # plafond de sécurité
```

---

## 6. Impact sur `finalize_source`

`finalize_source` **ne bloque pas** si des candidats sont encore `queued`.  
Une source `rag_ready` avec des candidats `queued` est un état sain et permanent, permettant une génération de notes progressive, à la demande ou partielle.

---

## 7. Migration & Backfill

Un script de migration `scripts/temp/002_backfill_note_candidates.py` permettra de découper automatiquement les sources existantes déjà en base pour alimenter la table `note_candidates`.

---

## 8. Ripple — Mises à jour requises

- `docs/architecture/DATABASES.md` — schéma de `note_candidates` et `notes.review_status`
- `docs/architecture/ARCHITECTURE.md` — pipeline de segmentation
- `docs/user-guide/07-notes.md` — explication du cycle candidats $\to$ notes $\to$ relecture
- `.claude/rules/vault-usage.md` — intégration de `list_note_candidates` et `get_note_candidate`
- Tests unitaires complets : `tests/tools/text/test_segment.py`, `tests/tools/vault/test_note_candidates.py`
