import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.commands.notes import app

runner = CliRunner()


def _make_note(uid="nuid-1", title="Mon Note", note_type="synthese", status="vaulted"):
    from core.schemas import Note
    return Note(
        uid=uid, slug="mon-note", title=title, docstring="Une note.",
        body="## Contenu\nTexte.", note_type=note_type, source_type="youtube",
        tags=["economie"], date_created="2026-03-30", date_modified="2026-03-30",
        sync_status="synced",
    )


def _make_note_result(note=None):
    from core.schemas import NoteResult
    n = note or _make_note()
    return NoteResult(note=n, markdown_path="/vault/notes/mon-note.md")


# --- note list ---

def test_note_list_default():
    notes = [_make_note()]
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._list_notes", return_value=notes):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Mon Note" in result.output


def test_note_list_json_mode():
    notes = [_make_note()]
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._list_notes", return_value=notes):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["title"] == "Mon Note"


def test_note_list_filter_by_type():
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._list_notes", return_value=[]) as mock_list:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list", "--type", "synthese"])
    assert result.exit_code == 0
    mock_list.assert_called_once()
    call_args = mock_list.call_args
    assert call_args[0][1] == "synthese" or call_args[1].get("note_type") == "synthese"


# --- note get ---

def test_note_get_success():
    note = _make_note()
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["get", "nuid-1"])
    assert result.exit_code == 0
    assert "Mon Note" in result.output


def test_note_get_not_found():
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=None):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["get", "nonexistent"])
    assert result.exit_code == 1


# --- note create ---

def test_note_create_from_file(tmp_path):
    yaml_file = tmp_path / "note.yaml"
    yaml_file.write_text(yaml.dump({
        "source_uid": None,
        "title": "Elasticite des prix",
        "docstring": "Note sur l'elasticite.",
        "body": "## Contexte\nContenu.",
        "note_type": "synthese",
        "source_type": "youtube",
        "tags": ["elasticite"],
    }))
    note_result = _make_note_result()
    mock_settings = MagicMock()
    mock_settings.taxonomy = MagicMock(note_types=["synthese"], source_types=["youtube"])
    with patch("cli.commands.notes._load_settings", return_value=mock_settings), \
         patch("cli.commands.notes._get_existing_slugs", return_value=set()), \
         patch("cli.commands.notes._create_note", return_value=note_result):
        result = runner.invoke(app, ["create", "--from-file", str(yaml_file)])
    assert result.exit_code == 0
    assert "mon-note" in result.output


def test_note_create_invalid_yaml(tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text("not: valid: yaml: {{{")
    with patch("cli.commands.notes._load_settings", return_value=MagicMock()):
        result = runner.invoke(app, ["create", "--from-file", str(yaml_file)])
    assert result.exit_code == 1


def test_note_create_file_not_found():
    with patch("cli.commands.notes._load_settings", return_value=MagicMock()):
        result = runner.invoke(app, ["create", "--from-file", "/nonexistent/note.yaml"])
    assert result.exit_code == 1


# --- note update ---

def test_note_update_title():
    note_result = _make_note_result()
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._update_note", return_value=note_result):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["update", "nuid-1", "--title", "Nouveau titre"])
    assert result.exit_code == 0


def test_note_update_no_fields():
    with patch("cli.commands.notes._load_settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["update", "nuid-1"])
    assert result.exit_code == 1


def test_note_update_json_mode():
    note_result = _make_note_result()
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._update_note", return_value=note_result):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["update", "nuid-1", "--title", "Nouveau", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "uid" in data


def test_note_update_status():
    note_result = _make_note_result()
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._update_note", return_value=note_result) as mock_update:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["update", "nuid-1", "--status", "draft"])
    assert result.exit_code == 0
    mock_update.assert_called_once()
    assert mock_update.call_args[0][1].get("status") == "draft"


def test_note_update_invalid_status():
    with patch("cli.commands.notes._load_settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["update", "nuid-1", "--status", "invalid"])
    assert result.exit_code == 1


def test_note_list_filter_by_status():
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._list_notes", return_value=[]) as mock_list:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["list", "--status", "draft"])
    assert result.exit_code == 0
    mock_list.assert_called_once()
    call_kwargs = mock_list.call_args[1] if mock_list.call_args[1] else {}
    call_args = mock_list.call_args[0] if mock_list.call_args[0] else []
    # status can be passed positionally or as keyword
    assert "draft" in list(call_args) + list(call_kwargs.values())


# --- note approve ---

def test_note_approve_success():
    """Approves a draft note — calls update_note then finalize_source."""
    note = _make_note(uid="nuid-approve")
    note.source_uid = "src-1"
    note_result = _make_note_result(note)
    from core.schemas import FinalizeResult, Source
    finalize_result = FinalizeResult(source_uid="src-1", new_status="vaulted", media_moved_to=None)
    mock_source = Source(
        uid="src-1", slug="src-slug", source_type="youtube",
        status="rag_ready", date_added="2026-03-30",
    )

    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note), \
         patch("cli.commands.notes._update_note", return_value=note_result) as mock_update, \
         patch("cli.commands.notes._get_source", return_value=mock_source), \
         patch("cli.commands.notes._finalize_source", return_value=finalize_result):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nuid-approve"])

    assert result.exit_code == 0
    mock_update.assert_called_once()
    assert mock_update.call_args[0][1] == {"status": "active"}


def test_note_approve_no_source():
    """Approves a note with no source_uid — no finalize_source call."""
    note = _make_note(uid="nuid-nosrc")
    note_result = _make_note_result(note)

    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note), \
         patch("cli.commands.notes._update_note", return_value=note_result), \
         patch("cli.commands.notes._finalize_source") as mock_finalize:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nuid-nosrc"])

    assert result.exit_code == 0
    mock_finalize.assert_not_called()


def test_note_approve_not_found():
    """Returns exit code 1 when note does not exist."""
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=None):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_note_approve_json_mode():
    """--json flag outputs JSON."""
    note = _make_note(uid="nuid-json")
    note_result = _make_note_result(note)

    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note), \
         patch("cli.commands.notes._update_note", return_value=note_result), \
         patch("cli.commands.notes._finalize_source", return_value=None):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nuid-json", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "uid" in data
