# Spec : Synthèse de grosses sources

**Date :** 2026-04-06
**Brainstorm :** `2026-04-06-large-source-synthesis-notes.md`
**Statut :** Draft — en attente de validation
**Supersedes :** Aucun (nouveau sujet)

---

## 1. Contexte

Le pipeline actuel (`generate_note_from_source`) envoie `source.transcript` en entier
au LLM avec la template de génération. Quand la source dépasse la context window du modèle,
la génération échoue ou produit un résultat tronqué.

Le pipeline d'ingestion convertit déjà les sources en markdown structuré (PDF → md avec
titres, audio → transcript). Le chunking/embedding pour le search est un problème séparé
(il bénéficie naturellement de la structure markdown).

**Cette spec traite uniquement la génération de notes synthétiques pour les grosses sources.**

---

## 2. Architecture

### 2.1 Seuil de déclenchement

Le mode multi-pass se déclenche quand la source dépasse un ratio de la context window :

```
source_tokens > context_window × direct_threshold_ratio
```

- `context_window` : auto-détecté ou configuré (voir §3.2)
- `direct_threshold_ratio` : 0.6 par défaut (laisse de la place pour le prompt + output)
- En dessous du seuil : génération directe (pipeline actuel, inchangé)
- Au dessus : cascade multi-pass

### 2.2 Cascade de stratégies avec fallback

```
┌─────────────────────────────────────────────┐
│ Source > seuil ?                             │
│   non → génération directe (inchangé)       │
│   oui ↓                                     │
├─────────────────────────────────────────────┤
│ Web search résumé ? (si activé par user)    │
│   trouvé → utiliser comme input principal   │
│   pas trouvé ↓                              │
├─────────────────────────────────────────────┤
│ TOC détectée ? (H1/H2 dans le markdown)     │
│   oui → split par chapitre → sous-notes     │
│   non ↓                                     │
├─────────────────────────────────────────────┤
│ Map-Reduce : split en sections de N tokens  │
│   → sous-note par section                   │
├─────────────────────────────────────────────┤
│ Synthèse finale : toutes les sous-notes     │
│   → note finale via template + prompt merge │
└─────────────────────────────────────────────┘
```

L'utilisateur peut aussi forcer une stratégie via config.

### 2.3 Réutilisation de la template à chaque niveau

Chaque sous-génération (par chapitre ou par chunk) utilise la **même template** que la
note finale (standard.yaml ou custom). Le LLM produit pour chaque sous-section :
- title, docstring, body, tags, note_type — même schéma que `NoteContentInput`

Le prompt de sous-génération est enrichi avec :
- Le contexte global : "Chapitre 3/12 du livre '{title}' de {author}"
- La table des matières (si disponible) pour garder la vision d'ensemble

### 2.4 Synthèse finale (merge)

La note finale est générée avec un prompt dédié qui reçoit :
- Toutes les sous-notes concaténées (dans le format template)
- Les métadonnées source (titre, auteur, type)
- La template de génération (même schéma de sortie)

Le LLM fusionne : tags (dédup, garder les plus fréquents), key ideas (consolider),
punchlines (garder les meilleures mot pour mot), body (synthèse structurée).

---

## 3. Configuration

### 3.1 Presets — deux axes indépendants

```yaml
# user.yaml
provider_mode: local       # local | api
quality_preset: balanced   # quick | balanced | quality
```

**`provider_mode`** détermine les contraintes techniques (context window, coût token, vitesse).
**`quality_preset`** détermine le niveau de détail et le nombre de passes.

| Preset | Stratégie par défaut | Chunk size (tokens) | Web search |
|--------|---------------------|---------------------|------------|
| quick | map-reduce | 10000 | non |
| balanced | auto (TOC → map-reduce) | 5000 | non |
| quality | toc-first | 3000 | optionnel |

### 3.2 Paramètres system.yaml

```yaml
# system.yaml
llm:
  max_retries: 2
  large_format_threshold_tokens: 50000  # existant
  context_window: null                  # auto-detect si null
  direct_threshold_ratio: 0.6          # ratio context window pour multi-pass

note_generation:
  strategy: auto                        # auto | direct | toc | map-reduce | web-search
  merge_chunk_size: 5000               # tokens par sous-section en mode map-reduce
  max_sub_notes: 30                    # limite de sécurité
  web_search_summary: false            # chercher un résumé existant avant de synthétiser
  cache_intermediate: false            # persister les sous-notes en debug
```

### 3.3 Auto-détection de la context window

Ordre de résolution :
1. `system.yaml > llm.context_window` (override explicite)
2. Ollama : `GET /api/show` → `model_info.context_length`
3. Mapping hardcodé pour providers API connus (Claude, GPT-4, etc.)
4. Fallback : 8192 tokens (conservateur)

---

## 4. Composants à créer/modifier

### 4.1 Nouveaux

| Composant | Rôle |
|-----------|------|
| `tools/text/synthesize.py` | Orchestrateur multi-pass : detect strategy, split, sous-générations, merge |
| `infrastructure/llm_provider.py::get_context_window()` | Auto-détection context window |
| `config/templates/generation/merge.yaml` | Template de prompt pour la synthèse finale (merge des sous-notes) |
| `config/templates/generation/sub_note.yaml` | Template enrichie pour sous-génération (contexte chapitre) |

### 4.2 Modifiés

| Composant | Modification |
|-----------|-------------|
| `tools/vault/generate_note_from_source.py` | Appeler `synthesize()` si source > seuil, sinon pipeline direct |
| `core/config.py` | Ajouter `NoteGenerationConfig`, `context_window`, `provider_mode`, `quality_preset` |
| `config/system.yaml` | Section `note_generation` |
| `infrastructure/llm_provider.py` | Ajouter `get_context_window()`, supporter Ollama/OpenAI providers |

### 4.3 Inchangés

Le reste du pipeline (chunking, embedding, search, API/CLI/MCP surfaces) n'est pas impacté.
La cascade est interne à la génération de note.

---

## 5. Notes intermédiaires — cycle de vie

```
Sous-note générée
    ↓
Stockée en mémoire (liste de NoteContentInput)
    ↓
Envoyée en contexte pour la synthèse finale
    ↓
Supprimée après finalisation réussie

Si cache_intermediate: true →
    Persistée dans egovault-user/cache/generation/{source_uid}/
    Videable via purge --cache
```

Les sous-notes ne sont **jamais** insérées en DB ni embedées. Seule la note finale l'est.

---

## 6. Estimation des tokens par stratégie

Pour un livre de 500 pages (~200k tokens source) :

| Stratégie | Sous-calls | Tokens input total | Tokens output estimé |
|-----------|-----------|-------------------|---------------------|
| direct | 1 | 200k (échoue) | — |
| map-reduce (10k chunks) | 20 + 1 merge | ~200k + ~20k merge | ~20k |
| toc (15 chapitres) | 15 + 1 merge | ~200k + ~15k merge | ~15k |
| web-search + merge | 1 fetch + 1 call | ~5k | ~2k |

Le coût est proportionnel à la taille source dans tous les cas sauf web-search.

---

## 7. Hors scope V1

- **Enrichissement web** (LLM utilise le web pour diriger l'axe) — V2, option user
- **Chunking structure-aware** pour le search — sujet séparé
- **Semantic cache** — spec future existante
- **Ollama/OpenAI provider implémentation** — pré-requis séparé (actuellement seul Claude est implémenté)
- **Presets auto-sélectionnés** (détection automatique local/api) — V2

---

## 8. Dépendances

- **Provider Ollama/OpenAI dans llm_provider.py** — nécessaire pour que le mode `local` fonctionne.
  Actuellement seul Claude est implémenté. Peut être livré en parallèle ou avant.
- **Estimation de tokens** — besoin d'un tokenizer rapide (tiktoken pour API, ou comptage approximatif
  par mots ÷ 0.75). Pas besoin d'être exact, c'est pour le seuil de déclenchement.

---

## 9. Questions ouvertes

1. **Token counting** — tiktoken (précis, dépendance) ou heuristique `len(text.split()) / 0.75` (approximatif, zéro dépendance) ?
2. **Limite de sous-notes** — `max_sub_notes: 30` est-il suffisant pour les très gros livres ?
3. **Template sub_note vs template standard** — est-ce qu'on crée une template séparée pour les sous-notes, ou on réutilise standard.yaml avec un system_prompt enrichi dynamiquement ?
