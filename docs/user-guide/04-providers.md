# 04 — Providers

EgoVault uses three external services (LLM, embedding, transcription) and you
can mix them. The provider strategy was deliberately designed so that **one
API key (or zero) unlocks the full stack** — never 4 different bills.

> Background: `docs/product-audit/12-provider-coherence.md` for the original
> rationale, and `.meta/audits/2026-05-19/synthesis-retrieval-sota-2026-05-19.md`
> for the SOTA cross-check.

## The four personas

| Persona | Embedding | LLM (note gen) | Transcription | Keys | When to pick |
|---|---|---|---|:-:|---|
| **Local-first (F5)** | Ollama `nomic-embed-text` | Ollama `qwen2.5:7b-instruct` (or 3b) | faster-whisper (local) | **0** | Privacy-first; offline; no per-token bill; ~6–7 GB RAM available |
| **MCP-only** | Ollama `nomic-embed-text` | n/a (Claude via MCP does it) | faster-whisper | **0** | You have Claude Desktop / Code; your subscription covers all "intelligence" |
| **Hybrid (cloud LLM)** | Ollama (local) | Claude API | faster-whisper | **1** (Anthropic) | Best quality on FR notes; fast; pay-per-token |
| **Cloud (future)** | OpenAI | OpenAI / OpenRouter | (Whisper API) | **1** | Reserved — `openai` provider raises NotImplementedError today; see chantier B |

## Choosing — decision tree

```
Do you want zero ongoing cost AND offline capability?
├── YES → Local-first or MCP-only
│         ├── Have a Claude Desktop subscription you'll use anyway? → MCP-only (recommended)
│         └── No subscription / want autonomous note gen?         → Local-first (F5)
└── NO  → Best note quality / fastest gen?
          ├── Have an Anthropic API key?                          → Hybrid (cloud LLM)
          └── Want OpenRouter / multi-model?                      → wait for chantier B
```

## Configuration matrix

| Persona | `user.yaml` `llm.provider` | `install.yaml` keys | Notes |
|---|---|---|---|
| Local-first | `ollama` | none | `model: qwen2.5:7b-instruct` (or 3b fallback) |
| MCP-only | any (not invoked) | none | Internal note gen disabled; MCP client composes notes and calls `create_note` |
| Hybrid | `claude` | `anthropic_api_key` | `model: claude-sonnet-4-6` etc. |

## Local-first deep-dive (F5)

Shipped 2026-05-17. The `_generate_ollama` path mirrors the Claude path's
template/validation/retry contract exactly.

### Model recommendations

| Model | Disk | RAM (working set) | FR quality | Notes |
|---|---|---|---|---|
| **`qwen2.5:7b-instruct`** (target) | ~4.7 GB | ~6–7 GB | very good | Best size/quality for FR + structured JSON adherence. Default recommendation. |
| `qwen2.5:3b-instruct` (RAM-safe fallback) | ~1.9 GB | ~3 GB | good | When 7B causes swap / OOM. Lower precision but still usable. |
| `gemma3:1b` | ~0.8 GB | ~1.5 GB | poor for structured output | **Not recommended** — too small to honor the note schema reliably. |
| `mistral:7b-instruct`, `llama3.1:8b-instruct` | similar | similar | comparable | Acceptable but Qwen2.5 generally beats them on JSON adherence. |

### Performance expectations

- **First call**: 30–60 s (Ollama loads the model into RAM)
- **Subsequent calls**: 50–100 s per note on a Ryzen 7 / 8-core CPU
- **Worst case (3 retries)**: 200–250 s per note (when the LLM produces invalid
  JSON or rejected tags on first attempts)
- **Validated**: 22/25 notes generated successfully on first pass on a 25-source
  French corpus (88%); after the tag-slugify follow-up (2026-05-21), 25/25 (100%).
  See `.meta/audits/2026-05-20-real-notegen-test-results.md`.

### Tag normalization (transparent)

The local model sometimes emits accented French tags (`systèmes`,
`décentralisation`) that violate the vault's ASCII-only tag rule. EgoVault
**auto-slugifies** tags in both providers (NFKD → ASCII → lowercase → kebab) at
generation time, so `["Systèmes", "Décentralisation"]` becomes
`["systemes", "decentralisation"]` — no retry, no failure. The same
normalization runs on the Claude path for strict provider parity.

### Running it

1. `ollama pull qwen2.5:7b-instruct`
2. Set `user.yaml`:
   ```yaml
   llm: { provider: ollama, model: qwen2.5:7b-instruct }
   ```
3. Verify: `python -m cli.main status` reports `LLM: ollama / qwen2.5:7b-instruct`.
4. Trigger note generation either via MCP (`generate_note_from_source(uid)`),
   via `auto_generate_note: true` in `user.yaml` (auto on ingest), or via the
   CLI on demand.

## MCP-only deep-dive

The leanest possible setup. EgoVault provides:
- Embeddings (Ollama local — required for search)
- Storage (SQLite + Markdown vault)
- Search/curate tools (deterministic, no LLM needed at tier 0)
- All ingest pipelines (audio/PDF/web/YouTube)

Your MCP client (Claude Desktop, Claude Code, Cursor) provides the
"intelligence":
- Reading sources via `get_source(uid)`
- Composing notes via its own context window
- Calling `create_note(content)` to save your approved draft

This is the **MCP-first principle**: most users need zero API keys because
their existing LLM subscription already pays for the intelligence.

Setup: see [09-mcp.md](09-mcp.md).

## Hybrid (cloud LLM) deep-dive

Use when you want the best note-generation quality without local model
latency, and you already pay for Anthropic API access.

```yaml
# user.yaml
llm:
  provider: claude
  model: claude-sonnet-4-6           # or claude-haiku-4-5 for cheaper / faster
```

```yaml
# install.yaml
providers:
  anthropic_api_key: sk-ant-api03-...
  ollama_base_url: http://localhost:11434  # still needed for embeddings
```

Pricing reference: a 25-source FR corpus costs roughly $0.15–0.70 (Haiku 4.5)
to $0.50–2 (Sonnet 4.6) for full note generation, depending on source length.
Real-world test data: `.meta/audits/2026-05-20-real-notegen-test-results.md`.

## What's NOT supported today

- **OpenAI** provider for either LLM or embedding (raises `NotImplementedError`).
- **OpenRouter** unified proxy.
- A **setup wizard** that lets you swap personas interactively.
- **`providers.mode: local | cloud | hybrid`** as a single high-level dial.

All four are part of **chantier B** (the broader provider-management spec —
see SESSION-CONTEXT open question 10.4). Slice A (the Ollama LLM provider)
was shipped intentionally as a vertical to validate the architecture before
the broader abstraction.

## What's next

- [05 — Ingest](05-ingest.md): the workflows that feed your sources
- [06 — Search and curate](06-search-and-curate.md): how queries reach your data
- [07 — Notes](07-notes.md): generation, approval, lifecycle
