# 08 — CLI reference

The `egovault` CLI is a thin shell over the workflows and tools. Every
command is documented below with its options and a real example.

## Invocation

```bash
# Recommended (always works regardless of PATH state):
python -m cli.main <command> [options]

# Via venv python directly (stable):
.venv/Scripts/python.exe -m cli.main <command>     # Windows
.venv/bin/python -m cli.main <command>              # macOS/Linux

# After `pip install -e .` adds the entry-point script:
egovault <command> [options]
```

Help:

```bash
egovault --help
egovault <command> --help
```

## Global commands

### `status`

Show DB paths, embedding/LLM provider configuration, recent activity.

```bash
egovault status
```

Useful to confirm `user.yaml` and `install.yaml` are loaded correctly.

### `ingest`

Ingest a source. See [05-ingest.md](05-ingest.md) for the full pipeline.

```bash
egovault ingest <target> [--title TITLE]
                         [--generate-note/--no-generate-note]
                         [--language fr]
                         [--json]
                         [--verbose]
```

| Option | Effect | Default |
|---|---|---|
| `target` (positional) | URL or file path; type auto-detected | — |
| `--title` | Title for text/HTML input (otherwise inferred) | inferred |
| `--generate-note / --no-generate-note` | Override `user.yaml` `auto_generate_note` | `user.yaml` value |
| `--language` | Whisper language hint for audio | `fr` |
| `--json` | Output result as JSON (script-friendly) | text |
| `--verbose` | Per-stage timings | off |

### `search`

Raw semantic search (no escalation, no fusion). For curated results, use
`curate`.

```bash
egovault search "<query>" [--mode notes|chunks] [--limit 10] [--filters JSON]
```

| Option | Effect | Default |
|---|---|---|
| `query` | The text query | — |
| `--mode` | Search the notes tier or the chunks tier | `chunks` |
| `--limit` | Max results | 10 |
| `--filters` | JSON `SearchFilters` literal | none |

### `curate`

Librarian retrieval (tier 0 today; tier 1 in the future). Respects
`escalation_*` and `use_hybrid_retrieval`. See [06-search-and-curate.md](06-search-and-curate.md).

```bash
egovault curate "<query>" [--limit 5] [--filters JSON]
```

### `purge`

Hard-delete sources or notes flagged `pending_deletion`. Requires
`allow_destructive_ops: true` in `user.yaml` if invoked via MCP — the CLI is
always allowed.

```bash
egovault purge sources [--older-than 30d]
egovault purge notes
```

## Source commands

### `source list`

```bash
egovault source list [--status STATUS] [--limit 50]
```

Common statuses: `raw`, `rag_ready`, `pending_deletion`, `failed`.

### `source get`

```bash
egovault source get <uid>
```

Returns full row including `transcript` (truncated for display by default).

### `source delete`

```bash
egovault source delete <uid>           # soft — status=pending_deletion
egovault source delete <uid> --hard    # hard — gone (FTS + chunks_vec cleaned)
```

### `source restore`

```bash
egovault source restore <uid>
```

Restores from `pending_deletion` to the previous status.

## Note commands

### `note list`

```bash
egovault note list [--status STATUS] [--note-type TYPE] [--limit 50]
```

Statuses: `draft`, `active`, `pending_deletion`.

### `note get`

```bash
egovault note get <uid>
```

### `note generate`

Run note generation on a source (mid-ingest or after).

```bash
egovault note generate <source_uid> [--template standard]
```

The source must be at `rag_ready` status. The new note starts at `draft`.

### `note create`

Create a note manually from a YAML file.

```bash
egovault note create --from-file ./my-note.yaml
```

Schema of `my-note.yaml`: see [07-notes.md § Manual note YAML format](07-notes.md#manual-note-yaml-format).

### `note approve`

Flip a draft to active.

```bash
egovault note approve <uid>
```

Validates taxonomy fields at this step. Surfaces a clear error if the LLM
proposed an unknown `note_type` or `source_type`.

### `note update`

```bash
egovault note update <uid> [--title T] [--docstring D] [--rating 1-5] [...]
```

Updates `notes_fts` automatically when `title` or `docstring` change.

### `note delete` / `note restore`

```bash
egovault note delete <uid>             # soft delete
egovault note delete <uid> --hard      # hard delete
egovault note restore <uid>
```

## Maintenance

### Re-embed

Drops `chunks_vec` + `notes_vec`, recreates with current `embedding.dims`, and
re-embeds everything from `chunks.content` and `notes.docstring`.

```bash
python scripts/reembed.py
```

Run after changing `embedding.model` or `embedding.dims`. See
[11-maintenance.md](11-maintenance.md).

### OpenTimestamps

```bash
bash scripts/timestamp-release.sh v0.X.0
```

See `docs/TIMESTAMPS.md` for the full timestamping process.

## Output formats

Most commands honor `--json` for machine-readable output:

```bash
egovault ingest "https://..." --json | jq .uid
```

Without `--json`, output uses `rich`-styled tables and panels.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | runtime error (network, LLM, validation, etc.) |
| `2` | usage error (bad flag, missing arg, unsupported input type) |

Errors are printed to stderr in a sanitized form (API keys / paths stripped) —
see `core/sanitize.py`.

## What's next

- [09 — MCP integration](09-mcp.md): expose all of this to Claude / Cursor / etc.
- [12 — Troubleshooting](12-troubleshooting.md): when commands fail
