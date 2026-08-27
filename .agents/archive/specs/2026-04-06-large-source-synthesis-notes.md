# Brainstorm : Synthèse de grosses sources

**Date :** 2026-04-06
**Participants :** Vincent + Claude
**Statut :** Validé → passer en spec

---

## Problème

Quand une source (PDF livre, long transcript, grosse page web) dépasse la context window
du LLM, comment générer une note synthétique de qualité (résumé, tags, key ideas, punchlines) ?

**Deux problèmes distincts identifiés :**
1. **Chunking & embedding** de la source — problème d'indexation/search (séparé, pas traité ici)
2. **Génération de note synthétique** — problème de summarization quand l'input est trop grand

Le chunking bénéficie déjà du pipeline PDF → Markdown (structure, titres = frontières naturelles).
La synthèse est le vrai problème non résolu.

---

## Décisions validées

### A. Cascade de stratégies avec fallback

```
Web search résumé existant (optionnel, choix user)
    ↓ fallback ou choix user
TOC + synthèse par chapitre (si structure détectée)
    ↓ fallback si pas de TOC
Map-Reduce brut (split en sections → résumé de chaque)
    ↓ dans tous les cas
Résumé final des pré-résumés
```

Chaque niveau est autonome. Le système se dégrade gracieusement.

### B. Template de note réutilisée à chaque sous-génération

Insight clé : chaque sous-résumé (par chapitre ou par chunk) est généré avec la même
template que la note finale (tags, résumé, key ideas, punchlines mot pour mot, etc.).

Avantages :
- La synthèse finale est un **merge/dédup** plutôt qu'une régénération from scratch
- Les tags récurrents remontent naturellement (fréquence = signal de pertinence)
- Les punchlines mot pour mot sont préservées au lieu d'être paraphrasées
- Moins de perte d'info entre les niveaux

Le prompt de sous-génération inclut le contexte ("chapitre 3/12 d'un livre sur X")
pour éviter des tags/résumés trop locaux. La TOC (si disponible) aide ici.

### C. Seuil multi-pass auto-détecté

- Si source < ~60% de la context window du modèle → génération directe (comme aujourd'hui)
- Si source > 60% → mode multi-pass (cascade ci-dessus)
- Context window auto-détecté : Ollama API (`ollama show`), mapping hardcodé pour API providers
- Fallback : paramètre yaml `llm.context_window` overrideable par l'user
- Le ratio (60%) est aussi configurable : `note_generation.direct_threshold_ratio: 0.6`

### D. Notes intermédiaires — cache temporaire

3 niveaux :
- **Default :** en mémoire, supprimé après finalisation réussie
- **Debug :** persisté dans `egovault-user/cache/generation/`, videable d'un coup
  (`purge --cache` ou équivalent)
- **Futur :** à brancher sur un système de cache plus général (semantic cache dans specs future)

Pas de stockage long terme par défaut — redondant avec la source brute et sans usage spécifique.

### E. Presets — deux axes orthogonaux

Qualité et mode provider sont **indépendants** :

```yaml
# user.yaml
provider_mode: local      # local | api
quality_preset: balanced   # quick | balanced | quality
```

Un user local avec grosse machine peut vouloir `quality` sans clé API.
Un user API peut vouloir `quick` pour minimiser les coûts.

| Combinaison | Comportement |
|-------------|-------------|
| local + quick | Gros chunks, map-reduce direct, pas de web search |
| local + quality | Petits chunks, TOC-first, plus de passes |
| api + quick | Gros chunks, minimiser les calls API |
| api + quality | Petits chunks, TOC-first, web search optionnel |

Chaque paramètre individuel reste overrideable pour les power users.
Le preset est un bundle de defaults.

### F. Web enrichissement — option non-prioritaire

- Proposer au LLM d'utiliser le web ou son contexte pour enrichir/diriger l'axe général
- Tout en option user
- Second temps, pas dans le V1

---

## Questions résolues

| Question | Réponse |
|----------|---------|
| Seuil multi-pass ? | Auto-detect context window du modèle, ratio ~60% |
| Notes intermédiaires ? | Cache mémoire, debug persisté, pas de long-term par défaut |
| Presets ? | 2 axes indépendants : provider_mode × quality_preset |
| Template sous-génération ? | Même template que la note finale |
| Web search ? | Option user, non-prioritaire, V2 |

---

## Hors scope (sujets identifiés mais séparés)

- **Chunking structure-aware post-markdown** — optimisation du search, pas de la synthèse
- **Semantic cache** — spec future existante (`2026-03-28-semantic-cache-design.md`)
- **Search quality / reranking** — spec future existante (`2026-03-28-reranking-design.md`)
