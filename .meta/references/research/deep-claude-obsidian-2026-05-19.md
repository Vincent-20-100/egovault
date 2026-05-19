---
mode: deep
date: 2026-05-19
slug: claude-obsidian
url: https://github.com/AgriciDaniel/claude-obsidian
angle: compare to EgoVault Knowledge Compiler + Librarian/curate vision; is this the Karpathy LLM Wiki pattern; what to borrow/reject
status: active
---

# Deep — AgriciDaniel/claude-obsidian

## 1. Fingerprint

- **Primary lang:** Shell (orchestration); Python helpers; Markdown is the data plane
- **Repo type:** Claude Code plugin + Obsidian vault (knowledge wiki system)
- **File count:** 158
- **License:** MIT
- **Stars / last commit:** unknown (`gh` unavailable in sandbox)
- **Pitch:** "Persistent, compounding wiki vault based on Karpathy's LLM Wiki" — Claude + Obsidian knowledge companion.

## 2. Structure map

```
commands/   wiki.md autoresearch.md save.md canvas.md       ← user entry points
skills/     wiki wiki-ingest wiki-query wiki-lint wiki-fold  ← the engine
            autoresearch canvas defuddle obsidian-markdown obsidian-bases save
agents/     wiki-ingest.md  wiki-lint.md                     ← subagent defs
_templates/ source concept entity question comparison       ← typed page schemas
wiki/       sources/ concepts/ entities/ questions/ comparisons/ folds/ meta/
            index.md hot.md log.md overview.md Wiki Map.canvas
.raw/       immutable read-only source layer
scripts/    boundary-score.py  tiling-check.py               ← deterministic guards
.vault-meta/ address-counter.txt tiling-thresholds.json     ← "dragonscale" addressing
hooks/      hooks.json   CLAUDE.md AGENTS.md GEMINI.md WIKI.md
```

## 3. Key findings

### 3.1 Extension points
- **Skill-per-operation** (`skills/wiki-ingest`, `wiki-query`, `wiki-lint`,
  `wiki-fold`): each wiki operation is an isolated skill — same decomposition
  EgoVault uses for tools. Adding an operation = adding a skill. *Why it
  matters:* mirrors EgoVault's tool granularity; validates the architecture.
- **Typed page templates** (`_templates/{source,concept,entity,question,
  comparison}.md`): flat-YAML frontmatter, universal fields (`type,title,
  created,updated,tags,status,related,sources`) + type-specific. *Why:*
  directly comparable to EgoVault `note_type` taxonomy (G3) but file-template
  driven rather than DB-schema driven.

### 3.2 Safety & governance
- **`.raw/` immutable source layer** + append-only `wiki/log.md` (newest on
  top, timestamps every op). *Why:* same provenance discipline as EgoVault
  (sources never mutated; audit trail). Confirms the raw→compiled split.
- **Deterministic guards** `scripts/boundary-score.py`, `tiling-check.py`,
  frontmatter schema validation, git commits. *Why:* the LLM writes, but
  structural invariants are checked deterministically — EgoVault's
  "deterministic tier-0, LLM accelerator" principle, independently arrived at.

### 3.3 Documentation quality
- Strong: `WIKI.md` is a precise spec of ingest/query/compound mechanics;
  `CLAUDE.md`/`AGENTS.md`/`GEMINI.md` triple harness docs; install guide + PDF.
  *Why:* the operational contract is explicit enough to reimplement — useful
  as a reference spec for EgoVault's own librarian docs.

### 3.4 Developer workflow
- `commands/wiki.md` + `bin/setup-vault.sh` + `hooks/hooks.json`: zero-DB,
  pure-markdown + git; Obsidian renders the graph. *Why:* contrast — EgoVault
  carries SQLite+sqlite-vec; this proves a viable **embedding-free** path.

### 3.5 Distinctive patterns
- **Token-frugal progressive retrieval (the key idea):** query precedence is
  `hot.md` (~500 tok recent context) → `index.md` (~1000 tok master catalog)
  → 3–5 domain/entity pages (100–300 tok each) → synthesize. *Why it matters
  enormously:* this is a **deterministic, embedding-free `curate()` tier-0**.
  EgoVault finding E showed cosine ranking is weak/imprecise on French; a
  hot+index+typed-pages precedence sidesteps embedding quality entirely for
  the compiled (notes) tier.
- **Source fan-out:** one source → 8–15 typed pages; batch mode defers
  cross-referencing until all sources processed. *Why:* concrete model for an
  EgoVault multi-note generation + deferred linking workflow.
- **Compounding > retrieving:** synthesis already reflects all prior sources;
  contradictions flagged inline; `overview.md` is a maintained big-picture.
  *Why:* this is exactly the EgoVault VISION thesis ("RAG retrieves then
  forgets; a compiler accumulates"), shipped.
- **Reject:** six hardcoded "modes" (Website/GitHub/Business/Personal/
  Research/Book) with fixed sub-folder taxonomies. *Why:* violates EgoVault
  G3 (config-driven, not code-driven taxonomy); over-engineered vs EgoVault's
  user-configurable `taxonomy:` block.

## 4. Tiered recommendations

- **USE AS-IS:** (none) — different stack (markdown/git vs SQLite/MCP/API);
  no component drops in unchanged.
- **EXTRACT PARTS:** the **hot.md + index.md + typed-page precedence** as a
  deterministic `curate()` tier-0 strategy for the *notes* tier — a
  `hot`/`index` materialized cache rebuilt on note write, queried before
  (or instead of) cosine search. Rationale: direct mitigation of finding E
  (FR cosine imprecision) without an embedding-model change; aligns with the
  already-specced curate() escalation model.
- **BORROW CONCEPTS:** append-only `log.md` op-journal; `.raw/` immutability
  naming; one-source→N-typed-pages fan-out + deferred cross-ref (informs the
  large-source-synthesis spec); inline contradiction callouts during synthesis
  (a tier-1 curate() / note-gen quality feature).
- **INSPIRATION:** `WIKI.md` as the shape of a precise, reimplementable
  librarian operational spec; Obsidian-graph-as-UI as a zero-build
  visualization story for the EgoVault vault (`egovault-user/vault/`).
- **REJECT:** the six hardcoded modes/taxonomies; pure-LLM-everything with no
  semantic retrieval at all (EgoVault keeps RAG tier-1 for verbatim/precision;
  the right answer is hybrid, not embedding-free).

## 5. Open questions for follow-up

1. Can a `hot.md`/`index.md`-style materialized digest be generated
   deterministically from EgoVault's `notes` table on write, and become
   curate() tier-0's first lookup (before cosine), measured against the
   finding-E corpus? (Feeds the search-quality track.)
2. Does the 8–15-pages-per-source fan-out conflict with EgoVault's
   human-approval gate (notes start `draft`)? Batch-defer-crossref vs
   per-note approval — sequencing question for large-source-synthesis.
3. Is contradiction-flagging better as a curate() tier-1 synthesis feature
   or a separate lint pass over notes (cf. their `wiki-lint` skill)?
