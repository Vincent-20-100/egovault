# 11 — Maintenance

The boring (but load-bearing) chapter. Everything you may need to do once
EgoVault is in real use.

## Re-embedding

**When:** you change `system.yaml` `embedding.model` or `embedding.dims`. Or
you upgrade Ollama's `nomic-embed-text` to a new version with different
behavior.

**Why:** existing embeddings were computed with the old model and don't share
the same vector space as the new one. Mixing them = nonsense distances.

**How:**

```bash
# 1. (optional but recommended) back up the DB first
cp egovault-user/data/vault.db egovault-user/data/vault.db.pre-reembed

# 2. ensure Ollama is up and the new model is pulled
ollama list
ollama pull nomic-embed-text                # or your replacement model

# 3. run reembed
python scripts/reembed.py
```

The script:
1. Drops `chunks_vec` and `notes_vec`
2. Recreates them via `init_db` (with current `embedding.dims`, cosine metric)
3. Re-embeds every chunk (from `chunks.content`) and note (from
   `notes.docstring`) via the configured provider
4. Updates `db_metadata` with the new provider/model/dims

**Caveats** (tracked in `.meta/audits/2026-05-17-pre-reinit-audit.md` SCRIPT-M1):
- The script drops vec tables BEFORE confirming the embedding provider is
  reachable. If Ollama is down mid-run you end up with empty vec tables.
  → Always verify Ollama before running it.
- No backup of `vault.db` is automatic. Make one yourself.

## FTS5 backfill (automatic)

When you upgrade to a version of EgoVault that ships FTS5 (or after
running `init_db` on a DB that pre-dates FTS5), the FTS mirror tables
auto-populate from the existing rows on first startup. No action needed.

If you ever want to **rebuild** the FTS index from scratch:

```bash
sqlite3 egovault-user/data/vault.db "DELETE FROM chunks_fts; DELETE FROM notes_fts;"
# Then any process that calls build_context() will trigger backfill:
python -m cli.main status
```

The backfill is idempotent — running it twice does nothing the second time.

## Backups

Two distinct backup targets:

### `vault/notes/` (text — easy)

It's a private git repo by design. Cron a daily commit + push:

```bash
#!/usr/bin/env bash
cd ~/Documents/egovault-user/vault
git add -A
git diff --quiet --cached || git commit -m "snapshot $(date -I)"
git push --quiet
```

### `data/vault.db` (binary — copy the file)

SQLite's file is self-contained. Three options:

| Method | Pros | Cons |
|---|---|---|
| `cp vault.db ~/backups/vault-$(date +%F).db` | trivial, atomic when DB is quiet | doesn't lock the DB; can race during writes |
| `sqlite3 vault.db ".backup ~/backups/vault-$(date +%F).db"` | online backup, safe during writes | requires `sqlite3` CLI |
| `litestream` | continuous replication to S3/etc. | extra moving part |

Recommended: nightly `.backup` to a synced folder (Dropbox, iCloud). The DB
grows ~10 MB per 100 text sources; a year of daily snapshots is small.

## Run tracking and monitoring

Every workflow execution has a `run_id` (UUID4 via `contextvars`). Inspect:

```bash
# CLI
egovault status

# FastAPI (when the api server is running)
curl http://localhost:8000/monitoring/runs?limit=20
curl http://localhost:8000/monitoring/runs/<run_id>
curl http://localhost:8000/monitoring/cost?from=2026-05-01
```

`tool_logs` in `.system.db` records every tool call's `duration_ms`,
`token_count` (when provider returns it), `provider`, and `status`. Useful
for spotting slow tools or expensive LLM calls.

## OpenTimestamps (antériorité proofs)

For knowledge-IP timestamping (vision specs, key audits), EgoVault uses
OpenTimestamps. Only `v0.X.0` semver tags are stamped.

```bash
git push origin v0.X.0
bash scripts/timestamp-release.sh v0.X.0
git add .timestamps/ && git commit -m "chore: add OTS proofs for v0.X.0"
git push
```

Full guide: `docs/TIMESTAMPS.md`. Existing OTS proofs (v0.1.0, v0.2.0, v0.3.0)
live in `.timestamps/`.

> **Hard rule that affects maintenance:** never rewrite git history of a
> commit that is an ancestor of an OTS-tagged commit. That changes the
> tagged commit's SHA and invalidates the `.ots` proof. See
> `.meta/GUIDELINES.md` § Git commits and the 2026-05-18 history-cleanup
> precedent.

## Dependency updates

```bash
# uv (recommended)
git pull
uv sync --all-extras
python -m pytest tests/ -q

# pip
pip install -e ".[tier1,tech-watch]" --upgrade
```

After every dep bump, run the full suite. If `pyproject.toml` adds a new
optional extra, `--all-extras` picks it up automatically.

## Test suite hygiene

The suite has been audited and is **deterministic** (no order-dependence) as
of 2026-05-17:

```bash
python -m pytest tests/ -q
```

Expected: ~500+ passed, ≤1 skipped, 0 failed.

If you see "permission denied" warnings about `.pytest_cache` — harmless,
ignore (cache write-back issue on Windows).

## Cleaning up stale files

```bash
# stale __pycache__ folders
find . -type d -name __pycache__ -exec rm -rf {} +

# stale OTS .ots if you accidentally re-stamped
# DO NOT delete .ots files for valid tags — they're the proof
```

## Disk-space inspection

```bash
du -sh egovault-user/data            # DB + media
du -sh egovault-user/vault           # notes (git repo)
du -sh egovault-user/data/media      # the heavy bit — audio/video downloads
```

If `data/media/` is huge, consider purging media files for sources you've
finished processing (transcripts persist in the DB; the audio file can be
deleted).

## What's next

- [12 — Troubleshooting](12-troubleshooting.md): when things go wrong
- [03 — Configuration](03-configuration.md): the flags that drive maintenance
- `.meta/audits/` — historical post-mortems (real-ingest, RRF experiment, etc.)
