# EgoVault — Session Context

> **This file carries the thinking from one session to the next.**
> It is NOT a log — it is rewritten each session to stay concise and relevant.
> A new LLM context must read this file to understand WHY decisions were made,
> not just WHAT was decided.

**Last updated:** 2026-05-17
**Last session:** `main` (direct commits)

---

## Current strategic direction: Knowledge Compiler + Librarian Agent

This session produced a **product vision shift** inspired by Andrej Karpathy's LLM Wiki
pattern and the agentify project. The core insight:

**RAG retrieves then forgets. A knowledge compiler accumulates and densifies.**

EgoVault should evolve from a RAG system to a **two-layer knowledge system** with an
intelligent retrieval agent. This is documented in detail in `docs/FUTURE-WORK.md`
(section "Architecture pivot — Knowledge compiler + Agent retrieval").

### The Two-Layer Architecture

- **Layer 1 (keep):** RAG on raw source chunks. Precise, verbatim, good for exact facts.
- **Layer 2 (new):** Compiled knowledge on notes. Dense, human-validated, cross-source synthesis.

### The Librarian Pattern

Instead of dumping top-K chunks into the conversation:

```
User ↔ Conversational LLM (via MCP, clean context window)
              ↓ calls curate("question about X")
        curate() tool inside EgoVault:
              ├── search_notes() → deterministic
              ├── search_chunks() → deterministic
              ├── ctx.get_completion(prompt) → isolated LLM call (separate context)
              └── return CuratedContext (synthesized, minimal)
```

**Key decision:** The librarian is NOT an autonomous agent or separate project. It's a
**smart tool** (`curate()`) that uses one isolated LLM call as a subroutine — same pattern
as `generate_note_from_source`. Testable, mockable, deterministic-except-one-call.

### Tiered — works without LLM

| Tier | What curate() does | Dependency |
|------|-------------------|------------|
| 0 | Search + rank + truncate → sorted raw results | Nothing (deterministic) |
| 1 | Tier 0 + LLM synthesis | LLM local or API key |

**Principle:** Every feature has a tier 0 deterministic baseline. LLM = accelerator, not prerequisite.

### Pre-packaged agent for MCP clients

For Claude Code users: provide `.claude/rules/vault-usage.md` + `AGENTS.md` so the user's
own LLM becomes the librarian via prompt. Zero extra infrastructure.

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
12. **Test counts: now 481 pass / 0 fail / 1 skip, DETERMINISTIC** (2026-05-17).
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
7. **curate() retrieval redesign (NEW, from 2026-05-19 tech-watch)** — 3
   independent SOTA projects reject pure cosine (synthesis card
   `.meta/references/research/synthesis-retrieval-sota-2026-05-19.md`). The
   deferred "curate() tier-1 = LLM synthesis of cosine top-K" must be
   re-brainstormed against hybrid (BM25+cosine RRF) + structural/tree
   retrieval BEFORE it is planned. Concrete first step (search-quality
   track, no brainstorm needed, no new dep): **RRF(BM25 via SQLite FTS5,
   cosine)** tested on the finding-E corpus.
