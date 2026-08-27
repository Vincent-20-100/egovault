from unittest.mock import patch, MagicMock
from core.schemas import NoteCandidate, NoteResult, Note, ChunkResult


def test_mcp_list_note_candidates(tmp_settings):
    import mcp.server as srv

    cand = NoteCandidate(
        uid="cand-1",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c1"],
        label="Cand 1",
        status="queued",
        model_version="v2",
        created_at="2026-08-15",
    )
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._list_note_candidates_tool", return_value=[cand]) as mock_tool:
        result = srv.list_note_candidates(source_uid="s1", status="queued")

    mock_tool.assert_called_once()
    assert len(result) == 1
    assert result[0]["uid"] == "cand-1"


def test_mcp_claim_note_candidate(tmp_settings):
    import mcp.server as srv

    cand = NoteCandidate(
        uid="cand-1",
        source_uid="s1",
        sequence_index=0,
        chunk_uids=["c1"],
        label="Cand 1",
        status="in_progress",
        claimed_by="mcp_agent",
        model_version="v2",
        created_at="2026-08-15",
    )
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._claim_note_candidate_tool", return_value=cand) as mock_tool:
        result = srv.claim_note_candidate("cand-1", session_id="mcp_agent", is_human=False)

    mock_tool.assert_called_once()
    assert result["status"] == "in_progress"
    assert result["claimed_by"] == "mcp_agent"


def test_mcp_create_note_from_candidate(tmp_settings):
    import mcp.server as srv

    note = Note(
        uid="note-conv-1",
        source_uid="s1",
        slug="note-conv-1",
        title="Note Converted",
        docstring="Docstring",
        body="Body text of adequate length.",
        date_created="2026-08-15",
        date_modified="2026-08-15",
        tags=["tag-cand"],
        candidate_uid="cand-1",
    )
    note_res = NoteResult(note=note, markdown_path="/path/note-conv-1.md")
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._create_note_from_candidate_tool", return_value=note_res) as mock_tool:
        result = srv.create_note_from_candidate(
            candidate_uid="cand-1",
            title="Note Converted",
            docstring="Docstring",
            body="Body text of adequate length.",
            tags=["tag-cand"],
        )

    mock_tool.assert_called_once()
    assert result["note"]["candidate_uid"] == "cand-1"


def test_mcp_skip_note_candidate(tmp_settings):
    import mcp.server as srv

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._skip_note_candidate_tool", return_value={"candidate_uid": "cand-1", "status": "skipped"}) as mock_tool:
        result = srv.skip_note_candidate("cand-1")

    mock_tool.assert_called_once()
    assert result["status"] == "skipped"


def test_mcp_get_chunks(tmp_settings):
    import mcp.server as srv

    chunks = [
        ChunkResult(uid="c1", position=0, content="Content 1", token_count=5),
        ChunkResult(uid="c2", position=1, content="Content 2", token_count=5),
    ]
    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server._get_chunks_tool", return_value=chunks) as mock_tool:
        result = srv.get_chunks(["c1", "c2"])

    mock_tool.assert_called_once()
    assert len(result) == 2
    assert result[0]["uid"] == "c1"


def test_mcp_review_note(tmp_settings):
    import mcp.server as srv

    note = Note(
        uid="note-1",
        source_uid="s1",
        slug="note-1",
        title="Note 1",
        docstring="Doc",
        body="Body of valid length.",
        date_created="2026-08-15",
        date_modified="2026-08-15",
        tags=["tag-1"],
        review_status="reviewed",
    )
    mock_ctx = MagicMock()
    mock_ctx.db.get_note.return_value = note

    with patch("mcp.server.settings", tmp_settings), \
         patch("mcp.server.ctx", mock_ctx), \
         patch("mcp.server._update_note_tool"):
        result = srv.review_note("note-1", review_status="reviewed")

    assert result["review_status"] == "reviewed"
