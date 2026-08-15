# EgoVault — Vision: Knowledge Compiler & Cognitive Architecture

**Date:** 2026-04-16 (Updated: 2026-08-15)
**Status:** Core Vision Document
**Inspired by:** Cognitive Neuroscience (Memory Consolidation, Spreading Activation), Andrej Karpathy's LLM Wiki pattern, SOTA Agent Memory systems (GraphRAG, TencentDB-Agent-Memory, Letta/MemGPT).

---

## 1. The Core Problem with Naive RAG

Classic RAG systems operate on a naive mental model: *"Split text into arbitrary 800-token chunks, embed verbatim words, retrieve top-K by cosine distance, dump into LLM prompt."*

This approach fails for high-level intellectual work for three fundamental reasons:

1. **Verbatim Myopia & Vocabulary Mismatch:** A conférencier can discuss *"asymmetric bets with capped downside and infinite upside"* for 30 minutes without ever uttering the word *"antifragility"*. A chunk search on *"antifragilité"* will miss the passage or return poor rank.
2. **Context Pollution & Attention Degradation:** Flooding a conversational LLM with 20,000 tokens of conversational fluff, verbal disfluencies, and fragmented sentences triggers the well-documented *lost-in-the-middle* degradation and consumes unnecessary reasoning budget.
3. **No Conceptual Compounding:** Every search restarts from zero. The system never learns, abstracts, or compresses knowledge into durable models.

---

## 2. The Cognitive Foundation: The Neuroscience Parallel

Human biology solved long-term knowledge retention and associative reasoning millions of years ago. EgoVault directly mirrors the **two-stage cognitive memory model**:

```
RAW STREAM (YouTube, PDF, Audio, Books, Web)
              │
              ▼
[1. Hippocampal Episodic Store] ──────► Chunks (Tier 1)
   - High volume, raw verbatim,         - Raw transcripts in SQLite + chunks_vec
   - Chronological, sensorily noisy      - Precise for exact quotes & numbers
              │
              ▼
   [CONSOLIDATION / SLEEP REPLAY] ────► Topic Segmentation + LLM Synthesis
   - Noise filtering & invariant extraction
              │
              ▼
[2. Neocortical Semantic Network] ────► Notes (Tier 2)
   - High conceptual density            - Markdown in Obsidian + notes_vec
   - Interconnected mental models       - Wikilinks [[...]] & tags
              │
              ▼
   [SPREADING ACTIVATION] ────────────► Librarian curate() + Multi-Hop
   - Prefrontal Working Memory (4-7 items) receives CuratedContext (Tier 3)
```

### A. Hippocampus vs Neocortex (Chunks vs Notes)
- **Hippocampus (Tier 1 Chunks):** Stores the raw episodic recording of what was read/heard. High volume, detailed, but unindexed by high-level meaning.
- **Sleep Replay / Consolidation (Knowledge Compilation):** Offline distillation that extracts the underlying thesis, structures the arguments, and registers new concepts.
- **Neocortex (Tier 2 Notes):** The permanent semantic web where knowledge lives as clean, abstracted mental models.

### B. Working Memory Limits & Active Associative Recall
- A human never holds 1,000 books in active consciousness. Working memory maintains only 4 to 7 active concepts at a time.
- True "personalization" of an AI is not achieved by stuffing all lifetime reading into a giant prompt. It is achieved through **instant associative recall** of the exact 2 to 3 distilled mental models relevant to the query.

### C. Spreading Activation (Collins & Loftus)
- In human memory, activating a concept node (*"Risk"*) automatically pre-activates adjacent nodes (*"Optionality"*, *"Antifragility"*, *"Skin in the game"*).
- In EgoVault, retrieving a note activates its conceptual neighbors via wikilinks `[[concept]]` and shared tags, powering lateral thinking and serendipity.

---

## 3. Why Vectorizing *Concepts* (Notes) Beats Vectorizing *Chunks*

| Dimension | Tier 1: Raw Chunk Vectorization | Tier 2: Conceptual Note Vectorization |
|---|---|---|
| **Content** | Oral speech, repetition, anecdotes, filler words | Distilled thesis, canonical vocabulary, clear headings |
| **Vector Sharpness** | Diffuse, noisy, subject to phrasing variance | Sharp, dense, concentrated at the concept's centroid |
| **Retrieval Power** | Literal match (finds where a word was said) | **Conceptual resonance** (finds related mental models) |
| **Lateral Thinking** | Myopic: brings 10 repetitive chunks of the same topic | **Serendipitous:** brings 3 distinct models across domains |
| **Token Budget** | High (~15,000 tokens of raw text) | Ultra-frugal (~1,200 tokens of pure signal) |

**The Lateral Thinking Breakthrough:**  
When vectorizing distilled notes, we can loosen the semantic search threshold. Instead of returning 15 chunks repeating the exact same tactical advice, the system surfaces cross-disciplinary principles (e.g., combining a note on *Darwinian Evolution*, a note on *Boyd's OODA Loop*, and a note on *Taleb's Convexity*). The LLM can then reason across domains rather than parroting transcripts.

---

## 4. Architecture: 3 Knowledge Tiers

```
Tier 3 — Compiled Context (What the Conversational LLM receives)
    On-the-fly syntheses, note excerpts, sourced citations.
    Minimal, high-signal, ready to consume. Never noise.

Tier 2 — Compiled Notes (The Neocortical Vault)
    Structured Markdown notes, human-validated, cross-source.
    Dense, reliable, searchable via notes_vec + notes_fts.
    Human-navigable in Obsidian, agent-accessible via MCP.

Tier 1 — Raw Source Chunks (The Hippocampal Evidence Layer)
    Embedded chunks from original sources (YouTube, PDF, web, text).
    Precise, verbatim, immutable evidence.
    Searchable via chunks_vec + chunks_fts (Hybrid RRF).
```

---

## 5. The Librarian (`curate()`): The Cognitive Retrieval Engine

The Librarian is a **deterministic tool with an isolated LLM call as a subroutine** (same pattern as `generate_note_from_source`):

```
User ↔ Conversational Agent (Claude via MCP, clean context)
              │
              │ "How should I structure my decision under uncertainty?"
              ▼
        curate(query)
              │
              ├── 1. Search compiled notes (Tier 2, conceptual resonance)
              ├── 2. Spreading activation: fetch linked notes ([[wikilinks]], tags)
              ├── 3. If exact facts/quotes needed → search RAG chunks (Tier 1)
              ├── 4. Isolated LLM synthesis call (separate context window)
              │
              ▼
        Returns CuratedContext:
              ├── synthesis: dense, cross-source structured answer
              ├── sources: citations with immutable UIDs (evidence trace)
              └── confidence: score based on evidence consensus
```

---

## 6. EgoVault vs The Ecosystem

| System | Target Audience | Storage & Architecture | Retrieval Philosophy |
|---|---|---|---|
| **Microsoft GraphRAG** | Enterprise / Analyst | Heavy graph DB + LLM clustering pipelines | Global community summaries; expensive ingest |
| **Letta (MemGPT) / TencentDB** | Autonomous Agent only | Memory pyramids in DB (opaque to user) | Autonomous agent self-edits memory |
| **Obsidian + Copilot / Smart Conn.** | Human only | Local Markdown notes | Naive chunk RAG on user files; no multi-source media ingest |
| **EgoVault** | **Hybrid: Human (Obsidian) + Agent (MCP)** | **Local-first: SQLite (`vault.db`) + Plain Markdown (`.md`)** | **Cognitive Knowledge Compiler: Tiered consolidation, conceptual vectors, deterministic Tier-0 baseline** |

---

## 7. The Guiding Principles

1. **Dual Citizenship:** Every piece of compiled knowledge must be **readable and editable by a human in Obsidian** AND **queryable by an LLM agent via MCP**.
2. **Deterministic Baseline (Tier 0 First):** Every feature must work reliably without an LLM (FTS5 + cosine + RRF). The LLM is an accelerator, never a fragile single point of failure.
3. **Local-First & Sovereign:** Your second brain belongs in a single SQLite database and a Git-tracked folder of Markdown files. Zero cloud lock-in.
4. **Compile, Don't Just Retrieve:** High-entropy input must be transformed into low-entropy, dense, permanent knowledge assets.
