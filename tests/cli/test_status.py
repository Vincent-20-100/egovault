import json
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.commands.status import app

runner = CliRunner()


def _make_job(job_id="job-abc-123", job_type="ingest_youtube", status="done"):
    return {
        "id": job_id,
        "job_type": job_type,
        "status": status,
        "created_at": "2026-03-30T10:00:00Z",
        "started_at": "2026-03-30T10:00:01Z",
        "completed_at": "2026-03-30T10:00:10Z",
        "result": {"slug": "ma-video"},
        "error": None,
    }


def test_status_default():
    jobs = [_make_job()]
    with patch("cli.commands.status._build_ctx") as mock_settings, \
         patch("cli.commands.status._list_jobs", return_value=jobs):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "job-abc" in result.output


def test_status_json_mode():
    jobs = [_make_job()]
    with patch("cli.commands.status._build_ctx") as mock_settings, \
         patch("cli.commands.status._list_jobs", return_value=jobs):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == "job-abc-123"


def test_status_verbose_shows_full_id():
    jobs = [_make_job()]
    with patch("cli.commands.status._build_ctx") as mock_settings, \
         patch("cli.commands.status._list_jobs", return_value=jobs):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["--verbose"])
    assert result.exit_code == 0
    assert "job-abc-123" in result.output


def test_status_no_jobs():
    with patch("cli.commands.status._build_ctx") as mock_settings, \
         patch("cli.commands.status._list_jobs", return_value=[]):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "No jobs" in result.output
