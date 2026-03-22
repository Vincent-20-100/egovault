# Documentation — Architecture et décisions techniques

_Ce document répond à "quoi" et "pourquoi ces choix". Pour le "pourquoi ce projet existe" : voir `FOUNDATION.md`. Pour le "comment l'utiliser" : voir `LLM.md` et `README.md`._
_Dernière mise à jour : 2026-03-22_

---

## Le double rôle du système

Ce système est simultanément deux choses :

**Pour l'humain** — un second cerveau (PKM). La connaissance capturée s'accumule, se connecte, reste retrouvable des années plus tard.

**Pour les LLMs** — une mémoire long-terme. Le corpus structuré (frontmatter + tags + liens) est conçu pour être interrogeable par RAG. Quand un MCP server sera branché, n'importe quel LLM travaillera avec des années de connaissance accumulée plutôt que de repartir de zéro.

Ces deux usages ont guidé chaque décision architecturale : la structure sert autant la lisibilité humaine que la récupérabilité machine.

---

## Architecture — Deux repos

### Décision

```
egovault/           ← app (code Python, public, template GitHub)
egovault-data/      ← données (notes, sources, privé par utilisateur)
```

### Pourquoi deux repos séparés ?

**Partageabilité** : le code est une infrastructure générique. N'importe qui peut cloner le repo app, configurer son `config.yaml` vers son propre vault, et l'utiliser. Les données restent privées.

**Sécurité** : les notes contiennent des réflexions personnelles qui ne doivent jamais apparaître dans un repo public par accident. La séparation physique est la seule garantie fiable.

**Versionning indépendant** : les données changent à chaque session (nouvelles notes). Le code change lors de développements. Ces deux rythmes n'ont pas à être couplés dans le même historique git.

### Pourquoi pas un monorepo avec gitignore ?

Un `.gitignore` est une protection fragile — une erreur de configuration et des données personnelles se retrouvent dans l'historique git public. La séparation en deux repos est irréversible par construction.

---

## Architecture — Pipeline en deux étapes

```
SOURCE BRUTE → capture.py → ingest/ → raw-sources/SLUG/ [status: pending]
                                               ↓
                                     LLM + Workflows A/B/C
                                               ↓
                                         notes/slug.md
```

### Étape 1 — Ingestion déterministe

`capture.py` + `scripts/ingest/` transforment une source brute en drop-off structuré. Cette étape est **purement déterministe et scriptable** : pas de jugement, pas de LLM, 100% testable.

### Étape 2 — Traitement intellectuel

Le LLM lit le drop-off, dialogue avec l'utilisateur, produit une note. Cette étape est **interactive et humaine** : le jugement (angle, thèse, liens pertinents) ne peut pas être automatisé sans perte de valeur.

### Pourquoi cette séparation ?

Mélanger les deux créerait un système fragile : si le traitement LLM échoue à mi-chemin, la transcription serait perdue. En séparant, la transcription (longue, coûteuse en CPU) est sauvegardée indépendamment du traitement intellectuel.

---

## Format — Markdown avec frontmatter YAML

### Pourquoi Markdown et pas une base de données ?

**Réversibilité** (axiome A6 de FOUNDATION.md) : les fichiers Markdown sont lisibles par n'importe quel outil, sur n'importe quel OS, dans 20 ans. Une base de données propriétaire peut devenir inaccessible.

**Versionnable** : git sur des fichiers texte donne un historique exact de chaque modification de chaque note.

**Obsidian-compatible** : l'écosystème Obsidian (graph view, plugins, mobile) fonctionne nativement sur Markdown. Pas de conversion nécessaire.

**Limite connue** : au-delà de ~10 000 notes, les performances de recherche et de graph view se dégraderont. La migration vers PostgreSQL + pgvector est prévue (voir `AMELIORATIONS.md` — Vision long terme).

### Pourquoi ce frontmatter spécifique ?

```yaml
date_creation: YYYY-MM-DD      # immuable — traçabilité temporelle
date_modification: YYYY-MM-DD  # suivi des évolutions substantielles
note_type: synthese            # détermine le workflow applicable
source_type: youtube           # contexte de la connaissance
depth: note                    # densité — aide à prioriser les révisions
tags: [tag1, tag2]             # connexions thématiques
source: "[[sources/slug/]]"    # lien vers la source primaire
url: "https://..."             # accès direct à l'original
```

Chaque champ répond à un besoin de **récupérabilité** : retrouver par date, par type, par thème, par profondeur. Ces champs sont aussi les dimensions d'un futur index vectoriel.

---

## Convention de nommage des fichiers

### Convention cible (en cours de migration)

`titre-en-kebab-case.md` — sans date en préfixe.

### Pourquoi supprimer la date du nom ?

La date est **metadata, pas data**. Elle appartient au frontmatter (`date_creation:`), pas au nom du fichier. Un nom de fichier est un identifiant stable : il ne devrait pas changer si la note est révisée, et il ne devrait pas contenir une information déjà présente ailleurs.

La date en préfixe créait aussi une dépendance de tri artificielle : les notes apparaissaient classées chronologiquement dans les explorateurs de fichiers, alors que la classification par concept (tags, liens) est plus pertinente.

### Gestion des doublons

Si deux notes ont le même slug : suffixe numérique `titre-2.md`. Un script de détection automatique (`scripts/check_duplicates.py`, à créer) propose fusion ou numérotation.

### Convention actuelle (transitoire)

Les notes existantes sont encore en `YYYY-MM-DD-titre.md`. La migration est planifiée (T2 dans `AMELIORATIONS.md`).

---

## Sources — Séparation du vault Obsidian

### Décision

Les sources (`sources/`, `raw-sources/`) sont **exclues du graph Obsidian** via `userIgnoreFilters`. À terme, elles seront physiquement hors du vault (dossier séparé).

### Pourquoi ?

Les sources créent des nœuds parasites dans le graph Obsidian. Le graph doit représenter les **connexions entre idées** (notes), pas entre fichiers de métadonnées (source.md) ou transcripts bruts.

Une source n'est pas une connaissance — c'est un matériau brut. La note créée depuis la source est la connaissance.

### Pourquoi pas de wikilinks directs vers les sources ?

Les wikilinks Obsidian sont basés sur le path du fichier. Si les sources déménagent (disque externe, cloud), tous les liens cassent. La solution long-terme est un système d'IDs stables (voir F1 dans `AMELIORATIONS.md`).

---

## Choix des outils

### faster-whisper (transcription)

Transcription locale, sans cloud, sans coût par usage. Le modèle `medium` offre un bon équilibre qualité/vitesse sur CPU. Le mode `fast` (modèle `small`, beam_size=1) est ~6-8x plus rapide pour les longues sources.

Alternative rejetée : l'API Whisper d'OpenAI — coût récurrent, données envoyées en dehors, dépendance réseau.

### yt-dlp + youtube-transcript-api

Deux stratégies complémentaires : d'abord tenter de récupérer les sous-titres existants via `youtube-transcript-api` (instantané, haute qualité). Si indisponible, fallback sur téléchargement audio + Whisper.

### ffmpeg (extraction audio vidéo)

Standard universel pour la manipulation audio/vidéo. Déjà requis par yt-dlp dans la plupart des configurations. Le handler `video.py` l'utilise pour extraire l'audio des fichiers MP4 avant transcription Whisper.

### PyYAML

Sérialisation/désérialisation des frontmatters et de la queue. `yaml.safe_load` utilisé exclusivement (pas de `yaml.load` non sécurisé). `yaml.dump` pour la génération — évite la sérialisation manuelle fragile.

### pytest

Framework de test standard Python. Structure miroir : `tests/ingest/test_audio.py` ↔ `scripts/ingest/audio.py`. 49 tests, 0 échec.

---

## Scripts de maintenance

| Script | Rôle | Quand |
|--------|------|-------|
| `vault_status.py` | Snapshot état vault → `_status.md` | Début de session |
| `update_index.py` | Reconstruit `_index.md` depuis frontmatters | Fin de session |
| `check_consistency.py` | Audit qualité (tags, liens, formats) | Hebdomadaire |
| `clean_sources.py` | Orphelins + vidage `_archive/` | À la demande |
| `queue.py` | Gestion queue d'ingestion | Via `capture.py queue` |

---

## Queue d'ingestion

Fichier `sources/queue.yaml` dans le vault (gitignored — état runtime).

```yaml
pending:
  - {type: youtube, source: "https://...", added: "2026-03-22"}
  - {type: video, source: "/path/to/file.mp4", title: "Mon titre"}
done:
  - {type: youtube, source: "https://...", ingested: "2026-03-22"}
failed:
  - {type: audio, source: "/path/...", error: "Fichier introuvable"}
```

Commandes : `capture.py queue add`, `queue run`, `queue status`, `queue clear-done`.

---

## Sécurité

Points vérifiés lors de l'audit 2026-03-22 :

- **Pas de `shell=True`** dans les appels subprocess — pas d'injection de commandes shell
- **`yaml.safe_load` exclusivement** — pas de désérialisation YAML non sécurisée
- **Assertion path traversal** dans `make_drop_off` — le drop-off ne peut pas sortir de `raw-sources/`
- **Reconstruction URL YouTube** depuis l'ID extrait, pas depuis l'URL brute — pas de SSRF
- **Aucun credential hardcodé** — `config.yaml` gitignored
- **`find_duplicate`** compare les URLs par parsing YAML, pas par sous-chaîne brute

---

## Ce document et les autres

| Fichier | Répond à |
|---------|----------|
| `FOUNDATION.md` | **Pourquoi** ce projet existe — philosophie, axiomes, vision |
| `DOCUMENTATION.md` | **Quoi et pourquoi ces choix** — architecture, décisions justifiées |
| `AMELIORATIONS.md` | **Comment évoluer** — TODO, backlog, brainstorm |
| `LLM.md` | **Comment faire** — protocoles opérationnels session par session |
| `README.md` | **Comment démarrer** — installation, commandes de base |
