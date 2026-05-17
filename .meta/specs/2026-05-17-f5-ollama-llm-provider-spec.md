# F5 — Ollama LLM Provider (note generation)

**Date:** 2026-05-17
**Status:** Reviewed (architect + code-coherence agents, 2026-05-17;
11 corrections applied) — awaiting user validation before writing-plans
**Scope:** A — vertical slice. First concrete piece of open question 10.4
("Provider management"). Does NOT build the full multi-provider abstraction,
`providers.mode`, setup wizard, OpenRouter, or hot-swap (= future chantier B).
**Supersedes:** nothing.
**Related:** `docs/product-audit/12-provider-coherence.md` (§12.3 personas —
this implements the "Local-first" LLM tier), `docs/VISION-KNOWLEDGE-COMPILER.md`
(tier 0 principle), `.meta/audits/2026-05-17-real-ingest-test-results.md`.

---

## 1. Problem

`infrastructure/llm_provider.generate_note_content` implements only the
`claude` provider. `ollama` and `openai` `raise NotImplementedError`. The
project's product identity (VISION, §12.3) mandates a first-class local-first
persona (zero API key, no big GPU). Without a local LLM path, autonomous note
generation is impossible offline, and curate() tier-2 (notes layer) cannot be
exercised without a paid API.

Sequencing decision (A3, already taken with the user): the **claude** path
(already implemented) is used for immediate curate tier-2 testing via an API
key — that needs zero code and is out of scope here. This spec covers ONLY the
ollama implementation, which remains a product requirement regardless.

## 2. Goal / success criteria

- `generate_note_content` with `provider: ollama` returns a valid
  `NoteContentInput` from a local Ollama model, honoring the exact same
  contract as the claude path (template, validation, retry, error handling).
- `build_context` wires a working `generate` callable when `provider: ollama`
  (no API key required).
- Pipeline degrades cleanly: Ollama unreachable → sanitized `RuntimeError`,
  the rest (ingest → search → curate tier-0) keeps working (no LLM required).
- Target model `qwen2.5:7b-instruct` (Q4_K_M); documented fallback
  `qwen2.5:3b-instruct`. Model is config-driven (`user.yaml` `llm.model`) —
  no model name hardcoded in code.

Non-goals: openai provider, `providers.mode` config, setup wizard, OpenRouter,
hot-swap, reranker/embedding provider changes, prompt/template redesign.

## 3. Design

### 3.1 `_generate_ollama` — behavioral equivalent of `_generate_anthropic`

New function in `infrastructure/llm_provider.py`, reusing the existing
`_load_template` and `_build_user_message` unchanged. **Add `import requests`
at the module top** (`llm_provider.py` does NOT currently import it — only
`embedding_provider.py` does; P0).

- Same retry loop: `for attempt in range(max_retries + 1)` with
  `error_context` injected. NOTE: not a *strict* mirror — claude injects via
  the SDK `system=` kwarg; ollama injects the same text into the chat
  `messages[0]` (system role) content. Behavioral equivalent, adapted to the
  chat array.
- **Validation contract — exact claude parity (P0, correctness trap):** use
  bare `NoteContentInput(**data)` with **NO taxonomy context**, identical to
  `_generate_anthropic` (`llm_provider.py:100`). `validate_taxonomy` is
  `mode="before"` and no-ops without `info.context`; taxonomy is enforced
  later at approval (`cli/commands/notes.py`). Do NOT add
  `model_validate(..., context={"taxonomy": ...})` — that would silently
  diverge from the claude path.
- Same output contract: `json.loads(raw)` → `NoteContentInput(**data)`;
  retry on `(json.JSONDecodeError, ValidationError)`; raise `ValueError`
  with the last error after exhaustion (identical message shape).
- `max_retries = settings.system.llm.max_retries` (reused).
- Accepted debt: the retry/validate/error-context loop is duplicated between
  `_generate_anthropic` and `_generate_ollama`. A shared
  `_run_generation_loop(call_fn, ...)` seam is intentionally NOT introduced
  here — the right provider interface is chantier B's job (it has the broader
  openai/openrouter/usage requirements). Consolidation is tracked B debt.

`generate_note_content`: replace the ollama `raise NotImplementedError`
branch with `return _generate_ollama(...)`. The `openai` and unknown branches
are unchanged.

### 3.2 Ollama call

Mirror `_embed_ollama` (same HTTP style, same error handling):

- `requests.post(f"{base_url}/api/chat", json=payload, timeout=<configurable>)`
  where `base_url = settings.install.providers.ollama_base_url`.
- Payload:
  - `model = settings.user.llm.model`
  - `messages = [{"role": "system", "content": system_prompt + error_context},
    {"role": "user", "content": user_message}]`
  - `stream: false`
  - **`format` (design decision, was R1):** default to `format: "json"`
    (broadly supported). Passing the full
    `NoteContentInput.model_json_schema()` is an *optional optimization*,
    gated on a known-good Ollama version — NOT the default-safe path. The
    retry loop (not the wire schema) is the source of truth for validity.
    This avoids coupling the infrastructure provider to core's live Pydantic
    schema as a load-bearing wire contract.
  - `options = {"temperature": 0.2, "num_ctx": <configurable>}` — temperature
    is a code constant, intentionally NOT user-configurable (YAGNI; §12.7's
    provider-config UX is about provider/key selection, not generation
    hyperparameters — no contradiction).
- Response text extracted from `response.json()["message"]["content"]`
  (non-streaming `/api/chat` shape — confirmed; `/api/generate` would be
  `["response"]`, not used here).
- On any request/HTTP exception: `from core.sanitize import sanitize_error;
  raise RuntimeError(sanitize_error(e)) from None` (exact existing pattern).
- `response.raise_for_status()` before parsing.

### 3.3 Config

- **`ProvidersConfig` (install.yaml), NOT `system.yaml`:** add
  `ollama_num_ctx: int = 8192` and `ollama_timeout_s: int = 180` next to the
  existing `ollama_base_url`. Rationale (architect P2): these are per-install
  operational tuning, exactly like `ollama_base_url`; putting them in
  versioned `system.yaml` would ship provider-specific tuning baked in for
  all users and split Ollama config across two files. This also matches the
  §12.7 install-level provider-config direction (no divergence B must undo).
  Defaults make existing `install.yaml` keep parsing.
- `user.yaml.example`: document `llm.provider: ollama` +
  `llm.model: qwen2.5:7b-instruct` with the `qwen2.5:3b-instruct` fallback
  note. (Code stays config-driven; `LLMUserConfig.model` default is `llama3`
  — only the example file names a model, no hardcoding.)

### 3.4 Context wiring

`infrastructure/context.py::_llm_is_configured`: add — return `True` when
`settings.user.llm.provider == "ollama"` (no key required). Effect:
`generate_fn` is wired (not `None`) in local mode. **Also update the
docstring**: it currently says "has credentials configured" — ollama is
configured but keyless; reword to "a usable LLM provider is configured
(credentials OR keyless local)". This + the `ProvidersConfig` fields are the
behavioral ripples beyond `llm_provider.py` (no other provider/key gate
exists — `generate_note_from_source` only checks `ctx.generate is None`).

### 3.5 Tier-0 / degradation (unchanged, asserted)

If Ollama is down, `_generate_ollama` raises a sanitized `RuntimeError`;
`generate_note_from_source` surfaces it as today for the claude path. ingest
→ search → curate tier-0 are LLM-free and unaffected. No new degradation
logic — just confirm via test.

**Large-source gate (asserted, was R2):** `workflows/ingest.py` raises
`LargeFormatError` and closes the run BEFORE the `ctx.generate` block, and
the threshold (`large_format_threshold_tokens`) is provider-agnostic — so the
ollama path inherits the gate for free, no change needed. Caveat: the gate's
size estimate is a word-count proxy (`len(text.split())`), not a real
tokenizer, so a source under the gate can still exceed a small `num_ctx`.
The gate guards against pathological sizes; the retry loop + configurable
`num_ctx` cover the tight-budget case.

## 4. Testing

Mirror `tests/infrastructure/test_llm_provider.py`, mocking the boundary
(`requests.post`) — never the internal functions:

1. Valid JSON in `message.content` → `NoteContentInput` returned, 1 call.
2. First response invalid JSON/schema, second valid → 2 calls, success,
   `error_context` present in the 2nd payload's system message.
3. All `max_retries+1` invalid → `ValueError`, message includes last error.
4. `requests` raises (Ollama down) → `RuntimeError`, message sanitized
   (no raw URL/secret leakage).
5. Payload assertion: `format == "json"` (default path), `model` equals
   configured model, `stream is False`, system message contains the template
   system prompt.
6. `_llm_is_configured` returns `True` for `provider: ollama` — construct
   settings with `provider="ollama"` explicitly (mirror the `model_copy`
   pattern at `test_llm_provider.py:135-139`); do NOT rely on the
   `tmp_settings` fixture default (which may be `claude` for the existing
   claude tests).
7. Validation parity: a payload that would only pass WITH taxonomy context
   still succeeds (proves bare `NoteContentInput(**data)`, no context — same
   as claude).

All tests offline (no real Ollama). Existing claude tests must stay green.

## 5. Ripple (exhaustive)

| Target | Change |
|--------|--------|
| `infrastructure/llm_provider.py` | **`import requests`** (P0, missing today) + `_generate_ollama` + branch swap |
| `infrastructure/context.py` | `_llm_is_configured` ollama case + docstring reword |
| `core/config.py` + `config/install.yaml.example` | `ProvidersConfig.ollama_num_ctx`, `ollama_timeout_s` (NOT system.yaml) |
| `config/user.yaml.example` | document ollama provider + model |
| `tests/infrastructure/test_llm_provider.py` | new tests (§4) |
| `docs/product-audit/12-provider-coherence.md` | mark local-first LLM tier implemented |
| `PROJECT-STATUS.md` | F5 resolved (ollama) ; debt table |
| `SESSION-CONTEXT.md` | open question #6 resolved for ollama |
| `docs/FUTURE-WORK.md` | note ollama LLM done; openai still "do not implement partially" |
| Out of scope (chantier B) | openai, `providers.mode`, wizard, OpenRouter, hot-swap, reranker/embedding |

**Deferred decision (named, not accidental):** neither the claude nor the
ollama path records `token_count`/`provider` into `tool_logs` (the claude
path discards `message.usage` today). The run-tracking infra exists
(`insert_tool_log`, `get_workflow_run_cost`) but per-provider token accounting
is intentionally NOT introduced here — it belongs to chantier B's provider
seam to do uniformly. This keeps slice A from touching the monitoring layer.

## 6. Risks / open points (post-review)

- **R1 — RESOLVED → design decision (§3.2):** default `format: "json"`;
  full-schema is an optional, version-gated optimization. Retry loop is the
  validity source of truth. No open question remains.
- **R2 — RESOLVED → asserted (§3.5):** upstream `LargeFormatError` gate is
  provider-agnostic and fires before `generate`, protecting ollama for free.
  Documented caveat: the gate uses a word-count proxy, so `num_ctx` +
  retry still matter for tight budgets.
- **R3 — model not pulled (residual, accepted):** if `llm.model` isn't
  pulled, Ollama returns an error → surfaces as sanitized `RuntimeError`
  (not a cryptic 404). Acceptable for v1 (user runs `ollama pull`); a test
  asserts the error is sanitized and non-cryptic.
- **R4 — RESOLVED:** hardcoded temperature does not contradict any
  documented principle (§12.7 is about provider/key selection, not
  generation hyperparameters). Kept YAGNI.
