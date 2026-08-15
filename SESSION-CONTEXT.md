# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-08-15
**Last session:** `main` (direct commits)

---

## Current strategic direction: Cognitive Architecture & Knowledge Compiler

This vision grounds EgoVault in **cognitive neuroscience** (memory consolidation, spreading activation) and converges with 2024–2026 SOTA agent memory systems (GraphRAG, TencentDB-Agent-Memory, Letta/MemGPT):

**RAG retrieves then forgets. A cognitive knowledge compiler consolidates, densifies, and connects.**

### The Cognitive Neuroscience Mapping

1. **Hippocampal Episodic Buffer (Tier 1 Chunks):** Raw, chronological, sensory recording of ingestion (YouTube, PDF, web). High volume, verbatim evidence.
2. **Sleep Replay & Consolidation (Compiler Pipeline):** Topic segmentation + LLM distillation. Extracts invariant theses and removes oral noise.
3. **Neocortical Semantic Network (Tier 2 Notes):** Clean, interconnected Markdown notes in Obsidian (`notes_vec` + `notes_fts` + wikilinks).
4. **Working Memory & Spreading Activation (Tier 3 Curated Context):** Prefrontal working memory has 4–7 slots. Instead of flooding context, `curate()` triggers conceptual associative recall (notes + linked wikilinks/tags) to give the conversational LLM high-density mental models.

### The Breakthrough: Conceptual Vectorization & Lateral Thinking

- Vectorizing *raw chunks* produces myopic literal search (bringing 10 repetitive verbatim snippets).
- Vectorizing *distilled notes* indexes pure conceptual centroids. With looser cosine thresholds, `curate()` retrieves multidisciplinary models (e.g. Antifragility + OODA Loop + Game Theory) for creative synthesis and true intellectual personalization.
- See `docs/VISION-KNOWLEDGE-COMPILER.md` and `.meta/references/research/cognitive-architecture-neuroscience-sota-2026-08-15.md`.

### Dual-Space Retrieval & Provenance (Replaces Complex Librarian)

We radically simplified the retrieval layer (2026-08-15):
- **No complex "Librarian subagent" or slash command plugin:** The consumer LLM (Claude, Cursor, Next.js) already has reasoning capabilities. EgoVault provides clean, structured, high-signal data.
- **Two explicit search spaces:**
  1. `search_notes` : Semantic + BM25 hybrid search on compiled conceptual notes (`notes_vec` + `notes_fts`).
  2. `search_chunks` : Semantic + BM25 hybrid search on raw source chunks (`chunks_vec` + `chunks_fts`).
- **Full Traceability & Provenance Drill-Down:**
  - Notes link to candidates (`notes.candidate_uid`) and their source chunks (`chunk_uids`).
  - Passage locators: Timestamps for audio/video (`00:14:23-00:22:15`), Page numbers for books/PDFs (`p. 42-55`), Line numbers for text (`L120-L245`).
  - Calling `get_note(uid)` exposes the exact source chunks and locators for instant verbatim drill-down.

### Background Knowledge Gardening (Deferred to "Mode Veille")

- **Offline / Idle Knowledge Maintenance:**
  - Cluster `notes_vec` to suggest/insert `[[wikilinks]]` between related notes.
  - Tag curation (synonym detection & normalization).
  - Can incorporate a lightweight local/API mini-agent to suggest generative synthesis and process `queued` note candidates in batch.

---

## OpenTimestamps — setup complete, awaiting user action

**OpenTimestamps** is set up: script (`scripts/timestamp-release.sh`), docs (`docs/TIMESTAMPS.md`),
and tags (v0.1.0, v0.2.0, v0.3.0) are all created. OTS calendar servers were unreachable from
sandbox. **User must run from their machine:**

```bash
git push origin --tags
bash scripts/timestamp-release.sh v0.1.0
bash scripts/timestamp-release.sh v0.2.0
bash scripts/timestamp-release.sh v0.3.0
git add .timestamps/ && git commit -m "chore: add OTS proofs for v0.1.0, v0.2.0, v0.3.0"
```

Rule: only v0.X.0 tags are timestamped. Script enforces the pattern.

---

## Architecture decisions still active

- **VaultDB holds db_path internally** — upgrade to pooling = change internals only
- **generate is None when no LLM** — simplest approach
- **build_context() is the single wiring point**
- **Unified ingest with extractor registry** — add source type = add extractor + register
- **create_note_from_content()** builds system fields inside the tool
- **N pipeline families** — 2 implemented (document + media), architecture supports N
- **Web ingestion V1** — implemented with SSRF protection + 2-tier extraction

### Large source synthesis (spec written, not yet implemented)

- **Cascade:** web search (opt) → TOC+chapters → map-reduce → final synthesis
- **Template reuse:** same template per sub-generation → merge/dedup final
- **Presets:** `provider_mode` (local/api) × `quality_preset` (quick/balanced/quality)

**Principle clarified 2026-08-14 (Vincent, from the first end-to-end note-creation test):**
Chunks and notes must be told apart by what cuts them. A source's chunks are cut
**mechanically** (fixed-size windows over a big corpus) — a chunk's embedding is
necessarily a fragment, not a coherent idea. A note is cut **semantically** — one note
= one theme/concept/semantic nucleus, produced by an LLM (or a human, or both) *reading
across* the chunked mess to regroup by meaning. That's the entire point of the notes
layer: turn positional fragments into meaning-addressed vectors.
**Corollary: 1 source → N notes is the norm for anything multi-topic, not 1 source →
1 note.** `embed_note()` produces exactly one vector per note (title+docstring+body
concatenated, no internal chunking — confirmed in code and DB, 2026-08-14). So making a
note *longer* to cover more ground doesn't add resolution, it blurs the single vector by
averaging across topics — the same failure mode as an under-chunked source, just at the
note layer. **The fix for "notes feel too short" is never a longer note/prompt — it's
splitting into more notes, each still one coherent nucleus.**
This directly invalidates the 2026-08-14 ad hoc note-creation sub-agent prompt (one note
per source, regardless of source breadth) and should be the north-star constraint when
this spec is picked up: the cascade's map-reduce should map to **N notes by theme**, not
reduce to **one note**.

---

## Traps to avoid

1. Don't write specs without brainstorming with the user
2. Use analogies for architecture jargon (restaurant kitchen worked for VaultContext)
3. Don't forget the north star: 2-minute demo video
4. Don't mix features with refactoring
5. Rate limit / background thread tests MUST mock `_submit_job` to avoid DB locks
6. When editing CLAUDE.md, keep it ≤110 lines — detailed rules go in GUIDELINES.md
7. Don't optimize search/synthesis without real data first
8. **Don't assume the user understands the technical distinction between "agent" and "tool with LLM call"** — always explain concretely
9. **The system has never been tested with real data** — all tests are mocked. Real-world testing is prerequisite for any quality optimization.
10. **OpenTimestamps BEFORE publishing the vision** — establish antériority first.
11. ~~RAG distance is L2 on UNNORMALIZED embeddings~~ — **RESOLVED 2026-05-16**:
    cosine metric + `embed()` normalization. Distance ∈ [0,2], comparable across
    queries, verified semantically discriminant. `scripts/reembed.py` rebuilds vec
    tables after any metric/model change (run it on existing vaults). curate() spec
    `escalation_max_distance=0.5` is now meaningful.
12. **Test counts: now 511 pass / 0 fail / 1 skip, DETERMINISTIC** (2026-05-21,
    +5 from F5 follow-up, +14 from RRF hybrid slice, +1 from curate adoption).
    The old "7 pre-existing failures" were audited (zero product bugs) and fully
    fixed. The API suite was non-deterministic (session client + global
    rate-limit state) — fixed via autouse reset in `tests/api/conftest.py`.
    Still: a green suite is NOT a strong gate (TEST-C2 — ingest/semantic ranking
    is over-mocked). Always run the full suite; treat the real-data ingest
    (étape 6) as the first true integration signal.
13. **Mojibake on Windows shell** — console display mojibake != data corruption
    (verify stored bytes via Python `-X utf8`). BUT git **commit messages**
    passed via Bash `-m` ARE corrupted into history (shell argv encoding).
    Rule now durable in `.meta/GUIDELINES.md` § Git commits: ASCII-only
    messages. 8 corrupted commits cleaned 2026-05-18 via `filter-branch`
    (post-`v0.3.0` only — OTS proofs preserved), force-pushed. The
    `force_git_author` hook was also fixed (was appending `--author` to the
    last segment of compound commands). Backup branch `backup-pre-histclean`.
14. **uv ban LIFTED 2026-05-19** — full import audit (app + scripts/ + tests/)
    shows ZERO undeclared third-party deps; `pyproject.toml` is complete.
    Validated: `uv sync --all-extras` then full pytest = **496 pass / 1 skip /
    0 fail**, tech_watch works. **MANDATORY invocation: `uv sync --all-extras`**
    — bare `uv sync` STILL prunes `trafilatura` (tier1), `feedparser` +
    `huggingface_hub` (tech-watch) because they are *optional extras* the code
    imports. Use `--all-extras` and the env is fully functional. Backup freeze:
    `Documents/_venv-freeze-backup-20260519.txt` (deletable). save-progress
    skill still missing its preflight script — separate MINOR debt.
15. **Cosine distance is undefined for the zero vector** — sqlite-vec returns
    `NULL` distance → `SearchResult.distance: float` ValidationError. Never use a
    zero embedding in tests (`make_embedding(0.0)`); real embeddings are never zero.

---

## Deferred items (documented, not forgotten)

| Item | Where documented | When to do |
|------|-----------------|------------|
| ~~**Vision spec + OpenTimestamps**~~ | ~~SESSION-CONTEXT.md~~ | **DONE** — vision doc committed, OTS set up (user must push tags + stamp) |
| ~~**MCP Claude Desktop setup**~~ | ~~SESSION-CONTEXT.md~~ | **DONE** — `claude_desktop_config.json` configured, `docs/mcp/CLIENT-SETUP.md` created |
| ~~**MCP Claude Code setup**~~ | ~~`docs/mcp/CLIENT-SETUP.md`~~ | **DONE** — versioned `.mcp.json` at repo root. Claude Code does NOT read `mcpServers` from settings.json; uses `.mcp.json` (project) or `claude mcp add -s user`. Active after restart. |
| **Real-world testing** | SESSION-CONTEXT.md | **NEXT PRIORITY** — validate fundamentals with real data |
| ~~**Knowledge compiler (`curate()` tool)**~~ | ~~`docs/VISION-KNOWLEDGE-COMPILER.md`~~ | **DONE 2026-05-16 — tier 0 shipped** |
| **curate() tier 1 (LLM synthesis)** | plan §Self-Review / VISION | After F5 — needs generic `complete` Protocol on VaultContext; fills `confidence`, upgrades `synthesis` |
| **curate() API `/curate` endpoint** | plan §5 | Deferred — only MCP+CLI surfaces in tier 0 |
| **Calibrate `escalation_max_distance`** | `config/system.yaml` (=0.5) | During real-world testing — default is a guess |
| Pre-packaged librarian agent (AGENTS.md) | `docs/FUTURE-WORK.md` | After curate() exists |
| Large source synthesis | `.meta/specs/2026-04-06-large-source-synthesis-spec.md` | After real testing |
| Multi-source workflow | `.meta/specs/2026-04-06-notebooklm-synapthema-ideas.md` §1 | High priority brainstorm |
| Search quality (reranking) | `.meta/specs/future/2026-03-28-reranking-design.md` | After real-world testing |
| Crash recovery (`recover_source`) | Archive spec §16 | After large source synthesis |
| **Migrate librarian to MCP sampling** | spec `2026-05-29-curate-tier1-librarian-base` §10 | When Claude Code/Desktop advertise the sampling capability — replaces subagent/slash with transparent server-side isolation |
| **curate() tier-1 server-side LLM (ollama/API)** | spec §12 (out of scope of base) | Next spec — needed for the frontend/human path (no host agent to delegate to) |
| **Note approval lifecycle (`create_note`/`update_note` status)** | PROJECT-STATUS.md § Known technical debt | Explicitly flagged by Vincent as a real problem, not to be left as the SQL patch — needs its own brainstorm before any other note-workflow change |
| **Note-space clustering + LLM-named emergent themes** | Raised 2026-08-14 during the note-segmentation brainstorm, explicitly deferred by Vincent as "postérieur" | After `.meta/specs/2026-08-14-note-creation-semantic-clustering-spec.md` ships. Idea: cluster on the *notes* vector space (not chunks) to surface cross-source emergent themes, name clusters via LLM, and maintain the resulting non-vector proximity links (beyond uid/source/tags) via a deterministic script. Needs its own brainstorm — not scoped here. |

---

## Open questions (require interactive discussion)

1. ~~**Vision spec scope**~~ — **RESOLVED**: concise vision doc (docs/VISION-KNOWLEDGE-COMPILER.md), not a whitepaper.
2. ~~**OpenTimestamps setup**~~ — **RESOLVED**: v0.X.0 tags only, script enforces pattern, user must run from machine.
3. ~~**Real-world testing plan**~~ — STARTED 2026-05-15 (YouTube subtitles). Surfaced
   F1–F5 (see audit). Remaining: PDF/web sources, queue test — blocked on F2/F5 decisions.
4. ~~**curate() design**~~ — **RESOLVED for tier 0 (implemented 2026-05-16,
   validated on live vault 2026-05-17)**. curate() ran end-to-end on real
   embedded data (0 notes → chunk escalation, cosine distances discriminant).
   Findings A/B/C logged in `.meta/scratch/2026-05-17-prereinit-findings.md`
   (CLI UTF-8 mojibake, source.title None, hook brittleness FIXED). Only
   empirical tuning of `escalation_max_distance` remains. Tier 1 (LLM
   synthesis) is a separate future item, gated by F5.
   Spec + plan archived to `.meta/archive/{specs,plans}/`.
6. ~~**F5 scope**~~ — **RESOLVED 2026-05-17 (ollama)** — local note
   generation via Ollama implemented (brainstorm->spec->architect/code
   reviewed->plan->subagent-driven TDD). `_generate_ollama` mirrors the claude
   path: ollama chat with structured output honoring the same validation-retry
   contract. Suite green. **Chantier B still open** (openai provider,
   `providers.mode`, install wizard, OpenRouter) — ref audit 10.4.
   See `.meta/audits/2026-05-17-real-ingest-test-results.md`.
5. **AGENTS.md format** — follow agentify convention? Custom format? What agent definitions?
7. ~~**curate() retrieval redesign**~~ — **RESOLVED 2026-05-29**. Re-brainstormed
   (open question #7) → spec + plan written and committed
   (`.meta/specs|plans/2026-05-29-curate-tier1-librarian-base*`, `0177202`/`4a1adf2`).
   Decisions: **base = librarian sub-agent + `/ask-vault` slash command shipped as a
   Claude Code plugin**, using the host's own LLM (no API key / local model — verified
   MCP sampling is UNSUPPORTED by Claude Code/Desktop today, tracked as debt).
   **Selection method = recall-first hybrid RRF + wide net (both tiers, untruncated);
   precision delegated to the sub-agent's reasoning** (the PageIndex "LLM reasons over
   the pile" half, without building a structural index). Structural tier-0 deferred.
   Output contract `{answer, used_source_uids}`, stable across future layers. The only
   Python change is a `generous` mode on `curate()`. Next session = execute the 7-task plan.
8. **`create_note` approval lifecycle** — first real end-to-end test (2026-08-14: text/web/
   youtube-subtitles/PDF ingest, sub-agent note creation) surfaced that `create_note`'s
   `status="active"` default has no safety net: nothing stops an agent that skipped human
   review from producing "approved" notes, and no tool exposes `draft`↔`active` transitions
   at all (not even for `generate_note_from_source`'s drafts). 4 notes were force-flipped to
   `draft` via direct SQL as an explicit stopgap — Vincent was clear this is a band-aid, not
   a resolution, and wants it brainstormed properly (not silently designed inline). Candidate
   directions: `status` param on `create_note` (default `draft`?), `status` field on
   `update_note`, doc fixes. Needs a dedicated brainstorm session before touching code.
