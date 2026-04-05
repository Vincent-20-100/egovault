"""
MCP server for EgoVault v2.

Exposes tools/ via the Model Context Protocol (FastMCP).
All business logic lives in tools/ — this file is routing only.
"""

import sys
import importlib.util
import site
from pathlib import Path as _Path

from core.config import load_settings
from core.schemas import SearchFilters
from tools.media.compress import compress_audio as _compress_audio_tool
from tools.media.fetch_subtitles import fetch_subtitles as _fetch_subtitles_tool
from tools.media.transcribe import transcribe as _transcribe_tool
from tools.text.chunk import chunk_text as _chunk_text_tool
from tools.text.embed import embed_text as _embed_text_tool
from tools.vault.create_note import create_note as _create_note_tool
from tools.vault.update_note import update_note as _update_note_tool
from tools.vault.finalize_source import finalize_source as _finalize_source_tool
from tools.vault.search import search as _search_tool
from tools.export.typst import export_typst as _export_typst_tool
from tools.export.mermaid import export_mermaid as _export_mermaid_tool
from infrastructure.db import get_note as _get_note
from infrastructure.db import get_source as _get_source_db
from infrastructure.db import list_notes as _list_notes_db
from infrastructure.db import list_sources as _list_sources_db

try:
    settings = load_settings()
except FileNotFoundError:
    settings = None  # type: ignore[assignment] — overridden by tests via patch()

# Import FastMCP from the installed mcp package (not this local mcp/ package).
# The local `mcp/` directory shadows the installed `mcp` pip package.
# Strategy: temporarily remove project-root paths from sys.path AND clear the
# local mcp module cache so the installed package is found; then restore the
# local mcp and mcp.server references so this module keeps working correctly.
_project_root_abs = _Path(__file__).parent.parent.resolve()

def _resolves_to_project_root(p: str) -> bool:
    try:
        return _Path(p).resolve() == _project_root_abs
    except Exception:
        return False

_removed_paths = [(i, p) for i, p in enumerate(sys.path) if _resolves_to_project_root(p)]
for _i, _p in reversed(_removed_paths):
    sys.path.pop(_i)

# Save and clear local mcp module references
_local_mcp = sys.modules.pop("mcp", None)
_local_mcp_server = sys.modules.pop("mcp.server", None)
# Clear any other mcp submodules from local package (they have no __file__ in site-packages)
_other_local_mcp = {k: sys.modules.pop(k) for k in list(sys.modules)
                    if (k.startswith("mcp.") and k not in ("mcp.server",)
                        and sys.modules.get(k) is not None
                        and getattr(sys.modules.get(k), "__file__", None) is not None
                        and str(_project_root_abs) in str(getattr(sys.modules.get(k), "__file__", "")))}

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    # No-op fallback for test environments where FastMCP is not needed
    class _NoOpMCP:  # type: ignore[no-redef]
        def __init__(self, name: str):
            self._name = name

        def tool(self):
            def decorator(fn):
                return fn
            return decorator

        def run(self):
            raise RuntimeError("FastMCP not installed")

    FastMCP = _NoOpMCP  # type: ignore[misc]
finally:
    # Restore project-root paths
    for _i, _p in _removed_paths:
        sys.path.insert(_i, _p)
    # Restore the local mcp and mcp.server module references so that this
    # file continues to be importable as mcp.server (not overwritten by the
    # installed package's mcp.server).
    if _local_mcp is not None:
        sys.modules["mcp"] = _local_mcp
    if _local_mcp_server is not None:
        sys.modules["mcp.server"] = _local_mcp_server

mcp = FastMCP("egovault")


@mcp.tool()
def chunk_text(text: str) -> list[dict]:
    """
    Split text into overlapping chunks per system.yaml:chunking config.

    When to use: Rarely called directly via MCP. This is used internally by ingest
    workflows. Call it if you have raw text you want to split before embedding.

    What to call next: embed_text() on each chunk content to get vectors.
    """
    results = _chunk_text_tool(text, settings.system)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
def embed_text(text: str) -> list[float]:
    """
    Embed a text string using the configured provider (Ollama or OpenAI).
    Returns a flat list of floats. No DB write.

    When to use: Rarely called directly — embedding is handled automatically
    by create_note and update_note. Use this for custom embedding workflows.

    What to call next: Nothing — this is a utility tool.
    """
    return _embed_text_tool(text, settings)


@mcp.tool()
def search(query: str, filters: dict | None = None, mode: str = "chunks") -> list[dict]:
    """
    Semantic search over the vault.
    mode='chunks': chunk-level RAG — searches source content (transcripts, PDFs).
    mode='notes' : note-level semantic search — searches your written notes.

    When to use: The starting point for any knowledge retrieval task.
    Use mode='chunks' to find raw source material for a new note.
    Use mode='notes' to find existing notes on a topic.

    What to call next:
    - After mode='chunks': get_source(source_uid) to read the full source.
    - After mode='notes': get_note(uid) to read the full note.
    """
    search_filters = SearchFilters(**(filters or {}))
    results = _search_tool(query, settings, search_filters, mode)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
def transcribe(file_path: str, language: str = "fr") -> dict:
    """
    Transcribe a local audio or video file to text.

    When to use: When the user has a local audio/video file to process.
    The file must be under the configured media directory.

    What to call next: chunk_text() on the transcript, then embed each chunk.
    Or use the ingest_audio API endpoint for the full automated pipeline.
    """
    from core.security import validate_file_path
    validated = validate_file_path(file_path, [settings.media_path])
    if validated is None:
        raise ValueError("File path not allowed — must be under media directory")
    result = _transcribe_tool(str(validated), language)
    return result.model_dump(mode="json")


@mcp.tool()
def compress_audio(file_path: str, bitrate_kbps: int = 12) -> dict:
    """
    Compress an audio file to a low-bitrate format.

    When to use: Before transcription to reduce file size and speed up processing.
    The file must be under the configured media directory.

    What to call next: transcribe() on the compressed file.
    """
    from core.security import validate_file_path
    validated = validate_file_path(file_path, [settings.media_path])
    if validated is None:
        raise ValueError("File path not allowed — must be under media directory")
    result = _compress_audio_tool(str(validated), bitrate_kbps)
    return result.model_dump(mode="json")


@mcp.tool()
def fetch_subtitles(youtube_url: str, language: str = "fr") -> dict:
    """
    Fetch subtitles for a YouTube video (auto-generated or manual).

    When to use: When the video has existing subtitles and you want to skip transcription.
    Falls back to transcription automatically if no subtitles are found.

    What to call next: chunk_text() on the subtitle text, then embed each chunk.
    Or use the ingest_youtube API endpoint for the full automated pipeline.
    """
    result = _fetch_subtitles_tool(youtube_url, language)
    return result.model_dump(mode="json")


@mcp.tool()
def export_typst(note_uid: str) -> dict:
    """
    Export a note to Typst format for PDF generation.

    When to use: When the user wants a formatted PDF version of a note.
    Requires Typst to be installed on the system.

    What to call next: Nothing — this is a terminal export action.
    """
    result = _export_typst_tool(note_uid, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def export_mermaid(note_uid: str | None = None, tag: str | None = None) -> dict:
    """
    Export note relationships to a Mermaid diagram (note_uid or tag filter).

    When to use: To visualize connections between notes or explore a topic cluster.

    What to call next: Nothing — this is a terminal export action.
    """
    result = _export_mermaid_tool(settings, note_uid, tag)
    return result.model_dump(mode="json")


@mcp.tool()
def get_note(uid: str) -> dict:
    """
    Retrieve the full content of a note by UID.

    When to use: After list_notes() or search(mode='notes') returns a note UID,
    call this to read its full title, docstring, body, and tags.

    What to call next: update_note() to edit it, or export_typst() to export it.
    """
    note = _get_note(settings.vault_db_path, uid)
    if note is None:
        raise ValueError(f"Note '{uid}' not found")
    return note.model_dump(mode="json")


@mcp.tool()
def finalize_source(source_uid: str) -> dict:
    """
    Mark a source as 'vaulted' after its note has been created and reviewed.

    When to use: After create_note() and the user has reviewed and approved the note.
    This is the final step of the note creation workflow.

    What to call next: Nothing — the source is now archived.
    """
    result = _finalize_source_tool(source_uid, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def create_note(source_uid: str, content: dict) -> dict:
    """
    Create a new note from source content.

    When to use: After reading a source (via get_source) and synthesizing its key ideas.
    Always call list_notes() first to check no similar note already exists.
    The note content (NoteContentInput) must be approved by the user before calling.

    Expected workflow:
    1. search(query, mode='chunks') → find relevant source chunks
    2. get_source(source_uid) → read full source content
    3. list_notes() → check for existing notes on this topic
    4. Draft NoteContentInput → show to user for approval
    5. create_note(source_uid, content) → create the note
    6. finalize_source(source_uid) → archive the source

    content dict fields:
    - title (str, 3-200 chars): note title
    - docstring (str, max 300 chars): 3-line summary: what, why, thesis
    - body (str): main note content in Markdown
    - note_type (str|None): synthese | concept | reflexion
    - source_type (str|None): youtube | audio | pdf
    - tags (list[str]): 1-10 kebab-case tags in French, no accents
    - url (str|None): only for source-less notes
    """
    from core.schemas import NoteContentInput, NoteSystemFields
    from core.uid import generate_uid, make_unique_slug
    from infrastructure.db import get_vault_connection
    from datetime import date

    db = settings.vault_db_path
    conn = get_vault_connection(db)
    existing_slugs = {row[0] for row in conn.execute("SELECT slug FROM notes").fetchall()}
    conn.close()

    content_input = NoteContentInput(**content)
    today = date.today().isoformat()
    system_fields = NoteSystemFields(
        uid=generate_uid(),
        date_created=today,
        source_uid=source_uid if source_uid else None,
        slug=make_unique_slug(content_input.title, existing_slugs),
    )
    result = _create_note_tool(content_input, system_fields, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def get_source(uid: str) -> dict:
    """
    Retrieve a full source record by UID, including its transcript.

    When to use: After search() returns a chunk, call get_source(chunk.source_uid)
    to read the full source context (title, URL, full transcript) before drafting a note.
    This is the main tool for gathering content to write a note.

    What to call next: create_note() after reading and synthesizing the source content.
    """
    source = _get_source_db(settings.vault_db_path, uid)
    if source is None:
        raise ValueError(f"Source '{uid}' not found")
    return source.model_dump(mode="json")


@mcp.tool()
def list_notes(
    limit: int = 20,
    offset: int = 0,
    note_type: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """
    Browse notes in the vault.

    When to use: To check for existing notes on a topic before creating a new one
    (avoid duplicates). Also useful to list notes for review, export, or bulk update.
    Filter by note_type (synthese, concept, reflexion) or tags.

    What to call next: get_note(uid) to read the full content of a specific note.
    """
    results = _list_notes_db(settings.vault_db_path, note_type, tags, limit, offset)
    return [n.model_dump(mode="json") for n in results]


@mcp.tool()
def list_sources(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[dict]:
    """
    Browse sources in the vault.

    When to use: To find sources awaiting note creation (use status='rag_ready'),
    or to review all ingested sources. Status values: raw, rag_ready, vaulted.

    What to call next: search(query, mode='chunks') to explore a source's content
    semantically, or get_source(uid) to read its full transcript directly.
    """
    results = _list_sources_db(settings.vault_db_path, status, limit, offset)
    return [s.model_dump(mode="json") for s in results]


@mcp.tool()
def update_note(uid: str, fields: dict) -> dict:
    """
    Update editable fields on an existing note.

    When to use: After reviewing a note (via get_note) and wanting to improve the
    body, fix the title, add a rating, or update tags.

    Editable fields: title, docstring, body, note_type, source_type, rating (1-5), url.
    System fields (uid, date_created, source_uid, generation_template) are ignored.

    What to call next: finalize_source(source_uid) if the associated source is ready
    to be archived as vaulted.
    """
    result = _update_note_tool(uid, fields, settings)
    return result.model_dump(mode="json")


@mcp.tool()
def get_workflow_guide() -> str:
    """
    Return the recommended MCP workflow for EgoVault.

    When to use: At the start of a session to understand the intended tool sequence,
    or when unsure how to proceed with a user's request.
    """
    return """
EgoVault MCP Workflow Guide
===========================

EgoVault is a personal knowledge vault. You (the LLM) orchestrate note creation
by calling tools in sequence. EgoVault provides the building blocks; you provide
the intelligence.

## Core workflow: Source → Note

1. DISCOVER: search(query, mode='chunks')
   → Find relevant source chunks by semantic similarity.

2. READ: get_source(source_uid)
   → Read the full source record including transcript/content.
   → Also available: list_sources(status='rag_ready') to find all unprocessed sources.

3. CHECK: list_notes(tags=[...]) or search(query, mode='notes')
   → Verify no similar note already exists before creating one.

4. DRAFT: Compose NoteContentInput
   → title, docstring (3 lines: what/why/thesis), body (Markdown), tags (French kebab-case)
   → Show the draft to the user for approval before creating.

5. CREATE: create_note(source_uid, content)
   → Persists the note and embeds it into notes_vec automatically.

6. FINALIZE: finalize_source(source_uid)
   → Archives the source as 'vaulted'. Final step of the workflow.

## Editing an existing note

1. get_note(uid) → read current content
2. Propose changes to user
3. update_note(uid, fields) → apply changes and re-embed automatically

## Browsing

- list_sources(status='rag_ready') → sources ready for note creation
- list_notes(note_type='synthese') → browse by type
- search(query, mode='notes') → semantic note search

## Key rules

- Tags must be French, lowercase, kebab-case, no accents (e.g. 'biais-cognitifs')
- Always show note draft to user before calling create_note
- finalize_source only after the note is reviewed and approved
- Never expose or log API keys
"""


if __name__ == "__main__":
    mcp.run()
