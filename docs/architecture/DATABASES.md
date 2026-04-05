# EgoVault — Database Schemas

> Part of the architecture reference. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full index.

---

## 4. Database — vault.db

`vault.db` contains **user data**. It is the source of truth for the vault. Must be backed up.

### 4.1 Entity-relationship overview

```
sources ──< chunks       (one source → multiple chunks for RAG)
sources ──○ notes        (one source → zero or one note)
notes   ──< note_tags    (many-to-many with tags)
tags    ──< note_tags
db_metadata              (embedding config at index creation time)

Vector tables (sqlite-vec):
chunks_vec   ← one embedding per chunk  (source-level RAG)
notes_vec    ← one embedding per note   (note-level semantic search)
```

**Source lifecycle** (`status` column in `sources`):

| Status | Meaning |
|---|---|
| `raw` | File received in inbox, no processing started |
| `transcribing` | Text extraction in progress (Whisper / Docling) |
| `text_ready` | Transcript available, not yet chunked/embedded |
| `embedding` | Chunking + vector computation in progress |
| `rag_ready` | Chunks embedded, source queryable via RAG. Valid terminal state if no note is created. |
| `pre_vaulted` | **LLM path only.** LLM has generated a note draft, awaiting human validation before DB write. |
| `vaulted` | Note validated and written to the vault. Source archived. |
| `failed` | Processing error — see `tool_logs` in `.system.db` |
| `pending_deletion` | Marked for deletion via `delete_source`. Reversible via `restore_source`. Permanently removed by `purge`. |

**Two paths from `rag_ready` to `vaulted`:**
```
With LLM:    rag_ready → pre_vaulted → vaulted   (LLM generates draft, human validates)
Without LLM: rag_ready ──────────────→ vaulted   (user writes the note manually)
RAG only:    rag_ready                            (no note — permanently valid state)
```
Notes without a source (`reflexion`, `idee`, `personnel`) have no source status — `source_uid IS NULL`.

**Note sync status** (`sync_status` column in `notes`):

| Status | Meaning | Trigger |
|---|---|---|
| `synced` | Note embedding is up to date | Set by workflow after embed_note |
| `needs_re_embedding` | Note body modified, re-embedding queued | Set by vault watcher on file save |
| `embedding` | Re-embedding in progress | Set by embedding worker on pickup |
| `pending_deletion` | Marked for deletion via `delete_note` | Reversible via `restore_note`, permanent via `purge` |

### 4.2 Large format policy

A source exceeding `system.yaml:llm.large_format_threshold_tokens` follows a different path:

**RAG:** runs normally — chunks embedded, source reaches `rag_ready`. Fully queryable.

**Note generation:** blocked. The workflow does not attempt to generate a note from the full transcript. The user has two options:

1. **Write the note manually** — the source stays `rag_ready`, the user creates the note themselves.
2. **Provide an external summary** — the LLM works from this summary + source metadata.

**`rag_ready` without a note is a permanently valid state.** Many large sources may remain in this state indefinitely.

### 4.3 Full schema

```sql
-- ============================================================
-- SOURCES — raw ingested media
-- ============================================================
CREATE TABLE sources (
    uid          TEXT PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    source_type  TEXT NOT NULL,      -- validated against system.yaml:taxonomy.source_types
    status       TEXT NOT NULL DEFAULT 'raw',
    url          TEXT,
    title        TEXT,
    author       TEXT,
    date_added   DATE NOT NULL,
    date_source  DATE,
    media_path   TEXT,
    transcript   TEXT,
    raw_metadata TEXT,
    previous_status TEXT          -- saved before soft delete, restored by restore_source
);

-- ============================================================
-- NOTES — generated units of knowledge (system output)
-- ============================================================
CREATE TABLE notes (
    uid                 TEXT PRIMARY KEY,
    source_uid          TEXT REFERENCES sources(uid),
    slug                TEXT UNIQUE NOT NULL,
    note_type           TEXT,
    source_type         TEXT,
    generation_template TEXT,
                                            -- NULL for manually written notes
                                            -- NOT editable via frontmatter (watcher ignores it)
                                            -- NOT set by the LLM during generation
                                            -- Modifiable ONLY via regeneration workflow
    rating              INTEGER CHECK(rating BETWEEN 1 AND 5),
                                            -- set by user only, never inferred by the LLM
    sync_status         TEXT NOT NULL DEFAULT 'synced',
    title               TEXT NOT NULL,
    docstring           TEXT,
    body                TEXT NOT NULL,
    url                 TEXT,               -- only for notes without a source (source_uid IS NULL)
    date_created        DATE NOT NULL,      -- IMMUTABLE after creation
    date_modified       DATE NOT NULL,
    language            TEXT DEFAULT 'fr',
    previous_sync_status TEXT       -- saved before soft delete, restored by restore_note
);

-- ============================================================
-- CHUNKS — text fragments for RAG (linked to sources, not notes)
-- ============================================================
CREATE TABLE chunks (
    uid          TEXT PRIMARY KEY,
    source_uid   TEXT NOT NULL REFERENCES sources(uid) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    content      TEXT NOT NULL,
    token_count  INTEGER NOT NULL
);

-- ============================================================
-- EMBEDDING DIMENSION — read from system.yaml:embedding.dims
-- Schema is dynamically generated via infrastructure/db.py:_build_schema_sql(dims)
--
-- What breaks if you change the model without the full system:
--   - All existing vectors become incomparable.
--   - sqlite-vec virtual tables cannot ALTER their dimension after creation.
--   - Search results silently wrong with no error.
--
-- Before adding a new embedding provider:
--   1. Implement mismatch detection in core/config.py via db_metadata
--   2. Implement scripts/maintenance/reembed_all.py
--   3. Ensure dimension is a runtime value read from db_metadata
-- ============================================================
CREATE VIRTUAL TABLE chunks_vec USING vec0(
    chunk_uid    TEXT,
    embedding    FLOAT[768]          -- dims from system.yaml:embedding.dims
);

CREATE VIRTUAL TABLE notes_vec USING vec0(
    note_uid     TEXT,
    embedding    FLOAT[768]
);
-- Orphan cleanup: deleting a source cascades to chunks (ON DELETE CASCADE)
-- but NOT to chunks_vec (sqlite-vec limitation).
-- Normal deletion: finalize_source.py handles explicit sync.
-- Bulk cleanup: scripts/maintenance/sync_vectors.py

-- ============================================================
-- DB METADATA — tracks embedding model config
-- ============================================================
CREATE TABLE db_metadata (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL
);
-- INSERT INTO db_metadata VALUES ('embedding_provider', 'ollama');
-- INSERT INTO db_metadata VALUES ('embedding_model', 'nomic-embed-text');
-- INSERT INTO db_metadata VALUES ('embedding_dim', '768');

-- ============================================================
-- TAGS
-- ============================================================
CREATE TABLE tags (
    uid          TEXT PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,  -- kebab-case, no accents, lowercase
    language     TEXT DEFAULT 'fr',
    date_created DATE NOT NULL
);

CREATE TABLE note_tags (
    note_uid     TEXT REFERENCES notes(uid) ON DELETE CASCADE,
    tag_uid      TEXT REFERENCES tags(uid) ON DELETE CASCADE,
    PRIMARY KEY (note_uid, tag_uid)
);
```

### 4.4 Hybrid query patterns

```sql
-- Pattern A1: chunk-level RAG — vaulted sources only
SELECT c.content, c.source_uid, s.title, cv.distance
FROM chunks_vec cv
JOIN chunks c ON c.uid = cv.chunk_uid
JOIN sources s ON s.uid = c.source_uid
JOIN notes n ON n.source_uid = s.uid
JOIN note_tags nt ON nt.note_uid = n.uid
JOIN tags t ON t.uid = nt.tag_uid
WHERE t.name = 'decentralisation'
  AND cv.embedding MATCH vec_f32('[...]')
ORDER BY cv.distance LIMIT 5;

-- Pattern A2: chunk-level RAG — all indexed sources
SELECT c.content, c.source_uid, s.title, s.status, cv.distance
FROM chunks_vec cv
JOIN chunks c ON c.uid = cv.chunk_uid
JOIN sources s ON s.uid = c.source_uid
WHERE cv.embedding MATCH vec_f32('[...]')
ORDER BY cv.distance LIMIT 5;

-- Pattern B: note-level semantic search
SELECT n.title, n.slug, n.note_type, nv.distance
FROM notes_vec nv
JOIN notes n ON n.uid = nv.note_uid
WHERE nv.embedding MATCH vec_f32('[...]')
ORDER BY nv.distance LIMIT 10;
```

---

## 5. Database — .system.db

`.system.db` contains **operational data**. Dot prefix = hidden by default. Can be deleted without losing user data. Do not back up.

### 5.1 Two databases, two roles

| File | Contents | Backup |
|---|---|---|
| `vault.db` | sources, notes, chunks, *_vec, tags, db_metadata | **Required** |
| `.system.db` | tool_logs, workflow_runs, benchmark_runs, jobs, semantic_cache | Not required |

`db_metadata` stays in `vault.db` because it describes the sqlite-vec virtual tables in that same file.

### 5.2 Full schema

```sql
-- ============================================================
-- WORKFLOW RUNS — cross-tool correlation within a single workflow
-- ============================================================
CREATE TABLE workflow_runs (
    run_id      TEXT PRIMARY KEY,
    workflow    TEXT NOT NULL,
    -- values: "ingest_youtube" | "ingest_audio" | "ingest_pdf" | "mcp_session" | "api_request"
    status      TEXT NOT NULL,
    -- values: "running" | "success" | "failed"
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    source_uid  TEXT   -- optional link to the ingested source in vault.db
);

-- ============================================================
-- TOOL LOGS — every tool call is logged (migrated from vault.db)
-- ============================================================
CREATE TABLE tool_logs (
    uid          TEXT PRIMARY KEY,
    run_id       TEXT REFERENCES workflow_runs(run_id),
    tool_name    TEXT NOT NULL,
    input_json   TEXT,
    output_json  TEXT,
    duration_ms  INTEGER,
    token_count  INTEGER,   -- embedding + LLM tokens if available, NULL otherwise
    status       TEXT NOT NULL,   -- "success" | "failed"
    error        TEXT,
    timestamp    TEXT NOT NULL
);

-- ============================================================
-- BENCHMARK RUNS — results from the RAG quality benchmark framework
-- ============================================================
CREATE TABLE benchmark_runs (
    run_id      TEXT PRIMARY KEY,
    component   TEXT NOT NULL,   -- "search" | "chunk" | "all"
    metrics     TEXT NOT NULL,   -- serialized JSON of BenchmarkResult
    passed      INTEGER NOT NULL,
    timestamp   TEXT NOT NULL
);

-- Tables reserved for future extensions:
-- benchmark_ratings  ← human or LLM feedback on a run
-- benchmark_golden   ← cases promoted from the UI as "perfect answer"

-- ============================================================
-- JOBS — asynchronous workflow execution via the API
-- ============================================================
CREATE TABLE jobs (
    job_id      TEXT PRIMARY KEY,
    workflow    TEXT NOT NULL,
    status      TEXT NOT NULL,   -- "pending" | "running" | "success" | "failed"
    input       TEXT,            -- JSON (original filename for display, never used as path)
    result      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- ============================================================
-- SEMANTIC CACHE — avoids full RAG on previously handled queries
-- ============================================================
CREATE TABLE semantic_cache (
    cache_uid     TEXT PRIMARY KEY,
    query_text    TEXT NOT NULL,
    query_hash    TEXT NOT NULL,        -- MD5 hex for exact O(1) lookup
    mode          TEXT NOT NULL,        -- "chunks" | "notes"
    filters_json  TEXT,
    result_ids    TEXT NOT NULL,        -- JSON list of chunk_uid or note_uid
    rerank        INTEGER NOT NULL,     -- 0 | 1
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    hit_count     INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE semantic_cache_vec USING vec0(
    cache_uid  TEXT PRIMARY KEY,
    embedding  FLOAT[768]                -- same dims as vault.db
);

CREATE INDEX idx_cache_hash ON semantic_cache(query_hash);
CREATE INDEX idx_cache_expires ON semantic_cache(expires_at);
CREATE INDEX idx_cache_mode ON semantic_cache(mode);
```

### 5.3 Migrating tool_logs from vault.db

**Script:** `scripts/temp/001_move_tool_logs_to_system_db.py`

```
1. Creates .system.db with the new schema
2. Copies vault.db:tool_logs → .system.db:tool_logs (run_id = NULL, token_count = NULL for history)
3. DROP TABLE tool_logs in vault.db
```

One-shot script, no fallback.
