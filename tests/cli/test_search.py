import json
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.commands.search import app

runner = CliRunner()


def _make_result(title="Mon Note", score=0.9, content="Contenu du chunk", note_uid="nuid-1", chunk_uid="cuid-1"):
    from core.schemas import SearchResult
    return SearchResult(
        title=title,
        content=content,
        distance=1 - score,
        note_uid=note_uid,
        chunk_uid=chunk_uid,
        source_uid="suid-1",
    )


def test_search_returns_results():
    results = [_make_result()]
    with patch("cli.commands.search._load_settings") as mock_settings, \
         patch("cli.commands.search._run_search", return_value=results):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["elasticite des prix"])
    assert result.exit_code == 0
    assert "Mon Note" in result.output


def test_search_json_mode():
    results = [_make_result()]
    with patch("cli.commands.search._load_settings") as mock_settings, \
         patch("cli.commands.search._run_search", return_value=results):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["elasticite des prix", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Mon Note"
    assert "score" in data[0]


def test_search_verbose_shows_distance():
    results = [_make_result()]
    with patch("cli.commands.search._load_settings") as mock_settings, \
         patch("cli.commands.search._run_search", return_value=results):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["query", "--verbose"])
    assert result.exit_code == 0
    assert "distance" in result.output or "cuid-1" in result.output


def test_search_empty_results():
    with patch("cli.commands.search._load_settings") as mock_settings, \
         patch("cli.commands.search._run_search", return_value=[]):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["nothing"])
    assert result.exit_code == 0
    assert "No results" in result.output


def test_search_empty_query():
    with patch("cli.commands.search._load_settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, [""])
    assert result.exit_code == 1
