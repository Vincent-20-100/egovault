# EgoVault — État de l'Art & Idées d'Amélioration

> **Registre d'intelligence compétitive.** Centralise les projets analysés, patterns
> identifiés, et idées concrètes à intégrer dans EgoVault.
> Mis à jour à chaque session de veille. Dernière mise à jour : 2026-05-02.

---

## Projets analysés

### Tier 1 — Concurrents directs / overlap significatif

#### CocoIndex (`cocoindex-io/cocoindex`)

**Ce que c'est :** Framework Python/Rust pour indexation incrémentale. Moteur déclaratif
`Target = F(Source)` — ne retraite que le delta quand les sources changent.

**Pertinence pour EgoVault :** Très haute. Leur mémoïsation par hash de contenu est
exactement ce qu'il faudrait pour `compile()`. Quand une source est modifiée, seuls les
chunks affectés sont re-embeddés — 10x réduction de coût revendiquée.

**Idées à retenir :**
- Invalidation fine-grained par hash de contenu (pas de re-processing si input inchangé)
- Lineage end-to-end : chaque embedding trace son chunk source exact
- Sub-second freshness vs batch quotidien — pertinent si on veut du live sync
- Isolation des erreurs : un chunk qui crash ne bloque pas le reste

**Ce qu'ils font mieux :** Scale (pétaoctets), Rust core, 8 types de sources, 6 types de stores.
**Ce qu'on fait mieux :** Architecture hexagonale propre, MCP natif, zero vendor lock-in.

---

#### SurfSense (`MODSetter/SurfSense`) — 14.1k stars

**Ce que c'est :** Alternative open source à NotebookLM. 27+ connecteurs (Google Drive,
Slack, Notion, GitHub...), search hybride sémantique + full text, génération de podcasts,
slides, rapports PDF/DOCX/LaTeX.

**Pertinence pour EgoVault :** Benchmark feature. C'est notre horizon en termes de
fonctionnalités, mais leur architecture est monolithique (FastAPI + LangChain).

**Idées à retenir :**
- Search hybride : sémantique + full text avec Reciprocal Rank Fusion
- Hierarchical indices pour navigation dans de gros corpus
- AI-powered file sorting (classification automatique des sources ingérées)
- Outputs variés : podcast TTS, slides éditables, rapports multi-format
- Multiplayer avec RBAC (Owner/Admin/Editor/Viewer)

**Ce qu'ils font mieux :** 27 connecteurs, 50+ formats, multiplayer, outputs variés.
**Ce qu'on fait mieux :** Architecture clean, MCP natif, tier 0 sans LLM, privacy by design.

---

#### claude-obsidian (`AgriciDaniel/claude-obsidian`)

**Ce que c'est :** Wiki persistant implémentant le pattern LLM Wiki d'Andrej Karpathy.
Claude ingère des sources → 8-15 pages wiki auto-organisées → cross-refs → lint automatique.

**Pertinence pour EgoVault :** Valide notre vision Knowledge Compiler à 100%. C'est
exactement le cycle ingest → compile → query avec citations qu'on vise.

**Idées à retenir :**
- Cycle 3 opérations : Ingest / Query / Lint — simple et complet
- Hot cache (`wiki/hot.md`) : résumé du contexte récent entre sessions
- Lint automatique : détection de pages orphelines, liens morts, contradictions, gaps sémantiques
- `/autoresearch` : 3 rounds de recherche web avec gap-filling automatique
- Contradiction flagging : callouts marquant les claims inconsistants avec attribution source
- 8-15 pages par source ingérée — granularité plus fine que notre 1 note par source

**Ce qu'ils font mieux :** Déjà fonctionnel, lint automatique, hot cache entre sessions.
**Ce qu'on fait mieux :** Architecture propre (vs scripts Obsidian), tiered approach (tier 0
sans LLM), pipeline d'ingestion robuste (7 extracteurs), MCP server complet.

---

#### second-brain-agent (`flepied/second-brain-agent`)

**Ce que c'est :** Pipeline markdown → chunks → ChromaDB → MCP server. Inspiré de la
méthode "Building a Second Brain" de Tiago Forte.

**Pertinence pour EgoVault :** Validation du pattern MCP + vector store pour PKM.

**Idées à retenir :**
- Classification automatique par domaine (work/personal/topic)
- MCP server minimaliste avec 4 tools seulement (search, count, domains, recent)
- Monitoring de fichiers via systemd (auto-indexation au changement)
- CLI `qa.py` pour search sémantique avec attribution source

**Ce qu'ils font mieux :** Simplicité extrême.
**Ce qu'on fait mieux :** Tout le reste (multi-format, notes structurées, workflow unifié).

---

### Tier 2 — Inspirations architecturales

#### Hermes Agent (`NousResearch/hermes-agent`)

**Ce que c'est :** Agent AI auto-améliorant par Nous Research. Crée ses propres skills,
maintient une mémoire persistante, profile l'utilisateur.

**Pertinence pour EgoVault :** Pattern mémoire à 3 niveaux très pertinent.

**Idées à retenir :**
- **Mémoire à 3 niveaux** : session (FTS5 + summarization), profil persistant (préférences
  utilisateur), mémoire procédurale (skills réutilisables)
- **Periodic nudges** pour consolider la mémoire → pattern pour notre `compile()` automatique
- **Autonomous skill creation** : l'agent génère des procédures réutilisables après
  avoir complété une tâche complexe
- **Self-improving skills** : les compétences se raffinent à l'usage
- **agentskills.io** : standard ouvert pour skills partageables entre agents
- 40+ tools built-in + MCP extensible
- Multi-plateforme (Telegram, Discord, Slack, WhatsApp, Signal, email)

---

#### GraphRAG (`thu-vu92/graphRAG`)

**Ce que c'est :** RAG basé sur un knowledge graph avec détection de communautés.
Extraction d'entités typées → clustering Louvain → synthèse par communauté.

**Pertinence pour EgoVault :** Pattern pour notre tier 2 (notes compilées cross-source).

**Idées à retenir :**
- **Communautés sémantiques** : au lieu de top-K chunks, grouper les entités en clusters
  thématiques puis synthétiser par communauté
- **Multi-hop reasoning** : traverser le graph pour connecter des concepts distants
- **Entity resolution** : fusion des entités identiques provenant de sources différentes
- **Visualisation interactive** : graph D3.js filtrable par type d'entité
- Ontologie prédéfinie + validation Pydantic des relations extraites

---

#### Autocontext (`greyhaven-ai/autocontext`)

**Ce que c'est :** Framework récursif d'auto-amélioration d'agents. 5 rôles coopératifs
(competitor/analyst/coach/architect/curator), knowledge gating.

**Pertinence pour EgoVault :** Pattern curator pour filtrer ce qui mérite d'être compilé.

**Idées à retenir :**
- **5 rôles** : Competitor (propose), Analyst (explique), Coach (met à jour le playbook),
  Architect (suggère des changements structurels), Curator (gate la persistance)
- **Knowledge gating** : le curator décide ce qui persiste — pas tout, seulement ce qui
  améliore. Pattern directement applicable au librarian
- **Playbook accumulatif** : `playbook.md` accumule les leçons apprises, lu automatiquement
  par les runs suivants
- **Rollback des solutions faibles** : seules les améliorations effectives persistent
- **11 familles de scénarios** dont investigations avec chaînes de preuves

---

#### Feynman (`getcompanion-ai/feynman`)

**Ce que c'est :** Agent de recherche académique. 4 agents spécialisés : Researcher,
Reviewer, Writer, Verifier.

**Pertinence pour EgoVault :** Modèle pour nos futurs agents pré-packagés.

**Idées à retenir :**
- **4 agents spécialisés** avec rôles clairs et séparés
- **Source grounding** : chaque output lié à papers/docs/repos avec URLs directes
- **Session indexing** : rappel indexé des sessions de recherche précédentes
- **Simulated peer review** avec feedback severity-graded
- **Skills format** : fichiers Markdown d'instructions synchronisés localement

---

### Tier 3 — Outils complémentaires

#### claude-mem (`thedotmack/claude-mem`)

**Ce que c'est :** Plugin Claude Code pour capture automatique de sessions + injection
de contexte dans les futures sessions.

**Idées à retenir :**
- **Progressive disclosure en 3 couches** : search → index compact (~50-100 tokens),
  timeline → contexte chronologique, get_observations → détails complets (~500-1000 tokens).
  Pattern directement applicable à notre `curate()` tier 0
- **5 lifecycle hooks** (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd)
- SQLite + Chroma hybride (FTS5 + sémantique)
- Tags `<private>` pour exclure du contenu sensible

---

#### Synapthema (`Matthieu5555/Synapthema`)

**Ce que c'est :** Pipeline PDF → cours interactif HTML avec spaced repetition,
concept mapping, Bloom taxonomy.

**Idées à retenir :**
- **Deep reading phase** : extraction de concepts/entités par LLM AVANT la synthèse.
  Phase intermédiaire qui améliore la qualité. Applicable à notre ingest
- **Consolidation cross-chapitre** : entity resolution + tri topologique des concepts
- **Checkpoints resumables** : si crash au chapitre 8/15, reprise au 8. Pertinent pour
  notre large source synthesis
- **9 types d'éléments** mappés sur Bloom taxonomy (slides, flashcards, quizzes, concept
  maps, diagrams, self-explanation prompts)
- **Type detection** : classification automatique du document (quantitatif, narratif,
  procédural) pour adapter les templates

---

#### deepagents (`langchain-ai/deepagents`)

**Ce que c'est :** Agent harness LangGraph "batteries-included". Planning tool, filesystem
ops, shell execution, sub-agents, auto-summarize.

**Idées à retenir :**
- Auto-summarize des conversations longues pour efficacité token
- Sub-agent delegation avec contextes isolés
- LangGraph compiled graph pour streaming + persistence + checkpointing

---

## Patterns transversaux identifiés

### 1. La mémoire à 3 niveaux est universelle

| Projet | Niveau 1 (volatile) | Niveau 2 (structuré) | Niveau 3 (compilé) |
|--------|--------------------|--------------------|-------------------|
| **EgoVault** | Raw chunks | Notes structurées | Curated context |
| **Hermes** | Session memory | User profiles | Procedural skills |
| **claude-mem** | Index compact | Timeline | Full observations |
| **claude-obsidian** | Hot cache | Wiki pages | Cross-refs + lint |

**Conclusion :** Notre architecture 3-tier (raw → compiled → curated) est le bon modèle.
La convergence de projets indépendants vers le même pattern le valide.

### 2. La compilation incrémentale est le game-changer

CocoIndex, claude-obsidian, et Hermes convergent vers la même idée : ne pas tout
retraiter à chaque changement. CocoIndex le fait avec du hash-based memoization,
claude-obsidian avec des cross-refs incrémentales, Hermes avec des skills auto-améliorants.

**Pour EgoVault :** `compile()` doit tracker les hashes des sources qui ont contribué
à une note compilée. Si aucune source n'a changé, pas de re-compilation.

### 3. Le lint/audit automatique est un différenciateur

claude-obsidian a un `/lint` qui détecte : pages orphelines, liens morts, contradictions,
gaps sémantiques. Aucun autre projet ne fait ça.

**Pour EgoVault :** Un tool `audit_vault()` qui détecte les notes sans source, les sources
sans chunks, les contradictions entre notes, les tags orphelins. Tier 0 déterministe.

### 4. Progressive disclosure pour l'économie de tokens

claude-mem montre que le retrieval en 3 couches (index → contexte → détails) est plus
efficace que le top-K brut. SurfSense utilise des hierarchical indices.

**Pour EgoVault :** `curate()` tier 0 devrait retourner d'abord un index compact (titres +
scores), puis le détail à la demande. Pas tout d'un coup.

### 5. Search hybride est le standard

SurfSense (sémantique + full text + RRF), GraphRAG (graph + communautés), notre spec
reranking (cosine + cross-encoder). Le vector-only est dépassé.

**Pour EgoVault :** Implémenter la spec reranking existante, puis ajouter FTS5 (déjà
dans SQLite) pour search hybride. Reciprocal Rank Fusion pour combiner les scores.

---

## Idées concrètes pour EgoVault (par priorité)

### Haute priorité (renforce le core)

| Idée | Source | Impact | Effort |
|------|--------|--------|--------|
| `curate()` tier 0 — progressive disclosure (index → détails) | claude-mem, vision doc | Différenciateur majeur | Moyen |
| `curate()` tier 1 — LLM synthesis isolée | Vision doc, Hermes | Librarian fonctionnel | Moyen |
| Search hybride FTS5 + sémantique | SurfSense, spec reranking | Qualité retrieval | Moyen |
| Reranking cross-encoder | Spec existante | Qualité retrieval | Faible (spec prête) |
| Multi-source note synthesis | NotebookLM, claude-obsidian | Core feature manquant | Élevé |
| Hash-based compile invalidation | CocoIndex | Efficacité compilation | Moyen |

### Moyenne priorité (enrichit l'expérience)

| Idée | Source | Impact | Effort |
|------|--------|--------|--------|
| Vault audit/lint tool | claude-obsidian | Qualité du vault | Moyen |
| Deep reading phase avant synthèse | Synapthema | Qualité notes | Moyen |
| Entity resolution cross-source | GraphRAG, Synapthema | Liens entre sources | Élevé |
| Contradiction detection entre notes | claude-obsidian, GraphRAG | Fiabilité | Élevé |
| Citations sourcées dans les notes | NotebookLM, Feynman | Traçabilité | Faible |
| Classification automatique des sources | SurfSense | UX ingestion | Moyen |
| Confidence scores + temporal decay | Vision doc | Qualité retrieval | Moyen |

### Future (horizon lointain)

| Idée | Source | Impact | Effort |
|------|--------|--------|--------|
| Knowledge gating (curator pattern) | Autocontext | Auto-amélioration | Élevé |
| Agents pré-packagés (researcher/reviewer/writer) | Feynman, Hermes | Écosystème | Élevé |
| Self-improving skills | Hermes | Auto-amélioration | Très élevé |
| Graph visualization interactive | GraphRAG | UX exploration | Moyen |
| Podcast generation | SurfSense, podcastfy | Output alternatif | Moyen |
| Hot cache entre sessions | claude-obsidian | Continuité | Faible |
| Connecteurs externes (Drive, Slack, Notion) | SurfSense | Scale sources | Élevé |
| Multiplayer RBAC | SurfSense | Multi-user | Très élevé |

---

## Veille techno : optimisation inférence

### TurboQuant (Google, ICLR 2026)

Compression du KV cache LLM à 3 bits (keys) + 2 bits (values) sans perte de qualité.
Jusqu'à 8x de performance sur H100, 2x d'extension de contexte.

**Impact EgoVault :** aucun changement de code — optimisation d'infra (vLLM, Ollama).
Les users self-hosted avec grosses sources bénéficient d'une context window plus grande.

---

## Projets étoilés hors scope EgoVault

| Projet | Domaine | Pourquoi hors scope |
|--------|---------|-------------------|
| TradingAgents | Finance/trading | Domaine différent |
| punkpeye/awesome-mcp-servers | Liste de serveurs MCP | Référence, pas inspiration |
| yanshengjia/ml-road | Ressources ML | Éducatif |
| PaulLockett/CodeSignal_Practice | Coding practice | Éducatif |
| JuliusBrussee/caveman | Token reduction | Optimisation Claude Code, pas PKM |
| guipsamora/pandas_exercises | Pandas practice | Éducatif |
| Sapthak101/Forage-BCG | Data science program | Éducatif |
| Panniantong/Agent-Reach | Internet research agent | Trop générique |
| safishamsi/graphify | Code analysis | Domaine différent |
| GuillaumeDesforges/claude-ai-project-starter | Template projet | Template, pas inspiration |
| garrytan/gstack | Claude Code setup | Setup, pas architecture |
| datalab-to/chandra | OCR | Feature spécifique, pas architecture |
| PlamenStilyianov/FinMathematics | Finance | Domaine différent |
| 666ghj/MiroFish | Swarm intelligence | Domaine différent |
| ayusha1107/ebooks | Ebooks | Collection |
| affaan-m/everything-claude-code | Agent harness | Meta-outil |
| Nixtla/mlforecast | Time series | Domaine différent |
| opendataloader-pdf | PDF parser | Potentiellement utile pour notre extracteur PDF |
| souzatharsis/podcastfy | Content → audio | Idée output audio future |
