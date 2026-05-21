# EgoVault — Getting Started

> From zero to your first note in 10 minutes.

---

## 1. Prerequisites

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **Ollama** — [ollama.com/download](https://ollama.com/download) (free, local, handles embeddings)
- **Claude Desktop** — [claude.ai/download](https://claude.ai/download) (your LLM — uses your existing subscription)

---

## 2. Clone and install

```bash
git clone https://github.com/Vincent-20-100/egovault.git
cd egovault

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies (one of)
pip install -e .[tier1,tech-watch]        # plain pip
uv sync --all-extras                       # if you use uv (recommended)
```

> **Important on `uv`:** always use `uv sync --all-extras`, never bare `uv sync`
> — `trafilatura` (web extraction), `feedparser` + `huggingface_hub`
> (tech-watch) are *optional extras* the code imports; bare `uv sync` prunes
> them and breaks the env. See `docs/user-guide/02-installation.md`.

---

## 3. Set up Ollama (embeddings — and optionally local note generation)

EgoVault needs an embedding model. Ollama runs locally — your data never leaves
your machine.

```bash
# Start Ollama (keep it running in background)
ollama serve

# Pull the embedding model (~274 MB, one-time download)
ollama pull nomic-embed-text
```

**Optional — local note generation (F5, fully offline, zero API key):**

```bash
# Recommended (best FR + structured JSON adherence, ~4.7 GB, needs ~7 GB RAM)
ollama pull qwen2.5:7b-instruct
# RAM-tight fallback (~1.9 GB, ~3 GB RAM, lower quality)
ollama pull qwen2.5:3b-instruct
```

Then in `config/user.yaml`:

```yaml
llm:
  provider: ollama
  model: qwen2.5:7b-instruct
```

> **Three provider personas** (see `docs/user-guide/04-providers.md`):
> - **Local-first** (0 keys): Ollama for both embed and LLM — what we just set up
> - **MCP-only** (0 keys): your Claude/GPT subscription via MCP handles LLM work, Ollama covers embeddings only
> - **Cloud LLM**: Anthropic API key in `install.yaml`, Ollama still for embeddings

---

## 4. Initialize user directory

The user directory stores your data (DB, media) and vault (Markdown notes).
It lives **outside** the code repo so your data is never mixed with source code.

```bash
# From the egovault repo root:
python scripts/setup/init_user_dir.py
```

This creates:

```
../egovault-user/
├── data/
│   ├── vault.db          ← SQLite database (created on first use)
│   └── media/            ← downloaded audio/video files
└── vault/
    ├── notes/            ← Markdown notes (Obsidian-compatible)
    └── .obsidian/        ← Obsidian config (pre-configured)
```

It also creates two config files in `config/`:
- `install.yaml` — paths to your user directory (auto-filled)
- `user.yaml` — embedding/LLM provider preferences (defaults work out of the box)

**Verify** that `config/install.yaml` has the correct path:

```yaml
paths:
  user_dir: "C:/Users/YourName/path/to/egovault-user"
```

---

## 5. Quick sanity check

```bash
# Verify everything is wired correctly
python -m pytest tests/ -x -q
```

If tests pass, the installation is good.

---

## 6. Connect Claude Desktop (MCP)

EgoVault exposes its tools to Claude via the Model Context Protocol.
Claude Desktop becomes your LLM — no API key needed, your subscription does the work.

### Find your config file

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Add the EgoVault server

Open the file and add (or merge into) the `mcpServers` section:

**Windows:**

```json
{
  "mcpServers": {
    "egovault": {
      "command": "C:/Users/YourName/path/to/egovault/.venv/Scripts/python",
      "args": ["C:/Users/YourName/path/to/egovault/mcp/server.py"]
    }
  }
}
```

**macOS/Linux:**

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

> Replace the paths with your actual egovault repo location.

### Restart Claude Desktop

After saving, restart Claude Desktop. You should see **"egovault"** in the MCP tools panel (hammer icon at the bottom of the chat).

### Verify the connection

Ask Claude:

> "Call get_workflow_guide() to see how EgoVault works."

If it returns the workflow guide, you're connected.

---

## 7. Your first ingest: a YouTube video

Let's ingest the 3Blue1Brown video on GPTs as a test source.

Ask Claude Desktop:

> "Ingere cette vidéo YouTube dans mon vault : https://www.youtube.com/watch?v=wjZofJX0v4M"

Claude will call `ingest_youtube()` which:
1. Downloads subtitles (or transcribes the audio)
2. Splits the transcript into chunks
3. Embeds each chunk with Ollama
4. Stores everything in your vault database

This takes 1-3 minutes depending on your machine.

---

## 8. Create your first note

Once ingested, ask Claude:

> "Liste mes sources avec list_sources(). Puis lis la source avec get_source() et rédige une note de synthèse."

Claude will:
1. Call `list_sources()` to find the ingested video
2. Call `get_source(uid)` to read the full transcript
3. **Draft a note himself** (title, summary, body, tags)
4. Show you the draft for approval
5. Call `create_note()` to save it

Your note appears as a Markdown file in `egovault-user/vault/notes/`.

---

## 9. Search your vault

Now that you have content, try semantic search:

> "Cherche dans mon vault tout ce qui parle d'attention mechanism."

Claude calls `search()` and returns the most relevant chunks from your sources and notes.

For better precision on French content with exact-keyword queries, enable the
hybrid retrieval mode in `config/system.yaml`:

```yaml
curate:
  use_hybrid_retrieval: true   # cosine + BM25 (FTS5) fused via RRF
```

This complements pure cosine semantic search with lexical (keyword) recall —
see `docs/user-guide/06-search-and-curate.md` for when and why.

---

## 10. Open in Obsidian (optional)

If you use [Obsidian](https://obsidian.md/):

1. Open Obsidian
2. "Open folder as vault" → select `egovault-user/vault/`
3. Your notes appear with tags, backlinks, and graph view

---

## Architecture overview

```
You (Claude Desktop)
  │
  │  MCP protocol (stdio)
  │
  ▼
┌──────────────┐     ┌──────────┐
│  mcp/server  │────▶│  tools/  │──── chunk, embed, search, create_note...
│  (routing)   │     │workflows/│
└──────────────┘     └────┬─────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌────────┐ ┌──────────┐
        │  Ollama  │ │ SQLite │ │  vault/  │
        │(embed)   │ │  (DB)  │ │(Markdown)│
        └──────────┘ └────────┘ └──────────┘
```

**Key insight:** Claude Desktop IS your LLM. It reads sources, synthesizes notes,
and calls EgoVault tools. No API key needed — your Claude subscription does the work.
Ollama only handles the embedding vectors (turning text into searchable numbers).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: core` | Run from the egovault repo root, or use the venv python |
| `FileNotFoundError: install.yaml` | Run `python scripts/setup/init_user_dir.py` |
| `Connection refused` (Ollama) | Start Ollama: `ollama serve` |
| MCP tools don't appear | Check paths in `claude_desktop_config.json`, restart Claude Desktop |
| Embedding fails | Verify: `ollama list` should show `nomic-embed-text` |
| Tests fail with `sqlite_vec` | Run `pip install sqlite-vec` in your venv |
| `No module named 'feedparser'` / `'trafilatura'` after `uv sync` | Use `uv sync --all-extras` (see §2 note) |
| Local note generation fails: `tag must contain only ASCII characters` | Already auto-fixed since 2026-05-21 (slugify in provider); update your install |
| Note generation slow / RAM swap | Use `qwen2.5:3b-instruct` instead of 7b (set in `user.yaml`) — see `04-providers.md` |
| Search results imprecise on French | Enable `curate.use_hybrid_retrieval: true` in `system.yaml` — see `06-search-and-curate.md` |
| Console shows mojibake (`é` → `Ã©`) | Display-only on Windows. Stored bytes are clean UTF-8. Verify with `python -X utf8`. |

For deeper troubleshooting see `docs/user-guide/12-troubleshooting.md`.

---

## What's next?

- **Ingest more sources** — YouTube, PDFs, web pages, raw text
- **Build your knowledge graph** — create concept notes linking multiple sources
- **Configure your provider** — local Ollama, cloud (Anthropic), or hybrid →
  `docs/user-guide/04-providers.md`
- **Tune retrieval** — escalation thresholds, hybrid RRF →
  `docs/user-guide/06-search-and-curate.md`
- **Full reference** — `docs/user-guide/` covers concepts, configuration, CLI,
  MCP, Obsidian, maintenance, troubleshooting in detail.
