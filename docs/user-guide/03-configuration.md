# 03 — Configuration

EgoVault reads three YAML files at startup. Each has a precise role; mixing
them is a common mistake.

| File | Role | Git status | Edit when |
|---|---|---|---|
| `config/system.yaml` | App-wide defaults: chunking, retrieval, taxonomy, etc. | **Versioned** (committed) | Changing algorithm tuning the whole project should adopt |
| `config/user.yaml` | Your personal preferences: provider choice, language, sync | **Gitignored** | Switching LLM provider, model, language |
| `config/install.yaml` | Machine-specific: filesystem paths, API keys | **Gitignored** | First install, moving folders, rotating API keys |

`init_user_dir.py` writes `user.yaml` + `install.yaml` from the `.example`
counterparts on first run. The `.example` files in the repo are kept up to date
with every option.

All three are validated via Pydantic at startup — missing required fields fail
fast with an explicit error.

---

## `config/system.yaml` reference

### `chunking`

How transcripts are split into chunks before embedding.

```yaml
chunking:
  size: 800       # target tokens per chunk
  overlap: 80     # overlap between consecutive chunks (preserves context across boundaries)
```

Changing these requires a re-ingest of existing sources to take effect (chunks
are persisted with their original split).

### `embedding`

The embedding model used at ingest and query time.

```yaml
embedding:
  dims: 768                          # vector dimensions — must match the model
  provider: ollama                   # only `ollama` implemented today
  model: nomic-embed-text            # any Ollama embedding model
```

**Critical:** changing `model` or `dims` invalidates every existing embedding.
You must run `scripts/reembed.py` after the change. See [11-maintenance.md](11-maintenance.md).

### `llm`

System-wide LLM behavior (provider-independent).

```yaml
llm:
  max_retries: 2                      # provider re-tries on invalid JSON / schema (per attempt)
  large_format_threshold_tokens: 50000  # sources above this skip auto-note-gen (LargeFormatError)
```

The `max_retries` applies to both claude and ollama paths via the same retry
loop in `infrastructure/llm_provider.py`.

### `upload`

Size limits for ingestion APIs.

```yaml
upload:
  max_audio_mb: 500
  max_pdf_mb: 100
  max_text_chars: 500000
```

### `web`

Web ingestion (`fetch_web`).

```yaml
web:
  extraction_tier: 0                   # 0 = builtin (bs4), 1 = trafilatura (requires extra `tier1`)
  max_response_mb: 10                  # max HTTP response size
  timeout_seconds: 30                  # fetch timeout
  min_fetch_interval_seconds: 2        # global rate limit between fetches (anti-burst)
  max_redirects: 5
```

### `curate`

The Librarian / retrieval orchestrator. **Where you tune search quality.**

```yaml
curate:
  escalation_min_notes: 3              # < N relevant notes → escalate to chunks
  escalation_max_distance: 0.5         # "relevant" cosine threshold (calibrated on FR corpus)
  synthesis_max_chars_per_item: 800    # truncate content per source in the assembled synthesis
  use_hybrid_retrieval: false          # true = cosine + BM25 (FTS5) fused via RRF (exp #1)
```

- **`escalation_max_distance`** controls when notes are deemed insufficient.
  With cosine + normalized embeddings, distances ∈ [0,2]. On the validated FR
  corpus, relevant notes land 0.27–0.40, so 0.5 is a comfortable threshold. If
  notes never trigger escalation, lower it. If chunks always fire, raise it.
- **`use_hybrid_retrieval = true`** enables BM25 lexical recall alongside
  cosine, fused via Reciprocal Rank Fusion. Recommended **on** when your queries
  contain exact keywords (proper nouns, technical terms) — see
  [06-search-and-curate.md](06-search-and-curate.md) for the full mechanism and
  empirical results.

### `taxonomy`

User-configurable classification lists. **These are NOT engine constraints** —
the engine validates note fields against whatever you put here.

```yaml
taxonomy:
  note_types:
    - synthese
    - reflexion
    - concept
    # add your own here
  source_types:
    - youtube
    - audio
    - video
    - pdf
    - livre
    - texte
    - html
    - web
    - personnel
  generation_templates:
    - standard   # corresponds to config/templates/generation/standard.yaml
```

Adding a new value = one line here, no code change. Templates require a
matching `.yaml` file in `config/templates/generation/`.

---

## `config/user.yaml` reference

### `embedding`

Your installation's embedding choice (must match `system.yaml` `embedding.dims`).

```yaml
embedding:
  provider: ollama
  model: nomic-embed-text
```

### `llm`

Your LLM provider for note generation.

```yaml
llm:
  provider: ollama                    # claude | ollama
  model: qwen2.5:7b-instruct          # for ollama; for claude: claude-sonnet-4-6 etc.
  auto_generate_note: false           # true = ingest triggers note gen automatically
```

See [04-providers.md](04-providers.md) for the tradeoffs.

### `vault`

Vault behavior.

```yaml
vault:
  content_language: fr                # used for prompts and OS locale
  obsidian_sync: true                 # enable the Obsidian → DB sync watcher
  default_generation_template: standard
```

### `allow_destructive_ops`

```yaml
allow_destructive_ops: false   # MCP safety gate
```

When `false` (default), delete/purge tools are NOT exposed via MCP — your LLM
client can't accidentally wipe your vault. Set to `true` only when you want a
session to be able to delete sources or notes.

---

## `config/install.yaml` reference

### `paths`

Where your data lives. All paths are absolute (or relative to the repo root if
you use the `../` pattern).

```yaml
paths:
  user_dir: "C:/Users/YourName/Documents/egovault-user"
  data_dir: null     # default: user_dir/data
  vault_dir: null    # default: user_dir/vault/notes
  media_dir: null    # default: user_dir/data/media
  db_file: null      # default: user_dir/data/vault.db
```

The four optional overrides exist for users who keep their notes vault in a
synced folder (Dropbox, iCloud) while keeping the DB on a fast local SSD.

### `providers`

Per-install provider tuning and credentials.

```yaml
providers:
  ollama_base_url: http://localhost:11434
  ollama_num_ctx: 8192          # context window for local LLM note generation (F5)
  ollama_timeout_s: 180         # per-request timeout (CPU note gen can be slow)
  openai_api_key: null          # reserved for future provider; not implemented in v1
  anthropic_api_key: null       # required ONLY if user.yaml `llm.provider: claude`
```

**Per-install vs system-wide:** `ollama_num_ctx` / `ollama_timeout_s` live here
(not in `system.yaml`) because they're machine-dependent — a powerful workstation
can afford a larger context window than a laptop.

---

## Worked configurations

### Persona A: fully local (zero key, no internet for LLM work)

```yaml
# user.yaml
embedding: { provider: ollama, model: nomic-embed-text }
llm:       { provider: ollama, model: qwen2.5:7b-instruct }
```
```yaml
# install.yaml — only the path matters here
providers: { ollama_base_url: http://localhost:11434 }
```

### Persona B: MCP-only (your Claude Desktop subscription does everything)

```yaml
# user.yaml — local LLM not needed; Claude via MCP handles it
embedding: { provider: ollama, model: nomic-embed-text }
llm:       { provider: ollama, model: qwen2.5:7b-instruct }   # any value; not invoked
```

Note generation via the EgoVault internal path is unavailable here unless you
configure a real provider — but Claude via MCP can still call `search`,
`curate`, `create_note` (writing notes Claude composed), `ingest_*`.

### Persona C: cloud LLM (Anthropic API key)

```yaml
# user.yaml
embedding: { provider: ollama, model: nomic-embed-text }
llm:       { provider: claude, model: claude-sonnet-4-6 }
```
```yaml
# install.yaml
providers:
  anthropic_api_key: sk-ant-...
  ollama_base_url: http://localhost:11434
```

Full persona table + tradeoffs: [04-providers.md](04-providers.md).

---

## Editing safely

- `system.yaml` changes are committed and visible to teammates.
- `user.yaml` / `install.yaml` are gitignored — your edits stay local.
- After any change, run `python -m cli.main status` to confirm settings load
  cleanly (Pydantic surfaces errors immediately).
- Re-embedding required when: `embedding.model` or `embedding.dims` change.
- Re-init required when: `paths.*` change (move your data first; don't lose it).
