import json
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.commands.sources import app

runner = CliRunner()


def _make_source(uid="suid-1", slug="ma-source", source_type="youtube", status="rag_ready"):
    from core.schemas import Source
    return Source(
        uid=uid, slug=slug, source_type=source_type, status=status,
        url="https://youtube.com/watch?v=test", title="Ma Source",
        date_added="2026-03-30",
    )


def test_source_list_default():
    sources = [_make_source()]
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._list_sources", return_value=sources):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "ma-source" in result.output


def test_source_list_json_mode():
    sources = [_make_source()]
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._list_sources", return_value=sources):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["slug"] == "ma-source"


def test_source_list_filter_by_status():
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._list_sources", return_value=[]) as mock_list:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list", "--status", "rag_ready"])
    assert result.exit_code == 0
    mock_list.assert_called_once()


def test_source_get_success():
    source = _make_source()
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._get_source", return_value=source):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["get", "suid-1"])
    assert result.exit_code == 0
    assert "Ma Source" in result.output


def test_source_get_not_found():
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._get_source", return_value=None):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["get", "nonexistent"])
    assert result.exit_code == 1


def test_source_get_verbose_shows_transcript():
    from core.schemas import Source
    source = Source(
        uid="suid-1", slug="ma-source", source_type="youtube", status="rag_ready",
        url="https://youtube.com/watch?v=test", title="Ma Source",
        date_added="2026-03-30", transcript="Transcription complète du contenu.",
    )
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._get_source", return_value=source):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["get", "suid-1", "--verbose"])
    assert result.exit_code == 0
    assert "Transcription" in result.output


def test_source_generate_note_success():
    from core.schemas import Note, NoteResult
    from datetime import date

    note = Note(
        uid="note-gen", source_uid="src-gen", slug="gen-note",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Generated Note",
        docstring="desc", body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    note_result = NoteResult(note=note, markdown_path="/vault/gen-note.md")

    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._generate_note_from_source",
               return_value=note_result) as mock_gen:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["generate-note", "src-gen"])

    assert result.exit_code == 0
    mock_gen.assert_called_once()


def test_source_generate_note_not_found():
    from core.errors import NotFoundError
    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._generate_note_from_source",
               side_effect=NotFoundError("Source", "bad-uid")):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["generate-note", "bad-uid"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_source_generate_note_json_mode():
    from core.schemas import Note, NoteResult
    from datetime import date

    note = Note(
        uid="note-gen2", source_uid="src-gen2", slug="gen-note2",
        note_type=None, source_type=None, generation_template="standard",
        rating=None, sync_status="synced", title="Generated Note 2",
        docstring="desc", body="body content here", url=None, status="draft",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        tags=["test-tag"],
    )
    note_result = NoteResult(note=note, markdown_path="/vault/gen-note2.md")

    with patch("cli.commands.sources._load_settings") as mock_settings, \
         patch("cli.commands.sources._generate_note_from_source",
               return_value=note_result):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["generate-note", "src-gen2", "--json"])

    assert result.exit_code == 0
    import json as json_lib
    data = json_lib.loads(result.output)
    assert "note" in data
