"""
API response and request models.

These are separate from core/schemas.py — they define the HTTP contract.
Internal fields (sync_status, generation_template, source_uid, etc.) are
never exposed. Conversion from internal schemas happens inside each router.
"""

from pydantic import BaseModel, Field


# ============================================================
# JOBS
# ============================================================

class JobResponse(BaseModel):
    id: str
    status: str
    job_type: str
    input: dict | None = None
    result: dict | None = None
    error: str | None = None
    created_at: str
    updated_at: str | None = None


class JobListItem(BaseModel):
    id: str
    status: str
    job_type: str
    created_at: str


# ============================================================
# INGESTION
# ============================================================

class IngestYoutubeRequest(BaseModel):
    url: str
    auto_generate_note: bool | None = None


class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    url: str | None = None
    source_type: str | None = None
    auto_generate_note: bool | None = None


class IngestWebRequest(BaseModel):
    url: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=200)
    auto_generate_note: bool | None = None


class IngestResponse(BaseModel):
    job_id: str


# ============================================================
# NOTES
# ============================================================

class NoteListItem(BaseModel):
    uid: str
    slug: str
    title: str
    note_type: str | None
    rating: int | None
    tags: list[str]
    date_created: str


class NoteDetail(BaseModel):
    uid: str
    slug: str
    title: str
    body: str
    note_type: str | None
    source_type: str | None
    rating: int | None
    tags: list[str]
    date_created: str
    date_modified: str
    status: str = "active"


class NotePatch(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    tags: list[str] | None = None
    status: str | None = None


# ============================================================
# SOURCES
# ============================================================

class SourceListItem(BaseModel):
    uid: str
    slug: str
    source_type: str
    status: str
    title: str | None
    date_added: str


class SourceDetail(BaseModel):
    uid: str
    slug: str
    source_type: str
    status: str
    title: str | None
    url: str | None
    transcript: str | None
    date_added: str
    date_source: str | None


# ============================================================
# SEARCH
# ============================================================

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(10, ge=1, le=50)


class SearchResultResponse(BaseModel):
    note_uid: str
    slug: str
    title: str
    score: float
    excerpt: str


# ============================================================
# HEALTH
# ============================================================

# ============================================================
# MONITORING
# ============================================================

class WorkflowRunResponse(BaseModel):
    run_id: str
    workflow: str
    status: str
    started_at: str
    ended_at: str | None = None
    source_uid: str | None = None


class ToolLogResponse(BaseModel):
    uid: str
    run_id: str | None = None
    tool_name: str
    duration_ms: int | None = None
    token_count: int | None = None
    provider: str | None = None
    status: str
    error: str | None = None
    timestamp: str


class WorkflowRunDetailResponse(BaseModel):
    run: WorkflowRunResponse
    tool_logs: list[ToolLogResponse]


class WorkflowRunCostResponse(BaseModel):
    run_id: str
    workflow: str
    tool_count: int
    total_tokens: int
    total_duration_ms: int


# ============================================================
# HEALTH
# ============================================================

class HealthResponse(BaseModel):
    api: str
    ollama: str
    db: str
