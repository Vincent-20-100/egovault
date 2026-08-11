# Sentinel — Projet annexe (émergé d'EgoVault)

**Date d'émergence :** 2026-08-10
**Statut :** Idée validée — pas de spec, pas de plan. À démarrer après EgoVault tier-1.

---

## Vision en une phrase

Un moteur de veille open source automatique : surveille des corpus publics (GitHub, ArXiv,
HuggingFace, RSS…), filtre par pipeline multi-étapes sans exploser les coûts LLM, et génère
des notes de veille structurées que l'humain reçoit ou retrouve dans son contexte de travail.

---

## Le problème

La veille technique sur de grands corpus (500-1000+ repos GitHub, papiers ArXiv, modèles HF)
est soit manuelle et coûteuse en temps, soit automatisée mais bruyante. Les solutions existantes
(awesome lists, newsletters, RSS) ne sont pas personnalisées et n'intègrent pas le contexte
du projet en cours.

---

## Pipeline (entonnoir 3 étapes)

```
Source brute (ex: 1000 repos GitHub)
    ↓
Stage 1 — Metadata filter (gratuit, API seule, 0 LLM)
  stars > N, pushed > last_run, readme_size > 500B,
  description non nulle, topics match, dédup vs. déjà indexé
  → ~150 candidats

Stage 2 — Embed + semantic rank (Ollama local, 0 coût API)
  embed description + premiers 500 chars README/abstract
  cosine similarity vs. profil utilisateur / projet en cours
  → top 20-30

Stage 3 — LLM note generation (coûteux, uniquement sur le top)
  lit le document complet (README, abstract, model card…)
  génère : usecase concret pour le projet, tips, pourquoi pertinent
  → 3-8 notes par run si pertinent, 0 si rien de nouveau
```

**Principe clé :** le LLM ne cherche pas — il rédige sur un corpus déjà qualifié par deux
filtres sans IA. Son coût est justifié uniquement à cette étape finale.

---

## Sources généralisables

La structure est identique quelle que soit la source :

| Source | Signal de fraîcheur | Metadata de ranking | Extracteur |
|--------|--------------------|--------------------|-----------|
| GitHub repos | `pushed_at` | stars, forks, topics | GitHub Search API |
| ArXiv papers | `published` | citations, category | ArXiv API |
| HuggingFace models | `lastModified` | downloads, likes | HF Hub API |
| Awesome lists | commit diff | position dans la liste | GitHub Contents API |
| RSS / blogs | `pubdate` | — | feedparser |

---

## Output

- **Notes de veille structurées** — même format que les notes EgoVault (Markdown, tags, uid)
- **Mail digest** — hebdomadaire, uniquement si nouvelles notes générées
- **Injection contexte projet** — SessionStart hook ou MCP tool `get_veille(project, since)` ;
  les notes tombent dans le contexte Claude comme un collaborateur qui a fait sa veille la nuit

---

## Lien avec EgoVault

| EgoVault | Sentinel |
|----------|----------|
| Knowledge personnelle (ce que TU as lu et annoté) | Veille publique (ce qui existe et mérite attention) |
| Ingestion manuelle, pull | Ingestion automatique, push |
| Permanence, accumulation | TTL + refresh incrémental |
| "Qu'est-ce que je sais ?" | "Qu'est-ce que je devrais regarder ?" |

Les deux MCP servers coexistent dans Claude Desktop. Les notes Sentinel peuvent être
importées dans EgoVault si l'utilisateur veut les conserver dans sa knowledge personnelle.

---

## Stack envisagé

Python · httpx async · Ollama (embeddings) · SQLite + sqlite-vec · FastMCP · feedparser
· PyGitHub ou GitHub REST API directe · scheduler (APScheduler ou cron)

Réutilise ~60% de l'infrastructure EgoVault (chunking, embedding, sqlite-vec, MCP pattern).

---

## Ce qu'il reste à décider

- Standalone repo ou extension EgoVault (`ingest_github_topic` source type) ?
- Profil utilisateur : fichier YAML statique ou tiré des notes EgoVault (méta) ?
- Notification : email SMTP simple ou webhook (Slack, ntfy…) ?
- Seuil de génération de note : score sémantique seul ou combiné avec signal metadata ?
