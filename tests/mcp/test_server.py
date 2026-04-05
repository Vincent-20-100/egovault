import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_embedding, EMBEDDING_DIMS

from core.schemas import (
    ChunkResult, SearchResult, NoteResult, FinalizeResult,
    TranscriptResult, CompressResult, SubtitleResult, ExportResult,
)


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------

def test_mcp_chunk_text_calls_tool(tmp_settings):
    import mcp.server as srv

    chunk = ChunkResult(uid="c1", position=0, content="hello world here", token_count=3)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._chunk_text_tool", return_value=[chunk]) as mock_tool:
        result = srv.chunk_text("hello world here")

    mock_tool.assert_called_once()
    assert len(result) == 1
    assert result[0]["uid"] == "c1"


# ---------------------------------------------------------------------------
# embed_text
# ---------------------------------------------------------------------------

def test_mcp_embed_text_calls_tool(tmp_settings):
    import mcp.server as srv

    mock_ctx = MagicMock()
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx), \
         patch("mcp.server._embed_text_tool", return_value=make_embedding()) as mock_tool:
        result = srv.embed_text("hello")

    # embed_text passes ctx, not settings (G4 — tool receives VaultContext)
    mock_tool.assert_called_once_with("hello", mock_ctx)
    assert len(result) == EMBEDDING_DIMS


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def test_mcp_search_calls_tool(tmp_settings):
    import mcp.server as srv

    sr = SearchResult(content="content", title="title", distance=0.1)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._search_tool", return_value=[sr]) as mock_tool:
        result = srv.search("bitcoin")

    mock_tool.assert_called_once()
    assert len(result) == 1
    assert result[0]["content"] == "content"


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------

def test_mcp_transcribe_calls_tool(tmp_settings, tmp_path):
    import mcp.server as srv
    from pathlib import Path

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    audio_file = media_dir / "audio.mp3"
    audio_file.touch()

    tr = TranscriptResult(text="bonjour", language="fr", duration_seconds=10.0)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._transcribe_tool", return_value=tr) as mock_tool, \
         patch("core.security.validate_file_path", return_value=Path(str(audio_file))):
        result = srv.transcribe(str(audio_file))

    mock_tool.assert_called_once()
    assert result["text"] == "bonjour"


# ---------------------------------------------------------------------------
# compress_audio
# ---------------------------------------------------------------------------

def test_mcp_compress_audio_calls_tool(tmp_settings, tmp_path):
    import mcp.server as srv
    from pathlib import Path

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    audio_file = media_dir / "audio.mp3"
    audio_file.touch()

    cr = CompressResult(output_path="/tmp/out.opus", original_size_bytes=1000, compressed_size_bytes=200)
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._compress_audio_tool", return_value=cr) as mock_tool, \
         patch("core.security.validate_file_path", return_value=Path(str(audio_file))):
        result = srv.compress_audio(str(audio_file))

    mock_tool.assert_called_once()
    assert result["output_path"] == "/tmp/out.opus"


# ---------------------------------------------------------------------------
# fetch_subtitles
# ---------------------------------------------------------------------------

def test_mcp_fetch_subtitles_calls_tool(tmp_settings):
    import mcp.server as srv

    sub = SubtitleResult(text="subtitle text", language="fr", source="subtitles")
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._fetch_subtitles_tool", return_value=sub) as mock_tool:
        result = srv.fetch_subtitles("https://youtube.com/watch?v=abc")

    mock_tool.assert_called_once()
    assert result["text"] == "subtitle text"


# ---------------------------------------------------------------------------
# export_typst
# ---------------------------------------------------------------------------

def test_mcp_export_typst_calls_tool(tmp_settings):
    import mcp.server as srv

    er = ExportResult(output_path="/tmp/note.typ", format="typst")
    mock_ctx = MagicMock()
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx), \
         patch("mcp.server._export_typst_tool", return_value=er) as mock_tool:
        result = srv.export_typst("note-uid-1")

    # export_typst passes ctx (G4)
    mock_tool.assert_called_once_with("note-uid-1", mock_ctx)
    assert result["output_path"] == "/tmp/note.typ"


# ---------------------------------------------------------------------------
# export_mermaid
# ---------------------------------------------------------------------------

def test_mcp_export_mermaid_calls_tool(tmp_settings):
    import mcp.server as srv

    er = ExportResult(output_path="/tmp/graph.md", format="mermaid")
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._export_mermaid_tool", return_value=er) as mock_tool:
        result = srv.export_mermaid(tag="bitcoin")

    mock_tool.assert_called_once()
    assert result["format"] == "mermaid"


# ---------------------------------------------------------------------------
# update_note
# ---------------------------------------------------------------------------

def test_mcp_update_note_calls_tool(tmp_settings):
    import mcp.server as srv
    from core.schemas import NoteResult, Note
    from datetime import date

    note = Note(
        uid="n1", slug="test-note", title="Updated Title", tags=["tag1"],
        body="Updated body.", docstring="Updated docstring.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        rating=4,
    )
    mock_result = NoteResult(note=note, markdown_path="/tmp/test.md")

    mock_ctx = MagicMock()
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx), \
         patch("mcp.server._update_note_tool", return_value=mock_result) as mock_tool:
        result = srv.update_note("n1", {"rating": 4})

    # update_note passes ctx, not settings (G4)
    mock_tool.assert_called_once_with("n1", {"rating": 4}, mock_ctx)
    assert result["note"]["rating"] == 4


# ---------------------------------------------------------------------------
# get_source
# ---------------------------------------------------------------------------

def test_mcp_get_source_returns_source(tmp_settings):
    import mcp.server as srv
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-1", slug="src-1", source_type="youtube",
        status="rag_ready", date_added=date.today().isoformat(),
        title="My Video",
    )

    mock_ctx = MagicMock()
    mock_ctx.db.get_source.return_value = source
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx):
        result = srv.get_source("src-1")

    mock_ctx.db.get_source.assert_called_once_with("src-1")
    assert result["uid"] == "src-1"
    assert result["title"] == "My Video"


def test_mcp_get_source_not_found_raises(tmp_settings):
    import mcp.server as srv

    mock_ctx = MagicMock()
    mock_ctx.db.get_source.return_value = None
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx):
        with pytest.raises(ValueError, match="not found"):
            srv.get_source("nonexistent")


# ---------------------------------------------------------------------------
# list_notes
# ---------------------------------------------------------------------------

def test_mcp_list_notes_returns_notes(tmp_settings):
    import mcp.server as srv
    from core.schemas import Note
    from datetime import date

    note = Note(
        uid="n1", slug="note-1", title="Note 1", tags=["tag1"],
        body="Body content here.", docstring="Desc.",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )

    mock_ctx = MagicMock()
    mock_ctx.db.list_notes.return_value = [note]
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx):
        result = srv.list_notes(limit=10, offset=0)

    mock_ctx.db.list_notes.assert_called_once_with(None, None, 10, 0)
    assert len(result) == 1
    assert result[0]["uid"] == "n1"


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------

def test_mcp_list_sources_returns_sources(tmp_settings):
    import mcp.server as srv
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-1", slug="src-1", source_type="youtube",
        status="rag_ready", date_added=date.today().isoformat(),
    )

    mock_ctx = MagicMock()
    mock_ctx.db.list_sources.return_value = [source]
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx):
        result = srv.list_sources(limit=10, offset=0, status="rag_ready")

    mock_ctx.db.list_sources.assert_called_once_with("rag_ready", 10, 0)
    assert len(result) == 1
    assert result[0]["uid"] == "src-1"


# ---------------------------------------------------------------------------
# get_workflow_guide
# ---------------------------------------------------------------------------

def test_mcp_get_workflow_guide_returns_string(tmp_settings):
    import mcp.server as srv

    with patch("mcp.server.settings", tmp_settings):
        result = srv.get_workflow_guide()

    assert isinstance(result, str)
    assert "create_note" in result
    assert "finalize_source" in result


def test_mcp_generate_note_from_source_calls_tool(tmp_settings):
    import mcp.server as srv
    from unittest.mock import patch
    from core.schemas import NoteResult, Note
    from datetime import date

    note = Note(
        uid="note-mcp", source_uid="src-mcp", slug="note-mcp",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="MCP Note",
        docstring="desc", body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    mock_result = NoteResult(note=note, markdown_path="/vault/note-mcp.md")

    mock_ctx = MagicMock()
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx), \
         patch("mcp.server._generate_note_from_source_tool",
               return_value=mock_result) as mock_tool:
        result = srv.generate_note_from_source("src-mcp")

    # generate_note_from_source passes ctx, not settings (G4)
    mock_tool.assert_called_once_with("src-mcp", mock_ctx, "standard")
    assert result["note"]["status"] == "draft"
