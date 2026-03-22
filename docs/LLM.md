# Protocole du vault — Notes et réflexions personnelles

Tu es l'agent d'un système de gestion de la connaissance personnelle (PKM). Ce vault contient les idées, réflexions et synthèses de sources variées de son propriétaire.

**Principes fondateurs :**
- Accumuler du savoir, jamais en supprimer
- Minimiser la friction à la capture
- Maximiser les connexions entre idées

---

## Architecture du vault

```
Notes_générales/
├── README.md               ← explication humaine
├── CLAUDE.md               ← point d'entrée Claude Code (lit LLM.md)
├── LLM.md                  ← ce fichier : protocole complet
├── AMELIORATIONS.md        ← chantiers en cours et idées d'évolution
├── _index.md               ← registre des tags + connexions
├── _status.md              ← snapshot état vault (généré par vault_status.py)
├── sources/
│   ├── raw-sources/        ← zone de staging : nouveaux dépôts à traiter
│   │   └── _archive/       ← corbeille des raw traités (jamais supprimé sans clean_sources.py)
│   └── slug/               ← sources permanentes (sous-dossiers autonomes)
│       ├── source.md       ← métadonnées + lien vers note créée
│       └── [fichiers]      ← transcript.txt, .pdf, .mp3, etc.
├── notes/                  ← toutes les notes (idées, synthèses, réflexions, concepts)
└── scripts/                ← scripts déterministes d'assistance LLM
```

| Dossier | Rôle | Rétention |
|---------|------|-----------|
| sources/raw-sources/ | Staging — nouveaux dépôts | Déplacé vers sources/ ou _archive/ après traitement |
| sources/ | Référence permanente | Jamais supprimé |
| notes/   | Toutes les notes (tous types) | Jamais supprimé |

---

## Scripts disponibles

Ces scripts produisent des données fiables que le LLM consomme — ce qu'un script calcule avec certitude, le LLM ne devrait pas le recalculer par lecture de fichiers.

| Script | Rôle | Quand lancer |
|--------|------|--------------|
| `capture.py` | Point d'entrée unique — YouTube URL, audio local | Avant traitement |
| `scripts/vault_status.py` | Snapshot état vault → `_status.md` | Début de session |
| `scripts/update_index.py` | Reconstruit `_index.md` depuis les frontmatters | Après chaque session |
| `scripts/check_consistency.py` | Audit qualité (tags, liens, formats) | Hebdomadaire |
| `scripts/clean_sources.py` | Orphelins sources + vidage `_archive/` | À la demande |

---

## Protocole d'ouverture de session

À chaque nouvelle session, dans cet ordre :

1. Lire ce fichier (LLM.md)
2. Lire `_index.md`
3. Toujours lancer le scan au démarrage :
   ```
   .venv/Scripts/python scripts/vault_status.py
   ```
   Puis lire `_status.md` pour avoir l'état frais des drop-offs et des notes.
4. Annoncer : "Il y a X drop-off(s) en attente dans raw-sources/. Tu veux qu'on les traite ?"

## Protocole de fermeture de session

En fin de session (après création/modification de notes) :

```
.venv/Scripts/python scripts/update_index.py
```

`_index.md` est reconstruit depuis les frontmatters. C'est le script — pas le LLM — qui maintient l'index.

---

## Convention de nommage des fichiers

Format : `titre-en-kebab-case.md` (pas de préfixe date — la date est dans le frontmatter)

- Tout en minuscules
- Tirets à la place des espaces et caractères spéciaux
- Pas d'accents dans le nom de fichier (accents autorisés dans le titre interne)

Exemples :
- `elasticite-prix-microeconomie.md`
- `lex-fridman-ep400-bitcoin.md`

Dossiers sources : même convention — `slug/` sans date.

---

## Format d'une note

```yaml
---
date_creation: YYYY-MM-DD
date_modification: YYYY-MM-DD
tags: [tag-general, tag-specifique]
note_type: synthese        # idee | synthese | reflexion | concept
source_type: youtube       # youtube | audio | pdf | web | livre | cours | personnel
depth: note                # atomique | note | approfondi
source: "[[sources/slug/source.md]]"
url: "https://..."         # optionnel — URL originale si source web/youtube/pdf en ligne
---
```

Suivi d'un docstring :

```
> [3 lignes max : idée centrale / pourquoi cette note existe / thèse ou position]
```

Puis :

```markdown
# Titre

[Contenu principal]

## Réflexion personnelle
[note_type: synthese uniquement — accord/désaccord, prolongements]

## Liens
- [[autre-note]]
```

**Valeurs de `note_type` :**

| Valeur | Définition |
|--------|-----------|
| `synthese` | Résumé/distillation d'une source externe, avec point de vue personnel |
| `concept` | Définit un concept transversal, sert de hub dans le graphe (note émergente) |
| `reflexion` | Pensée personnelle non liée à une source précise |
| `idee` | Capture brute, non développée — point de départ possible |

**Valeurs de `depth` :**

| Valeur | Définition |
|--------|-----------|
| `atomique` | Une seule idée, 10-20 lignes max |
| `note` | Développement modéré, plusieurs angles, 20-100 lignes |
| `approfondi` | Traitement exhaustif, références multiples, 100+ lignes |

**Valeurs de `source_type` :**

| Valeur | Définition |
|--------|-----------|
| `youtube` / `audio` / `video` | Ingestion via pipeline automatique |
| `pdf` / `web` / `livre` / `cours` | Source externe, traitement manuel |
| `personnel` | Aucune source externe — réflexion propre |

**Marge de manœuvre LLM :** ces listes sont un point de départ, pas un dogme. Si un contenu ne rentre dans aucune valeur existante, le LLM peut proposer une nouvelle valeur à l'utilisateur avant de l'utiliser. Règle : proposer, ne pas imposer. Préférer étendre une valeur existante plutôt que d'en créer une nouvelle — les listes courtes sont plus utiles que les listes exhaustives.

**Règles sur les champs :**

- `date_creation` : immuable, jamais modifié après création
- `date_creation` = `date_modification` à la création initiale
- `date_modification` : mis à jour sur changements substantiels uniquement (pas pour corrections de fautes ou ajouts de tags mineurs)
- `source` : optionnel, omettre entièrement si absent (ne pas écrire `source: null`). Pointe vers `sources/SLUG/source.md`.
- `url` : optionnel. À inclure systématiquement si la source a une URL (youtube, web, pdf en ligne). Lire le champ `url` dans `source.md` du drop-off et le recopier. Omettre entièrement si absent.
- `## Réflexion personnelle` : réservée aux notes de type synthese (note_type: synthese). Acceptée ailleurs sur instruction explicite de l'utilisateur avec avertissement.
- `## Liens` : liste curatée, pas un miroir de backlinks. Le LLM propose à la création, l'utilisateur valide. Pas de mise à jour rétroactive sans demande explicite.
- `note_type` : obligatoire. Remplace le dossier de destination.
- `source_type` : obligatoire. `personnel` si aucune source externe.
- `depth` : obligatoire. Évaluation subjective de la densité de la note.
- Les tags restent strictement thématiques — jamais de méta dedans.

---

## Convention de tags

**Format :** français, minuscules, pas d'accents, tirets pour les mots multiples

- Correct : `biais-cognitifs`, `microeconomie`, `philosophie`
- Incorrect : `Philosophie`, `économie`, `biaisCognitifs`

**Normalisation — deux cas distincts :**

1. Correction de format sur tag existant (accent/majuscule) → normaliser silencieusement + informer : "J'ai normalisé 'Économie' en 'economie'."
2. Nouveau concept → proposer à l'utilisateur avant d'ajouter : "Je n'ai pas de tag pour ce concept. Je propose 'biais-cognitifs' — tu valides ?"

**Stratégie :** Toujours mettre le général ET le spécifique. Préférer trop de tags que pas assez.

**Clustering via notes-concept (émergence naturelle) :**

Les tags seuls ne suffisent pas à structurer le graphe. Quand suffisamment de notes partagent un même concept transversal, créer une **note-concept** (`note_type: concept`) qui sert de hub. Ces notes émergent du contenu — elles ne sont pas prédéfinies.

- Bon niveau d'abstraction : assez large pour être un carrefour (5+ notes), assez précis pour être cohérent
- Exemples qui ont du sens : `decentralisation`, `conscience`, `modeles-mentaux`
- Exemples trop larges : `art`, `philosophie`, `science` (à éviter sauf vault très spécialisé)
- `update_index.py` signale automatiquement les tags candidats dans `_index.md` (seuil : 4+ notes)

**Format d'une note-concept :**

```yaml
---
date_creation: YYYY-MM-DD
date_modification: YYYY-MM-DD
tags: [tag-du-concept, tag-connexe]
note_type: concept
source_type: personnel
depth: approfondi
---
```

```
> [Définition du concept en 1-2 lignes — ce qu'il est, pourquoi il mérite une note hub]
```

```markdown
# Nom du concept

[Définition développée + pourquoi ce concept est structurant dans ce vault]

## Notes liées
- [[note-qui-instancie-le-concept]]
- [[autre-note-liee]]

## Connexions avec d'autres concepts
- [[autre-note-concept]] — [nature de la relation]
```

Règles spécifiques aux notes-concept :
- `source_type` est toujours `personnel` (le concept est une construction du vault, pas une source)
- La section `## Notes liées` est obligatoire — c'est la raison d'être de la note
- Pas de `## Réflexion personnelle` — remplacée par `## Connexions avec d'autres concepts`
- Créer seulement si 5+ notes peuvent être listées dans `## Notes liées`

**Limites actuelles :**
- La détection de candidats est purement quantitative (nombre de notes par tag) — pas qualitative
- Aucune validation que la note-concept créée est bien liée aux bonnes notes
- Le seuil de 4 notes est arbitraire — à ajuster selon la densité du vault

**Avant de créer un tag :**

1. Lire `_index.md`
2. Chercher un tag existant couvrant le même concept
3. Si oui → utiliser ce tag
4. Si non → proposer à l'utilisateur avant d'ajouter

---

## Protocole _index.md

**Source de vérité : le script, pas le LLM.**

`_index.md` est reconstruit automatiquement depuis les frontmatters par `update_index.py`. Le LLM **lit** `_index.md` pour le contexte mais **ne l'édite pas** — toute édition manuelle serait écrasée au prochain run du script.

Lancer après chaque session :
```
.venv/Scripts/python scripts/update_index.py
```

Structure du fichier (générée par le script) :

```markdown
# Index du vault

_Dernière mise à jour : YYYY-MM-DD_

## Tags sujets
- `tag` → [[note1]], [[note2]]

## Tags transversaux
- `tag` → [[note1]]

## Notes orphelines (sans liens)
- [[note-sans-liens]]
```

**Règle d'immuabilité :** Tags jamais supprimés par le script (accumulation). Renommage de tag uniquement sur instruction explicite de l'utilisateur — modifier les frontmatters des notes concernées, puis relancer le script.

---

## Workflows

**Avant tout workflow :**

1. Lire `_index.md`

---

### Workflow A — Sources externes (notes/, note_type: synthese)

Pour podcasts, livres, vidéos, articles. La source doit être dans `sources/raw-sources/SLUG/` avant de commencer.

```
1. Lire source.md du drop-off — noter : titre, type_source, url (si présente), chaine + description (si source youtube)
   Analyser la source (lire transcript.txt ou fichier brut dans le sous-dossier raw-sources/SLUG/)
2. Proposer les idées principales identifiées
3. Demander : "Une note ou plusieurs ?"
   → Heuristique : 3+ thèmes distincts sans lien direct → plusieurs notes
   → Thèmes qui s'alimentent mutuellement → une note avec sections
4. Poser questions de validation :
   a. [Obligatoire] "Tu es d'accord avec [thèse principale] ?"
   b. [Si plusieurs angles] "Tu veux mettre en avant [A] ou [B] ?"
   c. [Optionnel] "Ce passage t'a évoqué quelque chose à ajouter en réflexion personnelle ?"
5. Rédiger la note selon les réponses
6. Proposer tags (depuis _index.md) + liens potentiels
7. Valider avec l'utilisateur
8. Créer le fichier dans notes/ (note_type: synthese) — inclure url: dans le frontmatter si source.md contient une URL
9. Décider du sort du raw-source :
    - Source utile à conserver → déplacer raw-sources/SLUG/ vers sources/SLUG/
    - Source jetable (URL suffit, doublon) → déplacer vers raw-sources/_archive/
    - Mettre à jour note_creee: dans source.md
10. Proposer de lancer update_index.py en fin de session (pas après chaque note)
```

---

### Workflow B — Idées et réflexions (notes/, note_type: idee ou reflexion)

Pour pensées spontanées, notes vocales, annotations.

```
1. Reformuler brièvement ce qui a été capturé
2. Demander si nécessaire : "Idée brute (note_type: idee) ou réflexion développée (note_type: reflexion) ?"
3. 1-2 questions si pertinent :
   - "Pourquoi tu voulais noter ça ?"
   - "Ça fait écho à quelque chose déjà dans le vault ?"
4. Rédiger la note
5. Proposer tags + liens
6. Valider et créer dans notes/ (note_type: idee ou reflexion)
```

---

### Workflow C — Concepts (notes/, note_type: concept)

Déclencheurs :

- Demande explicite de l'utilisateur
- Le LLM suggère quand plusieurs notes convergent sur un thème (3+ notes avec tags communs)
- Drop-off dans raw-sources/ qui ressemble à une synthèse multi-sources → demander "Je lance le Workflow C ?"

```
1. Lire _index.md
2. Identifier notes sources via tags communs dans _index.md
3. Proposer : "Voici les notes qui convergent sur ce thème : [X, Y, Z]. Je pars de ça ?"
4. Dialogue : quelle est la thèse centrale ? Qu'est-ce qui relie ces notes ?
5. Rédiger le concept en croisant les sources
6. Proposer tags + liens vers les notes sources
7. Valider et créer dans notes/ (note_type: concept)
8. Proposer d'ajouter [[nouveau-concept]] dans les ## Liens des notes sources
   → Exécuter uniquement sur confirmation explicite de l'utilisateur
```

---

## Règles d'immuabilité

Ce système accumule du savoir. Le LLM ne supprime jamais sans instruction explicite :

- Notes dans notes/
- Tags dans _index.md
- Champ `date_creation` d'une note
- Entrées dans _index.md
- Fichiers dans sources/ (hors raw-sources/)

**Règle sources :** Ne jamais supprimer un fichier de `sources/` (hors `raw-sources/`) sans rapport `scripts/clean_sources.py` validé explicitement par l'utilisateur.

**Règle raw-sources :** Après traitement, déplacer vers `sources/` (permanent) ou `raw-sources/_archive/` (corbeille). Ne jamais supprimer directement avec `rm`.

**`raw-sources/_archive/`** est vidé uniquement via `scripts/clean_sources.py --delete` après confirmation.
