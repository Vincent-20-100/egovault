---
mode: deep
date: 2026-05-19
slug: pageindex
url: https://github.com/VectifyAI/PageIndex
angle: vectorless reasoning-based RAG vs EgoVault cosine RAG (finding E); borrow for curate/search-quality
status: active
---

# Deep — VectifyAI/PageIndex

## 1. Fingerprint

- **Primary lang:** Python
- **Repo type:** library (vectorless RAG) + cookbook notebooks
- **File count:** 53
- **License:** MIT
- **Stars / last commit:** unknown (`gh` unavailable)
- **Pitch:** "Document Index for Vectorless, Reasoning-based RAG."

## 2. Structure map

```
pageindex/  page_index.py page_index_md.py retrieve.py client.py
            config.yaml utils.py __init__.py        ← the engine
run_pageindex.py                                    ← CLI: --pdf_path
cookbook/   agentic_retrieval / pageindex_RAG_simple / vision_RAG (.ipynb)
examples/   agentic_vectorless_rag_demo.py  documents/ tutorials/ workspace/
```

## 3. Key findings

### 3.1 Extension points
- `page_index.py` (PDF) and `page_index_md.py` (Markdown via heading
  hierarchy) are separate builders → a Markdown index builder already exists.
  *Why it matters:* EgoVault notes are Markdown with structure; `page_index_md`
  is the closest off-the-shelf to a notes-tree builder.
- `retrieve.py` is the reasoning-search step, decoupled from index building.
  *Why:* clean seam — index build (ingest-time) vs retrieve (query-time),
  same split as EgoVault ingest vs curate().

### 3.2 Safety & governance
- Retrieval returns page/section references with "full traceability" — every
  answer cites the node it came from. *Why:* matches EgoVault's
  verifiable-source-UID requirement in `CuratedContext`; reinforces that
  curate() must keep source UIDs (it does).

### 3.3 Documentation quality
- README states the thesis bluntly: **"Similarity ≠ relevance — similarity
  search often falls short"** for professional/domain documents. *Why:* this
  is EgoVault finding E named explicitly by an independent project — strong
  external corroboration that the cosine-only ceiling is real, not a bug.

### 3.4 Developer workflow
- `run_pageindex.py --pdf_path ...`, config in `config.yaml`
  (`--model` default gpt-4o, `--max-pages-per-node` 10, `--max-tokens-per-node`
  20000, `--toc-check-pages` 20). *Why:* tree build is LLM-driven and tuned for
  **long** docs; not a drop-in for EgoVault's tiny `source.md` corpus.

### 3.5 Distinctive patterns
- **Hierarchical tree index instead of vectors:** nodes = {title, node_id,
  page range, summary, children}. Retrieval = LLM traverses the tree by
  reasoning, not similarity. *Why it matters:* a concrete **tier-1**
  alternative to cosine for the RAG (source) layer on long sources
  (YouTube transcripts 5–15k tok, PDFs) — exactly where finding E hurts most.
- **Scale via a "File System" layer:** a file-level tree over a whole corpus
  ("millions of documents"), reasoned over top-down. *Why:* converges with
  deep #1 (claude-obsidian `index.md` precedence) — TWO independent projects
  reject pure cosine in favour of LLM-reasoning-over-structure. Signal, not
  noise (synthesis-over-collection): the SOTA direction for the notes tier is
  structured navigation, embeddings demoted to a recall prefilter.
- **Sweet spot = few long docs; "many small notes — less ideal."** *Why /
  caveat:* EgoVault's finding-E corpus was 25 tiny notes (1 chunk each) —
  NOT PageIndex's sweet spot. PageIndex helps EgoVault's *long-source* RAG,
  not the compiled-notes tier. Don't over-generalize the win.

## 4. Tiered recommendations

- **USE AS-IS:** (none) — LLM-call-heavy at index time, OpenAI-Agents-SDK
  examples, tuned for long PDFs; doesn't fit EgoVault's deterministic tier-0
  or its current stack unmodified.
- **EXTRACT PARTS:** the `page_index_md.py` heading-hierarchy → tree-of-
  {title,summary,children} construction, as a candidate **structural index
  for long sources** built at ingest (transcripts/PDFs) and stored alongside
  chunks; curate() tier-1 could reason over it instead of/with cosine.
  Rationale: targets finding E precisely on the layer where it bites.
- **BORROW CONCEPTS:** "similarity ≠ relevance" as the framing for the
  search-quality track; reasoning-over-TOC as the curate() **tier-1**
  retrieval design (complements the embedding-free tier-0 idea from deep #1 —
  together they form a coherent hybrid: deterministic structural tier-0 →
  LLM-reasoned structural tier-1 → cosine only as recall fallback).
- **INSPIRATION:** node traceability (cite node_id) reaffirms keeping verbatim
  source UIDs through every retrieval tier.
- **REJECT:** PageIndex for the small-notes (tier-2 compiled) corpus — wrong
  tool for short atomic notes; and the gpt-4o/OpenAI-Agents coupling
  (EgoVault is provider-agnostic, F5 local-first).

## 5. Open questions for follow-up

1. For long EgoVault sources (YouTube/PDF), does an ingest-time markdown/TOC
   tree (à la `page_index_md`) + LLM tree-reasoning beat cosine chunk search
   on the finding-E corpus? Design a head-to-head in the search-quality track.
2. Convergence check: deep #1 (deterministic `index.md` precedence) +
   deep #2 (LLM-reasoned tree) — are these the tier-0 and tier-1 of the SAME
   "structured-navigation curate()"? If so, that reframes the curate() tier-1
   spec away from "LLM synthesis of cosine results" toward "LLM reasoning over
   a structural index". Major design fork → needs a brainstorm.
3. Index-build cost: tree construction is LLM-heavy. Is it affordable per
   source under the F5 local-LLM budget, or API-only (chantier B)?
