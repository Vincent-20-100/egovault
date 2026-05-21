# 05 — Ingest

Ingest = "take a raw artifact and make it searchable + ready for note
generation." The pipeline is the same for every source type — only the
extractor up front changes.

## The pipeline (every source goes through this)

```
1. fetch / extract → raw transcript (text)
2. persist source row (status=raw)
3. chunk text          → N chunks
4. embed each chunk    → vectors (cosine-normalized)
5. populate FTS5       → BM25-searchable
6. update status       → rag_ready
   (optional 7. generate note via LLM → status=draft, awaiting approval)
```

Errors at any stage transition the source to `failed` and preserve the
partial transcript. You can inspect, manually fix, and re-ingest.

## Source types and their extractors

| Type | Extension / input | Extractor | Notes |
|---|---|---|---|
| `youtube` | YouTube URL | `youtube-transcript-api` (subtitles) → `faster-whisper` (fallback if no subs) | Both auto-detected. Whisper is local, GPU-accelerated when available. |
| `audio` | `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac` | `faster-whisper` directly | Language hint via CLI `--language` (default: `fr`) |
| `pdf` | `.pdf` | `pypdf` | Text-only; image-heavy PDFs lose content. Future: chandra OCR (tier-2 extractor, see product audit §11) |
| `texte` | `.txt` or text content via API/MCP | passthrough | Best for already-clean text |
| `html` | `.html`, `.htm` | builtin (`bs4`) or `trafilatura` (tier-1, optional extra) | Configurable via `system.yaml` `web.extraction_tier` |
| `web` | URL | `fetch_web` → 2-tier extraction | SSRF-protected; respects rate limit (`web.min_fetch_interval_seconds`) |

### `.md` is NOT accepted by the CLI

The CLI's `_detect_type` maps only `.txt`/`.html`/etc. `egovault ingest x.md`
raises "Unsupported input." Workaround: read the file into a string and call
the workflow API, or rename to `.txt`. This gap is tracked as a finding in
`.meta/audits/2026-05-17-real-ingest-test-results.md` (finding D).

## CLI usage

```bash
egovault ingest <target> [--title TITLE] [--generate-note/--no-generate-note]
                         [--language fr] [--json] [--verbose]
```

Examples:

```bash
# YouTube — auto-detected by URL pattern
egovault ingest "https://www.youtube.com/watch?v=XJMedY92fK0"

# Local audio
egovault ingest ./recordings/meeting-2026-05-21.mp3 --title "Meeting 2026-05-21"

# PDF book
egovault ingest ./books/ayn-rand-atlas-shrugged.pdf

# Web article (URL — extractor tier from system.yaml)
egovault ingest "https://example.com/article"

# Plain text file with custom title (recommended for clean ingestion)
egovault ingest ./notes/idea.txt --title "Brainstorm desire paths"

# Skip auto-note-gen for this specific ingest (overrides user.yaml default)
egovault ingest ./big-source.pdf --no-generate-note
```

After successful ingest the CLI prints the new source's `uid`, `slug`,
`status` (`rag_ready` on success), and elapsed time. Use `--json` for
scriptable output, `--verbose` for stage-by-stage timings.

## Programmatic ingest (MCP / API / Python)

Inside an LLM session via MCP:

```
ingest_youtube("https://...")
ingest_audio("/path/to/file.mp3")
ingest_pdf("/path/to/file.pdf")
ingest_web("https://...")
ingest_text("Long pasted text...", title="My idea")
```

In Python directly:

```python
from workflows.ingest import ingest
from infrastructure.context import build_context
from core.config import load_settings

ctx = build_context(load_settings())
source = ingest("texte", "Pasted text content here", ctx, title="My idea")
print(source.uid, source.status)
```

The CLI's `_run_ingest` is a thin shell over this same `workflows.ingest`.

## Large sources — the gate

Sources whose token count exceeds `system.yaml` `llm.large_format_threshold_tokens`
(default 50 000) **skip the auto-note-generation step** and raise
`LargeFormatError`. The source still becomes `rag_ready` and is searchable —
only the note auto-gen is gated. You then have two choices:

1. **Manual note** — create a note yourself via MCP or the CLI, citing
   relevant `search` results from the source.
2. **Large source synthesis (future)** — the cascade strategy in
   `.meta/specs/2026-04-06-large-source-synthesis-spec.md` (web-search →
   TOC+chapters → map-reduce → final synthesis). Not yet implemented.

Token estimate uses a fast word-count proxy (`len(text.split())`), not a real
tokenizer, so it under-counts on token-dense text. Tune the threshold
conservatively if you regularly ingest long YouTube transcripts.

## Batch / queue patterns

EgoVault doesn't ship a built-in batch ingester. The recommended pattern is
a shell loop over a list:

```bash
for url in $(cat queue.txt); do
  egovault ingest "$url" --no-generate-note
done
```

For Python automation, see the one-off driver pattern in
`.meta/scratch/notegen_corpus.py` (generated 2026-05-20 for the real-test
corpus) — adapt as needed.

A YAML-driven queue model (`queue.yaml`) is used in some test corpora
(`_corpus-test-20260517/queue.yaml`) but isn't yet a first-class CLI feature.

## Validating an ingest

```bash
# DB-level: counts, status, last-ingested
egovault status

# CLI list
egovault source list

# Drill into one source
egovault source get <uid>
```

If a source is stuck in `failed`, the `error` column on its row holds the
exception message — check via `egovault source get` or the API
`/sources/<uid>` endpoint.

## What's next

- [06 — Search and curate](06-search-and-curate.md): query the corpus you just ingested
- [07 — Notes](07-notes.md): turn sources into notes (the note-gen step)
- [11 — Maintenance](11-maintenance.md): re-ingest after embedding model change
