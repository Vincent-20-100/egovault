# Spec : Découpage des sources en notes par noyau sémantique

**Date :** 2026-08-14
**Brainstorm :** conversation du 2026-08-14 (premier test end2end réel du pipeline
ingestion → notes → recherche), voir `SESSION-CONTEXT.md` §"Large source synthesis"
et open question #8 pour les preuves empiriques ayant motivé cette spec.
**Statut :** Draft — en attente de validation utilisateur
**Supersedes :** `.meta/specs/2026-04-06-large-source-synthesis-spec.md` — partiellement
(voir §9). Le seuil de déclenchement, le principe de presets et le garde-fou
`max_sub_notes` sont repris ; la cascade de stratégies (§2.2 de l'ancienne spec),
la fusion en note unique (§2.4) et le cycle de vie "sous-notes jetables" (§5) sont
remplacés.

---

## 1. Contexte

### 1.1 Le problème découvert

Premier test end2end réel (2026-08-14) : 4 sources ingérées (texte, web, YouTube,
PDF), 4 notes créées par un sous-agent (1 note par source, prompt ad hoc), notes
embeddées et testées en recherche sémantique dans les deux espaces (chunks et
notes).

**Constat empirique reproductible sur 2 sources multi-thèmes :**

| Source | Notes créées | Requête sur thème dominant | Requête sur thème niche |
|--------|--------------|----------------------------|--------------------------|
| Antifragile (7 sous-thèmes réels) | 1 | #1, distance 0.417, marge nette | **#2**, dépassée par une note sans rapport |
| Masterclass ECM/DCM (6 chapitres) | 1 | (non testé isolément) | **absente du top-5** |
| Keynote Jack Mallers (1 thème réel) | 1 | #1, marge nette (0.303 vs 0.343) | #1, marge nette |
| Blog Ayn Rand (1 thème réel) | 1 | #1 | #1 |

### 1.2 La cause racine

`tools/text/embed_note.py` confirme : une note = **un seul vecteur** (title +
docstring + body concaténés, aucun chunking interne). Une note multi-thèmes produit
donc un vecteur qui moyenne des sujets distincts — il retrouve le thème dominant
par chance statistique, mais perd tout rappel sur les thèmes secondaires.

**Principe qui en découle :** un chunk est une coupe **mécanique** (position dans
le texte) ; une note doit être une coupe **sémantique** (un noyau de sens = un
vecteur). La couche notes n'a de raison d'exister (cf. `VISION-KNOWLEDGE-COMPILER.md`,
Layer 2) que si elle respecte ce principe. **1 source → 1 note** est correct
uniquement quand la source est déjà mono-thème ; sinon, **1 source → N notes**.

### 1.3 Ce que cette spec couvre

Le découpage automatique et déterministe d'une source `rag_ready` en un ensemble
de candidats-notes cohérents par le sens, prêts à être rédigés (par un humain ou
un agent). La rédaction elle-même (le contenu de chaque note) n'est pas re-spécifiée
ici — elle utilise le contrat `create_note` / `NoteContentInput` existant.

---

## 2. Architecture

### 2.1 Vue d'ensemble

```
Ingestion (inchangé)
  → extraction → chunk → embed (chunks_vec)      [déterministe, existant]
  ↓ source atteint rag_ready
Segmentation thématique (NOUVEAU)                  [déterministe]
  → topic segmentation sur les chunks ordonnés
  → fusion budgétée (garde-fous, pas de cible)
  → N candidats-notes écrits en file d'attente
Rédaction (découplée, humain OU agent, à tout moment)
  → lit un candidat → écrit la note → create_note() → candidat marqué "done"
```

Unification importante : **il n'y a plus de branche "petite source = 1 note
directe" vs "grosse source = cascade"**. Le pipeline est uniforme — une source
courte et mono-thème produit naturellement 1 seul candidat (aucune rupture
détectée), ce qui reproduit exactement le comportement actuel sans code spécial.

### 2.2 Étape 1 — Topic segmentation (déterministe, pas de LLM)

Sur les chunks d'une source, **dans leur ordre d'origine** :

1. Calculer la similarité cosinus entre chaque paire de chunks **consécutifs**
   (les embeddings existent déjà dans `chunks_vec`).
2. Détecter les ruptures : minima locaux de similarité (creux dans la courbe
   similarité(i, i+1) le long de la source) — technique standard de topic
   segmentation (apparentée à TextTiling), aucune dépendance nouvelle.
3. Chaque plage entre deux ruptures = un **segment brut**, toujours un passage
   **continu** de la source (jamais un patchwork de positions disjointes —
   contrainte explicitement voulue pour que le texte fourni au rédacteur reste
   lisible).

Le nombre de segments bruts M est **entièrement émergent** : piloté par la
variance sémantique réelle du contenu, indépendant de la longueur de la source.
Une source longue mais focalisée sur un seul sujet peut légitimement produire
M=1 ; une source courte mais dense peut en produire plusieurs.

### 2.3 Étape 2 — Fusion budgétée (garde-fous, pas de cible)

Les segments bruts sont fusionnés par un algorithme glouton (fusionner d'abord
la paire de segments adjacents la plus proche sémantiquement), **uniquement**
pour respecter deux garde-fous — ce ne sont **pas** des objectifs à atteindre :

- **Plancher `min_chunks_per_note`** : un segment plus petit que ce seuil est
  fusionné avec son voisin le plus proche. Remède au bruit de mesure sur les
  sources courtes (ruptures artificielles détectées à tort).
- **Plafond `max_notes_per_source`** : filet de sécurité si la segmentation
  dérape (source chaotique, seuil mal calibré) — réutilise `max_sub_notes: 30`
  de l'ancienne spec.

**Explicitement rejeté :** une cible proportionnelle à la taille de la source
(ex. "1 note par 15 chunks") — testée puis invalidée pendant le brainstorm :
elle forcerait une source longue-mais-focalisée à se fragmenter artificiellement,
recréant le problème qu'on cherche à éliminer. Si le nombre de notes semble
mauvais (trop peu pour un livre, trop pour un PDF court), le vrai levier est le
**seuil de détection de rupture** (§2.2), pas un forçage a posteriori.

### 2.4 File d'attente de candidats (NOUVEAU)

Chaque candidat = un segment final (post-fusion). Persisté :

- `source_uid`
- liste ordonnée de `chunk_uids` (pas de texte dupliqué — voir §2.5)
- `sequence_index` (position parmi les candidats de la même source, pour
  affichage/navigation)
- `label` (déterministe, ex. `"chunks 12-34"` — pas de nommage LLM à ce stade,
  cf. §9 pour le nommage sémantique reporté)
- `status` : `pending` | `done` (voir §8 pour la question du verrouillage)

### 2.5 Lecture d'un candidat — pas de duplication

Le texte à lire pour rédiger la note est **concaténé à la demande** depuis les
chunks référencés (immuables après ingestion → zéro risque de désync). Rejeté :
matérialiser un `.md` par candidat en permanence (duplication de stockage sans
bénéfice, le coût de concaténation à la lecture est négligeable). Un export
ponctuel vers `.md` reste possible à la demande (ex. pour édition manuelle dans
Obsidian) mais n'est pas un artefact persistant du pipeline.

---

## 3. Composants à créer/modifier

### 3.1 Nouveaux

| Composant | Rôle |
|-----------|------|
| `tools/text/segment.py` | Topic segmentation + fusion budgétée sur les chunks d'une source |
| `infrastructure/db.py::note_candidates` (table) | `uid, source_uid, chunk_uids (ordonné), sequence_index, label, status` |
| `mcp` tool `list_note_candidates(source_uid=None, status='pending')` | Parcourir la file — miroir de `list_sources` |
| `mcp` tool `get_note_candidate(uid)` | Concatène et retourne le texte du candidat — miroir de `get_source` |

### 3.2 Modifiés

| Composant | Modification |
|-----------|--------------|
| `workflows/ingest.py` | Déclenche la segmentation dès qu'une source atteint `rag_ready` |
| `tools/vault/create_note.py` / MCP `create_note` | Accepte un `candidate_uid` optionnel ; si fourni, marque le candidat `done` après création réussie |
| `core/config.py` | Nouvelle section config (voir §4) |
| `config/system.yaml` | Section `note_segmentation` (remplace `note_generation` de l'ancienne spec) |
| `docs/architecture/DATABASES.md` | Documenter la table `note_candidates` (doit rester synchronisé avec `infrastructure/db.py`, cf. CLAUDE.md) |
| `docs/user-guide/` | Chapitre notes — expliquer le flux candidat → note (automatisme #8 CLAUDE.md, changement user-visible) |

### 3.3 Supprimés / obsolètes (de l'ancienne spec)

`direct_threshold_ratio`, `strategy: auto|direct|toc|map-reduce`, `merge_chunk_size`,
`get_context_window()`, le routing de modèle §9 de l'ancienne spec — tous liés à
la cascade "tout envoyer au LLM d'un coup avec fallback", rendue obsolète : chaque
candidat étant déjà de la taille d'un petit groupe de chunks, aucun problème de
context window ne se pose plus à ce niveau.

**Orthogonal, non repris ici :** la branche "web search summary" de l'ancienne
spec (§2.2, 1er niveau de cascade) reste une idée valable mais indépendante —
elle pourrait enrichir la rédaction d'un candidat individuel, pas remplacer le
découpage. Hors scope de cette spec.

---

## 4. Configuration (proposition)

```yaml
# system.yaml
note_segmentation:
  similarity_break_threshold: null   # seuil de detection de rupture — a calibrer (null = heuristique par defaut)
  min_chunks_per_note: 3             # plancher — fusionne les segments plus petits
  max_notes_per_source: 30           # plafond de securite (repris de max_sub_notes)
```

**Les valeurs par défaut ne sont pas figées** — elles doivent être calibrées
empiriquement sur des sources réelles (même posture que `escalation_max_distance`
dans `curate()`, documenté comme "guess" en attente de calibration). Ne pas les
traiter comme validées avant un passage de tuning dédié.

---

## 5. Interaction avec le cycle de vie draft/active (dépendance croisée)

**Ne pas confondre avec cette spec, mais dépendance directe** : `create_note`
n'a aujourd'hui aucun paramètre `status` (debt trackée séparément dans
`PROJECT-STATUS.md` § Known technical debt, "create_note draft/active approval
lifecycle has no real transitions"). Un candidat traité par un **agent** doit
produire une note `draft` (non approuvée), pas `active` (défaut actuel).

Cette spec **dépend** de la résolution de cette debt avant implémentation
complète du flux agent-rédacteur, mais **ne la redéfinit pas** — c'est un sujet
séparé, déjà tracké, à traiter dans son propre brainstorm/spec.

---

## 6. Impact sur `finalize_source`

**Question ouverte, non tranchée dans ce brainstorm** — voir §8.

---

## 7. Estimation (exemple réel — Antifragile)

Source réelle testée aujourd'hui : 308 chunks, 221k tokens, 7 thèmes identifiés
manuellement en lisant le contenu (Triade, asymétrie, convexité/optionalité,
dinde inversée, via negativa, halteres, skin in the game). Avec ce design, on
s'attend à ce que la segmentation trouve un nombre de ruptures du même ordre de
grandeur (pas garanti — dépend du seuil calibré), produisant ~5-10 candidats au
lieu d'1 note actuelle qui les moyenne tous.

---

## 8. Questions ouvertes

1. **`finalize_source` doit-il bloquer si des candidats sont encore `pending`
   ?** Cohérent avec la règle existante "une source doit atteindre `rag_ready`
   avant de générer une note", mais pas tranché ici — à décider au moment du
   plan.
2. **Verrouillage des candidats (`claimed`)** — utile seulement s'il y a
   contention multi-agent réelle sur la même file. Absent du schéma minimal
   (`pending`/`done` seulement) : à ajouter seulement si un besoin concret
   apparaît (YAGNI).
3. **Valeurs par défaut de `similarity_break_threshold` et `min_chunks_per_note`**
   — à calibrer empiriquement, pas à deviner (cf. §4).
4. **Sources déjà en base sans candidats** (créées avant cette feature) —
   backfill nécessaire ? Migration à définir au moment du plan.
5. **Label déterministe des candidats** — `"chunks 12-34"` est fonctionnel mais
   pauvre pour naviguer une longue file. Un meilleur label déterministe (ex.
   premier heading détecté dans le segment, s'il existe) est possible sans
   LLM — à affiner en implémentation, pas bloquant pour la spec.

---

## 9. Hors scope (reporté explicitement)

- **Clustering sur l'espace des notes** pour faire émerger des thèmes
  transverses entre plusieurs notes/sources, avec nommage par LLM et création
  de liens de proximité non-vectoriels (au-delà des uids/tags/source_uid déjà
  en place) tenus à jour par un script déterministe. Idée validée comme
  intéressante par l'utilisateur mais explicitement **postérieure** à cette
  spec — traiter comme item futur séparé (à ajouter à `SESSION-CONTEXT.md`
  "Deferred items").
- **Nommage sémantique des candidats par LLM** avant rédaction — écarté
  explicitement pendant le brainstorm pour rester déterministe (éviter
  d'introduire un appel LLM dans une étape qui doit rester tier-0).
- Voir aussi §3.3 pour les items de l'ancienne spec explicitement non repris.

---

## 10. Ripple — mises à jour requises (à ne pas oublier au moment du plan)

- `docs/architecture/DATABASES.md` — nouvelle table `note_candidates`
- `docs/architecture/ARCHITECTURE.md` — nouvelle étape de pipeline
- `docs/user-guide/` (chapitre notes, chapitre ingest) — flux candidat visible utilisateur
- `.claude/rules/vault-usage.md` — nouveaux outils MCP dans le workflow order
- `PROJECT-STATUS.md` — remplacer l'entrée roadmap #13 "Large source synthesis"
  par un pointeur vers cette spec
- Tests : mirroring `tests/tools/text/test_segment.py`, `tests/tools/vault/test_note_candidates*.py`
