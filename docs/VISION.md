# EgoVault — Vision & Strategic Analysis

**Date:** 2026-03-31
**Context:** Strategic review during VaultContext brainstorm — stepping back before committing to architecture work.

---

## What EgoVault is

A **second cerveau personnel** qui :
- Ingère n'importe quoi (YouTube, audio, PDF, bientôt texte/web)
- Découpe, embedde, indexe automatiquement
- Permet de chercher sémantiquement dans tout ton savoir
- Génère des notes structurées via LLM
- Synchronise avec Obsidian
- Accessible via CLI, API, et MCP (donc directement dans Claude)

## Est-ce que ça existe déjà ?

Oui et non.

**Ce qui existe :**
- Obsidian + plugins (Copilot, Smart Connections) — recherche sémantique sur tes notes
- Mem.ai, Khoj, Rewind — capture automatique + search
- RAG pipelines (LangChain, LlamaIndex) — mais ce sont des frameworks, pas des produits

**Ce qui n'existe PAS dans cette combinaison :**
- **Local-first + multi-source + MCP.** Personne ne fait "je donne une URL YouTube et 3 minutes plus tard j'ai une note Obsidian cherchable sémantiquement, et mon assistant Claude peut fouiller dedans via MCP."
- Le MCP est ton killer feature. L'utilisateur parle à Claude, Claude cherche dans son vault. C'est du **context augmentation** pour LLM, pas juste une app de notes.

## Potentiel de buzz ?

**Oui, si tu frames bien.** Le marché est chaud :
- "Second brain" est un mouvement (Tiago Forte, Building a Second Brain — des millions de followers)
- Obsidian a une communauté massive et passionnée de devs/power users
- MCP est nouveau et les gens cherchent des use cases concrets
- Local-first est un argument fort (vie privée, pas d'abonnement)

**Le pitch qui buzz :** "J'ai construit un outil qui transforme mes vidéos YouTube, podcasts et PDFs en un knowledge base cherchable, et mon Claude peut y accéder en temps réel."

**Où poster :** r/ObsidianMD, r/selfhosted, Hacker News (Show HN), Twitter dev/AI, la communauté MCP Discord.

**Ce qui fera la différence :** une démo vidéo de 2 minutes. "Je colle un lien YouTube → 30 secondes plus tard → je demande à Claude une question → il me répond avec mes propres notes." Si ça marche smooth, ça buzz.

## L'architecture justifie-t-elle le temps investi ?

**Oui, pour trois raisons :**

1. **Le buzz attire des contributeurs.** Si le code est un spaghetti, personne ne fork. Si c'est propre et documenté, les gens veulent contribuer. Ton architecture hexagonale + VaultContext + specs = un repo qui inspire confiance.

2. **L'extensibilité est ton moat.** Si quelqu'un veut ajouter "ingest Notion" ou "ingest Kindle highlights", le registry pattern fait que c'est un fichier à écrire. C'est ce qui transforme un side project en écosystème.

3. **C'est formateur pour toi.** Tu l'as dit toi-même. Et un repo public bien architecturé avec des specs documentées, c'est un portfolio qui parle.

## Reusable template

EgoVault is designed to become a **reference template** for future ambitious projects.
The architecture, behavior files (CLAUDE.md, workflow, audit spec), and project structure
should be reusable as a clean starting point for any vibe-coded project. Every structural
decision must be made with this portability in mind.

## North star

Chaque décision doit rapprocher du moment où tu peux enregistrer la démo vidéo de 2 minutes. VaultContext → unified workflow → ingest_text → **démo**. C'est la north star.
