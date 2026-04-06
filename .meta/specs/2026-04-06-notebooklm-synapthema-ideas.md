# Brainstorm : Idées inspirées de NotebookLM & Synapthema

**Date :** 2026-04-06
**Contexte :** Veille produit — analyse de NotebookLM (Google) et Synapthema (open source)
**Statut :** Notes d'idées — à transformer en brainstorm dédié quand pertinent

---

## Idées à haute pertinence pour EgoVault

### 1. Multi-source workflow (synthèse créative)

L'utilisateur exprime une idée ou question → le LLM recherche les notes/sources pertinentes
dans le vault → brainstorm interactif → note multi-source avec liens dans le graph.

Ce n'est ni de l'ingest (source → note) ni du search (query → résultats).
C'est de la **synthèse créative assistée** — le use case qui différencie un vrai
knowledge vault d'un simple résumeur.

Le graph de liens se construit naturellement (note liée à N sources + N notes existantes).

**Priorité : haute** — c'est un workflow fondamental pour le vault.

### 2. Cross-document entity resolution (inspiré Synapthema)

Extraire les entités/concepts de chaque source → fusionner → détecter les recoupements
entre documents. Synapthema fait ça avec un topological sorting des concepts.

Utile pour : multi-source synthesis, détection de thèmes récurrents, enrichissement
automatique des tags.

**Priorité : moyenne** — renforce le multi-source, pas indispensable en V1.

### 3. Re-traitement avec template différente (cache reuse)

Le transcript source est déjà en DB. Relancer `generate_note_from_source(uid, template="critique")`
avec un autre template ne nécessite PAS de re-ingérer.

Pour les grosses sources : les sous-notes intermédiaires (cache) pourraient être réutilisées
si on les persiste — les chunks sont les mêmes, seul le prompt change.

**Priorité : moyenne** — renforce l'argument pour le cache debug persisté dans la spec
large source synthesis.

### 4. Citations sourcées dans les notes

Forcer le LLM à citer le passage exact de la source dans la note (blockquote avec référence
au chunk). Améliore la fiabilité ET la traçabilité dans le graph.

NotebookLM fait ça très bien — chaque réponse pointe vers le passage source.

**Priorité : moyenne** — amélioration de la template de génération.

---

## Idées à pertinence future (hors scope court terme)

### 5. Templates spécialisées d'analyse (inspiré Open Notebook Transformers)

Comme les "Transformers" structurés : extraction d'intent, scope, hypothèses, risques.
Pas juste du résumé — de l'analyse structurée.

Templates possibles : `extraction-concepts.yaml`, `critique-arguments.yaml`,
`analyse-risques.yaml`, `comparaison-sources.yaml`.

### 6. Checkpoints resumables dans la pipeline (inspiré Synapthema)

Pipeline de synthèse resumable — si ça crash au chapitre 8/15, on reprend au 8.
Synapthema fait ça avec des checkpoints à chaque stage.

### 7. Deep reading phase (inspiré Synapthema)

Phase d'extraction de concepts/entités par le LLM AVANT la génération de note.
Actuellement on passe directement au résumé. Cette étape intermédiaire pourrait
améliorer la qualité de la synthèse finale.

---

## Hors scope EgoVault

- Flashcards / quiz / spaced repetition (e-learning, pas knowledge vault)
- Cours interactif HTML (notre output = markdown Obsidian)
- Audio overview podcast-style (NotebookLM feature, fun mais hors scope)
