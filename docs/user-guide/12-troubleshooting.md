# 12 — Troubleshooting

Known pitfalls. Most are documented elsewhere in this guide; this chapter
collects them in one place for fast lookup.

## Installation / environment

### `No module named 'trafilatura'` (or `feedparser`, or `huggingface_hub`)

You ran a bare `uv sync` instead of `uv sync --all-extras`. These deps are
optional extras the code imports — bare sync prunes them.

```bash
uv sync --all-extras
```

This is a project-wide hard rule (see `.meta/GUIDELINES.md` § Environment).

### `No module named 'bs4'`

Same root cause as above (`beautifulsoup4` is in `tier1` extra). Fix:
`uv sync --all-extras`.

### `pytest`'s `cache could not write` warnings

Permission issue on `.pytest_cache`. Harmless — tests still run correctly.
Fix the cache permission with `chmod -R u+w .pytest_cache/` or just ignore.

### `ModuleNotFoundError: core` (or `tools`, `workflows`)

You're not running from the repo root, or you forgot to activate the venv.

```bash
cd /path/to/egovault
.venv/Scripts/activate          # Windows
source .venv/bin/activate       # macOS/Linux
python -m cli.main status
```

## Ollama

### `Connection refused` / `ConnectionError` at embed/generate

Ollama daemon isn't running.

```bash
ollama serve                    # in a separate terminal/window
ollama list                     # confirm models are visible
```

If `ollama list` is empty, pull the models you need:

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b-instruct       # if using local LLM
```

### Note generation is extremely slow / system swaps

Qwen2.5 7B Q4 needs ~6–7 GB RAM working set. On a 12 GB machine with a busy
browser, you'll swap.

Mitigations:
- Close heavy apps during generation
- Use the smaller fallback: in `user.yaml`, set `model: qwen2.5:3b-instruct`
- For Anthropic users: switch `llm.provider: claude` and use the cloud path

### Note generation fails with `LLM failed to produce valid NoteContentInput after N attempts`

The local model produced invalid JSON or violated the schema 3 times in a
row. Common cases:

| Cause | Fix |
|---|---|
| Tag with accent (`systèmes`) | **Auto-fixed since 2026-05-21** — update your install if you see this |
| Model too small (`gemma3:1b`) | Switch to `qwen2.5:3b-instruct` or 7b |
| Source content too long | Check `system.yaml` `llm.large_format_threshold_tokens` (default 50000) — sources above this skip auto note-gen |
| Ollama returns unexpected body shape | Captured & retried automatically since `b952d96`; if persistent, check Ollama logs |

The actual validation error is in the exception message — read it to learn
which field failed.

### Model is unloaded between calls (each call takes ~30 s of cold-start)

Ollama unloads models after inactivity. To keep a model warm:

```bash
# Sets the keep-alive to 5 minutes after each call (default ~5 minutes already)
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b-instruct","keep_alive":"30m"}'
```

For batch operations, generate sequentially in a single process (the driver
in `.meta/scratch/notegen_corpus.py` does this).

## Search / retrieval

### Search results imprecise on French content

Enable hybrid retrieval:

```yaml
# system.yaml
curate:
  use_hybrid_retrieval: true
```

This adds BM25 (FTS5) lexical recall alongside cosine via RRF. See
[06-search-and-curate.md](06-search-and-curate.md) for the mechanism.

### `curate()` always escalates to chunks even though notes exist

Check `system.yaml` `curate.escalation_max_distance`. On the validated FR
corpus, relevant notes land 0.27–0.40, so the default `0.5` is fine. If your
embeddings produce larger distances, raise it (e.g. to `0.7`).

### `curate()` returns notes with `distance=2.0`

That's the **BM25-only sentinel** introduced with hybrid retrieval — the doc
matched lexically but not semantically. It's a feature, not a bug:
`escalation_max_distance` correctly treats it as "not cosine-relevant" but
RRF still surfaces it in the top results.

## Ingest

### `Unsupported input` for `.md` file

`_detect_type` only recognizes `.txt`, `.html`, `.htm`, `.pdf`, audio
extensions, and URLs. Workarounds:

1. Rename `.md` → `.txt`
2. Read the file and call the workflow directly:
   ```python
   from workflows.ingest import ingest
   ingest("texte", open("file.md").read(), ctx, title="...")
   ```

Tracked as finding D in `.meta/audits/2026-05-17-real-ingest-test-results.md`.
Fix on the backlog.

### YouTube transcript not found, falls back to Whisper

This is normal — many videos don't have subtitles. Whisper transcribes from
the audio (downloaded by `yt-dlp`). Slower but works.

If `yt-dlp` itself fails (private video, region-locked, etc.), `ingest`
returns `failed` with the error in the row.

### `LargeFormatError` on a long source

The source exceeded `llm.large_format_threshold_tokens` (default 50 000). The
ingest itself succeeded (`status=rag_ready`); only the auto note-gen was
skipped.

To still create a note, use the manual flow (`egovault note create
--from-file ...` or via MCP). The future large-source-synthesis cascade will
handle this automatically.

## Database

### `database is locked` errors (especially in API tests)

Background threads holding the SQLite WAL connection. In tests, mock
`_submit_job` (see `.claude/rules/testing.md`). In production, the issue is
tracked as DB-M3 in the 2026-05-17 audit (connection-cleanup `try/finally`
refactor needed across ~50 functions).

### Hard-delete on a fresh DB raises `no such column: previous_status`

Fixed 2026-05-17 (DB-C1, commit `0434e07`). If you still see this, your DB
predates the schema fix and `init_db` should run a backfill — restart your
EgoVault process.

### `init_db` warns "chunks_vec uses the legacy L2 metric"

Your DB was created before the cosine fix (2026-05-16). Distances are
unreliable. Fix:

```bash
python scripts/reembed.py
```

This drops + recreates the vec tables with the cosine metric and re-embeds.

## Git / commits

### Commit message shows mojibake (`Ã©tape`, `â€"`) after a push

You used accented characters or em-dashes in `git commit -m "..."` via the
Bash tool on Windows. The shell's argv encoding mangles non-ASCII before git
sees them — **persists in history**.

Rule: **plain ASCII only in commit messages.** Use `-`, `"`, `'`. No `é`,
`—`, curly quotes.

If you've already committed corrupted history and need to clean it, see the
2026-05-18 precedent in `.meta/GUIDELINES.md` (`git filter-branch
--msg-filter`, with a hard constraint: never rewrite commits ancestor of an
OTS-tagged commit).

### Console shows mojibake but stored bytes are fine

Windows console encoding ≠ data corruption. Verify via Python:

```bash
python -X utf8 -c "import sqlite3; print(sqlite3.connect('vault.db').execute('SELECT title FROM notes LIMIT 1').fetchone())"
```

Stored bytes are clean UTF-8; only the terminal display is broken. This is
trap #13 in `SESSION-CONTEXT.md`.

### `git status` after `git commit` fails with "unknown option `author=...`"

The `force_git_author` PreToolUse hook used to append `--author=` to the LAST
segment of compound commands. Fixed 2026-05-19 (`2d89f75`) — now injects
after the `commit` keyword. If you still see this, update your install.

## MCP

### "EgoVault tools don't appear in Claude Desktop"

1. Restart Claude Desktop (config is read at launch only)
2. Check `claude_desktop_config.json` uses **absolute paths** with forward
   slashes, no `~`
3. Verify the python in `command` works:
   ```bash
   "C:/Users/.../.venv/Scripts/python.exe" mcp/server.py --help
   ```
4. Check Claude Desktop logs (Help → Show logs) for stderr from the server

### "Destructive tools missing" (delete/purge)

By design — they're gated by `user.yaml` `allow_destructive_ops`. Set to
`true` only when needed, revert after.

## `tech-watch` skill

### `gh CLI not found` during sweep

The skill needs the GitHub CLI for repo discovery. Install:

```bash
# Windows
winget install GitHub.cli
# macOS
brew install gh
# then auth once
gh auth login
```

Then run the sweep again. Without `gh`, only RSS and Reddit sources are
queried (lower signal for code-repo discovery).

### Sweep returns "No new items for theme X"

Two common causes:
1. **`gh` missing** → `GitHubSource` fails silently (most likely)
2. **Keywords too narrow / wrong language register** — current feeds (HN,
   r/MachineLearning, r/LocalLLaMA, Simon Willison) use concrete vocabulary
   (`Qwen`, `RAG`, `quantization`); broad concept keywords like
   "knowledge compiler" won't match. Edit `.meta/research-themes.yaml`.

## Tests

### Suite is slow (~50 s)

Normal. The bulk is `tests/api/` integration tests. To run a subset:

```bash
python -m pytest tests/infrastructure -q              # ~3 s
python -m pytest tests/tools -q                       # ~5 s
python -m pytest tests/ -k "not integration" -q       # ~10 s
```

### "Permission denied" writing to `.pytest_cache`

Harmless. Caused by Windows ACLs. Either ignore or:

```bash
chmod -R u+w .pytest_cache
```

## Where to look when nothing above helps

1. `PROJECT-STATUS.md` § Known technical debt — open issues
2. `SESSION-CONTEXT.md` § Traps to avoid — historical pitfalls
3. `.meta/audits/` — post-mortems and findings
4. `docs/FUTURE-WORK.md` — known limitations marked as future work

If still stuck, open an issue with:
- `egovault status` output
- The exact error message
- `python --version` + `ollama --version` + OS
