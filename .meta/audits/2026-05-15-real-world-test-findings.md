# Real-World Test Findings — 2026-05-15

First end-to-end test with real data (YouTube source `rGsLMYYVRR8`, FR, subtitles).
The system had never run on real data — all prior tests mocked.

## Setup

- Embedding: Ollama `nomic-embed-text` (pulled this session)
- LLM: switched `user.yaml` to `ollama / gemma3:1b` (Option B, local)
- Source: `https://youtu.be/rGsLMYYVRR8` (Théodore Dalrymple essay, ~FR)

## Findings

### F1 — DB not bootstrapped outside the API — RESOLVED

`init_db`/`init_system_db` were only called by the FastAPI lifespan. CLI/MCP got an
uninitialized schema → `no such table: sources`. Fixed by calling both (idempotent)
in `build_context()`, the documented single wiring point. Commit `160f27f`. Verified
end-to-end: real ingest reaches `rag_ready`. +2 unit tests, zero regression
(pre-fix 7 fail/463 pass vs post-fix 7 fail/465 pass — identical failures).

### F2 — RAG distance metric is L2 on unnormalized embeddings — CRITICAL, OPEN

`vec0` virtual tables use default **L2 (euclidean)** distance. Ollama embeddings are
returned raw (`_embed_ollama`), **not normalized**. Observed search distances ≈ 15–17,
CLI `score = 1 - distance` yields absurd negatives.

**Impact on the Knowledge Compiler strategy:** the `curate()` tier-0 spec
(`.meta/specs/2026-05-15-curate-tier0-spec.md`) relies on
`escalation_max_distance` as an absolute similarity threshold. With unnormalized L2,
no absolute threshold is meaningful across queries. **The spec must be revised**
(cosine + L2-normalized embeddings, or a relative/top-k escalation rule) before
`curate()` is implementable in a useful way. This is the central finding: the product
north star assumes a reliable similarity signal that does not currently exist.

Also: `nomic-embed-text` expects task prefixes (`search_query:` / `search_document:`)
which are not applied — separate quality issue to confirm once the metric is fixed.

### F3 — Subtitle "mojibake" — FALSE ALARM

Console showed `D'o�` for `D'où`. Verified the DB stores correct UTF-8
(`D'où`, `Théodore`, `problèmes`; no U+FFFD). The garbling was the Windows cp1252
console via the Bash tool, not data corruption. No code issue.

### F4 — 7 pre-existing broken tests — OPEN (tech debt)

Full suite: **465 pass / 7 fail / 1 skip** (was claimed "374 pass" in PROJECT-STATUS —
stale). Failures are pre-existing (identical before F1 fix), never caught because the
full suite had not been run in a long time:

- `tests/tools/test_export_typst.py::test_note_to_typst_escapes_quotes` —
  `_note_to_typst()` signature drifted (missing `lang`, `font` args)
- `tests/api/test_ingest_text.py` ×3 (`missing_title_422`, `too_large_413`,
  `custom_source_type`)
- `tests/api/test_integration.py` ×2 (`youtube_job_lifecycle_done/failed`)
- `tests/cli/test_notes.py::test_note_create_from_file` — AttributeError

### F5 — Ollama LLM generation unimplemented — OPEN (scope decision)

`generate_note_content()` raises `NotImplementedError` for `provider in {ollama, openai}`
— only `claude` is implemented. Option B (local note generation with gemma3:1b) is
**not supported by the codebase**; it is a feature, not a bug. `_llm_is_configured()`
returning `False` for ollama is honest. Note generation testing (real) requires either
implementing the ollama provider or using a Claude API key.

## Recommended next actions (priority order)

1. **Re-brainstorm `curate()` tier 0** in light of F2 — fix the similarity metric
   (cosine + normalization) as the prerequisite; revise the escalation rule.
2. Decide scope on F5 (implement ollama generation vs. require Claude key) — gates
   real note-generation testing and the ingest-queue test.
3. Triage F4 (separate debt cleanup pass).
