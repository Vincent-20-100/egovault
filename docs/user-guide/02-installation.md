# 02 — Installation

A complete install in ~10 minutes. For the abridged version, see
[`GETTING-STARTED.md`](../GETTING-STARTED.md).

## Prerequisites

- **Python 3.10+** — `python --version`
- **Git** — for cloning + the private notes vault git repo
- **Ollama** — local embedding (mandatory) and optionally local LLM (recommended).
  Download: [ollama.com](https://ollama.com/)
- **(optional) `uv`** — faster Python package manager. Install:
  `pipx install uv` or `pip install uv`. Recommended over plain pip.
- **(optional) `gh` CLI** — only required for the `tech-watch` SOTA scan skill.
  Install: `winget install GitHub.cli` (Windows) / `brew install gh` (macOS).

### Disk and RAM budget

| Component | Disk | RAM |
|---|---|---|
| Python + deps | ~500 MB | minimal |
| Ollama runtime | ~50 MB | minimal |
| `nomic-embed-text` (embeddings, mandatory) | ~274 MB | ~500 MB when loaded |
| `qwen2.5:7b-instruct` (LLM, recommended) | ~4.7 GB | ~6–7 GB working set on CPU |
| `qwen2.5:3b-instruct` (LLM, RAM-safe fallback) | ~1.9 GB | ~3 GB |
| `vault.db` | grows with corpus (~10 MB / 100 sources of text) | — |

## 1. Clone

```bash
git clone https://github.com/Vincent-20-100/egovault.git
cd egovault
```

## 2. Virtual environment

```bash
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (git-bash):
source .venv/Scripts/activate
# macOS / Linux:
source .venv/bin/activate
```

## 3. Install dependencies — pick ONE

### Option A — `uv` (recommended)

```bash
uv sync --all-extras
```

> **MANDATORY: `--all-extras`.** EgoVault's code imports `trafilatura` (web
> extraction, optional extra `tier1`), `feedparser` and `huggingface_hub`
> (tech-watch, optional extra `tech-watch`). A bare `uv sync` PRUNES these and
> breaks the env (`No module named 'trafilatura'`). This rule is locked in
> [`.meta/GUIDELINES.md`](../../.meta/GUIDELINES.md) § Environment.

### Option B — plain `pip`

```bash
pip install -e ".[tier1,tech-watch]"
```

Both options give you the same fully-functional environment.

## 4. Set up Ollama

```bash
# Start the daemon (keep it running in the background)
ollama serve

# Pull the mandatory embedding model (~274 MB)
ollama pull nomic-embed-text

# Optional but recommended — local note generation (F5)
ollama pull qwen2.5:7b-instruct           # ~4.7 GB
# OR the RAM-safe fallback:
ollama pull qwen2.5:3b-instruct           # ~1.9 GB
```

If you only want EgoVault as a knowledge backend for Claude Desktop / Claude
Code via MCP, you can skip the LLM model — your subscription handles
generation. See [04-providers.md](04-providers.md).

## 5. Initialize your user directory

```bash
python scripts/setup/init_user_dir.py
```

This creates `../egovault-user/` (configurable via `--target`) and writes
`config/user.yaml` + `config/install.yaml` if they don't exist. Both are
gitignored — personal to your install.

Verify `config/install.yaml`:

```yaml
paths:
  user_dir: "C:/Users/YourName/Documents/egovault-user"  # absolute path
```

## 6. Configure your providers

Edit `config/user.yaml`:

```yaml
embedding:
  provider: ollama
  model: nomic-embed-text     # leave default unless you ran reembed

llm:
  provider: ollama            # claude | ollama | (openai = future)
  model: qwen2.5:7b-instruct  # for ollama; fallback: qwen2.5:3b-instruct
  auto_generate_note: false   # true = generate notes automatically post-ingest
```

For the cloud LLM path, edit `config/install.yaml` instead:

```yaml
providers:
  anthropic_api_key: sk-ant-...   # only needed for provider: claude
  ollama_base_url: http://localhost:11434
  ollama_num_ctx: 8192            # context window for local LLM (F5)
  ollama_timeout_s: 180           # per-request timeout (CPU can be slow)
```

Full reference: [03-configuration.md](03-configuration.md). Provider tradeoffs:
[04-providers.md](04-providers.md).

## 7. Sanity check

```bash
# Tests should all pass (~500+ tests, ~50–60 s)
python -m pytest tests/ -q

# Ollama is up and has the right models
curl -s http://localhost:11434/api/tags

# CLI works and reads the config
python -m cli.main status
```

If `pytest` is green and `egovault status` prints DB paths and model info, you're done.

## 8. (Optional) Connect an MCP client

See [09-mcp.md](09-mcp.md) for Claude Desktop and Claude Code setup.

## Updating to a new version

```bash
git pull
uv sync --all-extras           # re-syncs deps, picks up new extras
python -m pytest tests/ -q     # confirm green on your machine
```

If a new EgoVault version changes the embedding model or dimensions, you'll
need to re-embed: see [11-maintenance.md](11-maintenance.md) § Re-embedding.

## What's next

- [03 — Configuration](03-configuration.md): full reference of every flag.
- [05 — Ingest](05-ingest.md): your first real ingest.
- [12 — Troubleshooting](12-troubleshooting.md): install-time pitfalls.
