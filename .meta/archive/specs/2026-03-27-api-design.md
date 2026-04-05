# EgoVault API Layer — Design Spec

**Date:** 2026-03-27
**Status:** Approved — pending implementation plan
**Scope:** `api/` only — frontend/ is a separate spec

---

## Purpose

Expose EgoVault's tools and workflows via HTTP/REST so that human clients (browser, frontend, curl) can interact with the vault without an LLM. Complements `mcp/server.py` which serves LLM clients.

Both layers call the same `tools/` and `workflows/`. Zero business logic duplication.

```
LLM clients (Claude, etc.)          Human clients (browser, frontend)
        ↓                                       ↓
  mcp/server.py                            api/
  (MCP protocol)                       (HTTP/REST)
        ↓                                       ↓
                    tools/ + workflows/
                      (business logic)
                            ↓
                     infrastructure/
                  (vault.db + .system.db)
```

---

## Key Decisions

### Async ingestion with job polling

Ingestion workflows (Whisper transcription, embedding) can take minutes. The API returns a `job_id` immediately and the client polls for completion. Chosen over sync (timeout risk) and WebSockets (overkill for MVP).

### Multipart upload for all file types

Audio, PDF, and video files are uploaded via HTTP multipart. Since the API runs locally (loopback), transfer speed is not a bottleneck — a 2GB video upload over loopback is a local memory copy. Simpler than mixing path-based and upload-based inputs.

Accepted file types (validated by extension in the router):
- Audio: `.mp3`, `.mp4`, `.wav`, `.m4a`, `.ogg`, `.webm`
- PDF: `.pdf`

Unsupported extension → `400 {"detail": "unsupported file type: .xyz"}`.

**File lifecycle:** The router writes the uploaded file to disk before submitting the job to the
ThreadPoolExecutor. This avoids Windows `NamedTemporaryFile` cross-process access issues and
ensures the file exists on a stable path before the worker thread starts.

```
POST /ingest/audio|pdf
→ generate job_id (UUID4)
→ write file to egovault-user/data/media/{job_id}/{original_filename}
→ INSERT job {status: "pending", input: {"filename": "media/{job_id}/{original_filename}"}}
→ executor.submit(run_workflow, job_id, absolute_path)
→ return 202 {"job_id": "..."}
```

If the job fails, the file remains in `media/{job_id}/` for manual inspection. Cleanup is out of
scope for the current implementation.

**Filename sanitisation:** `jobs.input` stores the original client filename for display only.
The actual path on disk is always `media/{job_id}/{sanitized_name}` where `sanitized_name` is
derived from the validated extension only — never constructed from the client-provided filename.
This prevents path traversal attacks.

### ThreadPoolExecutor for job execution

Whisper (CPU-heavy, C++ underneath) releases the GIL during computation. A `ThreadPoolExecutor` runs jobs in separate threads without blocking the FastAPI event loop. One process to launch (vs two for a worker pattern). Sufficient for local MVP.

### Two databases

| File | Location | Contents | Backup |
|---|---|---|---|
| `vault.db` | `egovault-user/data/vault.db` | sources, notes, chunks, *_vec, tags, db_metadata | Required |
| `.system.db` | `egovault-user/data/.system.db` | tool_logs, jobs | Not required |

`vault.db` is user knowledge — must be backed up. `.system.db` is operational state — hidden by default (dot prefix), can be wiped without data loss. `db_metadata` stays in `vault.db` because it describes the sqlite-vec virtual tables in that same file.

**Migration:** `egovault.db` → `vault.db` (rename). `tool_logs` moves from `vault.db` to `.system.db`.

Migration script: `scripts/temp/migrate_db.py` — one-shot, no fallback logic in config. No automatic fallback is implemented.

### No authentication

Local MVP — API binds to `127.0.0.1` only. No auth (local-only).

### Router-based structure

One router per resource. Adding endpoints does not touch other routers. Business logic stays in `tools/` — routers are pure HTTP adapters.

### api/models.py vs core/schemas.py

Routers always return `api/models.py` types — never `core/schemas` objects directly. Conversion
from internal schema to response model is done inside the router. Internal fields not exposed in
the API: `sync_status`, `generation_template`, `source_uid`, and any other fields not listed in
the endpoint shapes below.

---

## Directory Structure

```
api/
├── main.py           ← FastAPI app, router mounting, ThreadPoolExecutor init, startup cleanup
├── models.py         ← Pydantic request/response models (separate from core/schemas.py)
└── routers/
    ├── ingest.py     ← POST /ingest/youtube|audio|pdf
    ├── jobs.py       ← GET /jobs, GET /jobs/{id}
    ├── notes.py      ← GET/PATCH /notes, GET /notes/{uid}
    ├── sources.py    ← GET /sources, GET /sources/{uid}
    ├── search.py     ← POST /search
    └── health.py     ← GET /health

tests/api/
├── __init__.py
├── conftest.py       ← test app + temp DBs
├── test_ingest.py
├── test_jobs.py
├── test_notes.py
├── test_sources.py
├── test_search.py
└── test_health.py
```

---

## Database Changes

### vault.db (renamed from egovault.db)

No schema changes. `tool_logs` removed (moved to `.system.db`).

`core/config.py` additions:
```python
@property
def vault_db_path(self) -> Path: ...   # replaces db_path

@property
def system_db_path(self) -> Path: ...  # egovault-user/data/.system.db
```

`infrastructure/db.py` additions:
```python
def get_vault_connection() -> sqlite3.Connection: ...   # replaces get_connection()
def get_system_connection() -> sqlite3.Connection: ...
```

Both functions must set the following pragmas on every new connection:
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")  # ms — auto-retry on lock instead of raising
```

`WAL` mode allows concurrent readers + one writer, required as soon as ThreadPoolExecutor writes
to the DB while FastAPI handles read requests. `busy_timeout` prevents `OperationalError: database
is locked` under light concurrent load.

### .system.db (new)

```sql
CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,   -- UUID4
    status      TEXT NOT NULL,      -- pending|running|done|failed
    job_type    TEXT NOT NULL,      -- youtube|audio|pdf
    input       TEXT NOT NULL,      -- JSON: {"url": "..."} or {"filename": "..."}
    result      TEXT,               -- JSON: {"note_uid": "...", "slug": "..."}
    error       TEXT,               -- error message if failed
    created_at  TEXT NOT NULL,      -- ISO datetime
    updated_at  TEXT NOT NULL       -- ISO datetime
);

CREATE TABLE tool_logs (
    -- same schema as current vault.db tool_logs (migrated as-is)
    uid         TEXT PRIMARY KEY,
    tool_name   TEXT NOT NULL,
    input_json  TEXT,
    output_json TEXT,
    duration_ms INTEGER,
    status      TEXT NOT NULL,
    error       TEXT,
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## Endpoints

### Ingestion

```
POST /ingest/youtube
Body: {"url": "https://youtube.com/watch?v=..."}
→ 202 {"job_id": "uuid4"}

POST /ingest/audio
Body: multipart/form-data, field: "file"
→ 202 {"job_id": "uuid4"}

POST /ingest/pdf
Body: multipart/form-data, field: "file"
→ 202 {"job_id": "uuid4"}
```

### Jobs

```
GET /jobs?status=pending|running|done|failed&limit=20
→ 200 [{"id", "status", "job_type", "created_at"}, ...]

GET /jobs/{id}
→ 200 {"id", "status", "job_type", "input", "result", "error", "created_at", "updated_at"}
→ 404 if not found
```

### Notes

```
GET /notes?note_type=&tags=&limit=20&offset=0
→ 200 [{"uid", "slug", "title", "note_type", "rating", "tags", "date_created"}, ...]

GET /notes/{uid}
→ 200 {"uid", "slug", "title", "body", "note_type", "source_type",
        "rating", "tags", "date_created", "date_modified"}
→ 404 if not found

PATCH /notes/{uid}
Body: {"rating": 4} | {"tags": ["tag-1", "tag-2"]} | both
→ 200 updated note
→ 404 if not found
→ 422 if validation fails (rating out of range, etc.)
```

### Sources

```
GET /sources?status=&limit=20&offset=0
→ 200 [{"uid", "slug", "source_type", "status", "title", "date_added"}, ...]

GET /sources/{uid}
→ 200 {"uid", "slug", "source_type", "status", "title", "url",
        "transcript", "date_added", "date_source"}
→ 404 if not found
```

`transcript` is returned in full — no truncation or pagination. Local usage assumed; a 2h podcast
transcript (~200 KB) is acceptable over loopback. Revisit if performance becomes an issue.

```
```

### Search

```
POST /search
Body: {"query": "...", "limit": 10}
→ 200 [{"note_uid", "slug", "title", "score", "excerpt"}, ...]
```

Search behavior:
- Mode: note-level search (not raw chunks). The router calls `tools/vault/search` in notes mode.
- `score`: `1 - distance` (normalized 0–1, higher = more relevant).
- `excerpt`: `content` of the highest-scoring chunk belonging to that note.
- `tags` query param format: repeated values — `?tags=tag-1&tags=tag-2` (FastAPI `list[str]`).

### Health

```
GET /health
→ 200 {"api": "ok", "ollama": "up|down", "db": "ok"}
```

Checks: FastAPI reachable (trivial), Ollama ping via `GET http://localhost:11434/` (or configured
host), vault.db connection. Used by the frontend Dashboard status strip.
Never returns 5xx — always 200 with per-component status strings.

---

## Job Lifecycle

```
0. FastAPI startup:
   → UPDATE jobs SET status='failed', error='process restarted'
     WHERE status IN ('pending', 'running')
   (orphaned jobs from a previous crash are marked failed immediately)

1. POST /ingest/*
   → generate job_id (UUID4)
   → write uploaded file to egovault-user/data/media/{job_id}/{original_filename}  [audio/pdf only]
   → INSERT job {status: "pending"} into .system.db
   → executor.submit(run_workflow, job_id, ...)
   → return 202 {"job_id": "..."}

2. ThreadPoolExecutor (separate thread):
   → UPDATE job {status: "running"}
   → call workflow (ingest_youtube / ingest_audio / ingest_pdf)
   → write results to vault.db (source, note, chunks) — vault.db written FIRST
   → success: UPDATE job {status: "done", result: {"note_uid": "...", "slug": "..."}}
   → error:   UPDATE job {status: "failed", error: "..."}

3. Client polls GET /jobs/{id}
   → reads status from .system.db
   → terminates when status is "done" or "failed"
```

**Write ordering:** `vault.db` is written before `.system.db` status is set to `done`. If the
process crashes between the two writes, the job remains `running` and will be marked `failed` at
next startup (step 0). The note may already exist in `vault.db` — this is acceptable (no deduplication on restart).

---

## Error Handling

| Code | Meaning |
|---|---|
| `400` | Invalid input (bad URL format, unsupported file type) |
| `404` | Resource not found (note_uid, source_uid, job_id) |
| `422` | Pydantic validation failure (rating out of range, etc.) |
| `500` | Pipeline error — details in job.error or response body |

All errors return `{"detail": "..."}` (FastAPI default).

---

## Testing Strategy

`tests/api/` mirrors `api/routers/`. Each router is tested independently with mocked `tools/` and `workflows/`.

- **Unit tests**: mock tool calls, verify HTTP status codes and response shapes
- **Integration test**: full job lifecycle — POST /ingest → poll GET /jobs/{id} → verify status "done"
- **Temp DBs**: `conftest.py` creates fresh `vault.db` and `.system.db` per test session

---

## What This Does NOT Cover

- Authentication (local-only, `127.0.0.1`)
- Rate limiting
- WebSockets / SSE for real-time job updates (polling is sufficient for MVP)
- `frontend/` (separate spec)
- `DELETE /notes/{uid}` (pending_deletion workflow — spec section 7.3, requires human confirmation UI)
- Multi-provider embedding (separate chantier per spec section 7.3)
- `POST /chat` — no underlying tool exists yet. Out of current scope. Will be specified in a
  separate chantier once `tools/chat.py` is designed.
