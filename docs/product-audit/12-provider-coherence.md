# 12. Provider coherence — unified API key principle

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 12.1 Problem

EgoVault uses multiple external services, each potentially requiring its own API key:

| Service | Current provider | Alternative |
|---------|-----------------|-------------|
| **Embedding** | Ollama (local) | OpenAI API |
| **LLM** (summarize, internal path) | Ollama (local) | OpenAI API, Anthropic API |
| **Transcription** | faster-whisper (local) | — |
| **Reranking** (specced) | Ollama (local) | Cohere API, others |
| **OCR** (future, section 11) | chandra (local) | Datalab API |

If each service uses a different provider, a user could need **4-5 separate API keys** from different vendors. This is a terrible UX — especially for users who just want to "pay for convenience" without managing multiple accounts.

## 12.2 Design principle

**One API key should unlock the full stack.** A user who configures an OpenAI key should get embeddings + LLM + (potentially) other services through that single account. A user who runs everything locally with Ollama should need zero keys.

## 12.3 Provider personas

| Persona | Config | Keys needed | Services |
|---------|--------|-------------|----------|
| **Local-first** | Ollama + faster-whisper + chandra (local) | 0 | Everything runs on-device. Needs GPU for chandra. |
| **Ollama + cloud LLM** | Ollama for embeddings, OpenAI/Anthropic for LLM | 1 | Best balance: fast local embeddings, smart cloud LLM. |
| **Full cloud** | OpenAI for everything (or OpenRouter) | 1 | Simplest setup. Pay-per-token. No GPU needed. |
| **MCP-only** | No internal LLM needed | 0 (for LLM) | The user's Claude/GPT subscription handles all intelligence via MCP. EgoVault only needs an embedding provider. |

## 12.4 The MCP-first advantage

EgoVault's MCP-first design is a major asset here. When the user connects via Claude Desktop, Cursor, or any MCP client:

```
User's LLM subscription (Claude Pro, GPT Plus, etc.)
  → pays for all "intelligence" work (summarize, draft notes, suggest tags)
  → EgoVault only needs: embedding provider + extraction provider
  → Ollama covers both locally, for free
```

**The MCP path means most users need zero API keys.** The internal LLM path (Priority B) is an optional bonus for users who want autonomous note generation without MCP.

## 12.5 Claude Pro/Max subscription — current limitations

A common question: can users with a Claude Pro ($20/mo) or Max ($100-200/mo) subscription use their existing plan as EgoVault's LLM provider?

**Current answer: not directly.** The Claude Pro/Max subscription provides access to `claude.ai` and Claude Code CLI, but does **not** expose a reusable API key. The Anthropic API (`console.anthropic.com`) is a separate product with its own pay-per-token billing.

**However**, via MCP, the user's subscription already covers all LLM work — Claude calls EgoVault tools, and the subscription pays for Claude's reasoning. This is the recommended path.

**Watch for:** if Anthropic ever includes API access in Pro/Max subscriptions, this would be a significant unlock for the internal LLM path. Monitor Anthropic's pricing page.

## 12.6 OpenRouter as a unified proxy

[OpenRouter](https://openrouter.ai/) is a multi-model API proxy: one account, one API key, access to Claude, GPT, Llama, Mistral, and dozens of other models. Its API is OpenAI-compatible.

**Relevance for EgoVault:** if the user wants cloud LLM + cloud embeddings with a single account, OpenRouter could serve as the unified provider. This requires `llm_provider.py` and `embedding_provider.py` to support OpenRouter's endpoint format (already OpenAI-compatible, so likely minimal work).

**This should be explored during the Provider Management brainstorming** (see 10.4).

## 12.7 Recommended configuration UX

```yaml
# install.yaml — simplified provider config
providers:
  # Option 1: all local (default)
  mode: local                  # local | cloud | hybrid

  # Option 2: single cloud provider
  mode: cloud
  cloud_provider: openai       # openai | anthropic | openrouter
  api_key: sk-...              # one key for everything

  # Option 3: mix
  mode: hybrid
  embedding: ollama            # local embeddings (fast, free)
  llm: openai                  # cloud LLM (smart, paid)
  llm_api_key: sk-...
```

The `egovault setup` wizard (CLI, see section 7.3) would guide the user through this choice with clear trade-offs explained.

## 12.8 Implications for extraction provider

If the user has configured a cloud provider (e.g., OpenAI), the extraction provider should **not** require a separate Datalab API key for chandra. Options:
- Tier 0-1 (builtin/markitdown) work without any key — preferred default
- Tier 2 (chandra) local mode works with GPU, no key needed
- Tier 2 (chandra) API mode needs a Datalab key — this is acceptable as an **opt-in premium** feature, clearly documented as a separate paid service

**Principle:** the base experience (ingest + search + notes) must work with the user's single configured provider. OCR via Datalab API is an explicit opt-in.
