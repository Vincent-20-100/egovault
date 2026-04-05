import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.commands.ingest import app

runner = CliRunner()


def _make_source(slug="my-video", uid="uid-123", status="rag_ready", source_type="youtube", title="My Video"):
    from core.schemas import Source
    return Source(
        uid=uid, slug=slug, source_type=source_type, status=status,
        url="https://youtube.com/watch?v=test", title=title,
        date_added="2026-03-30",
    )


def test_ingest_youtube_success():
    source = _make_source()
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["https://youtube.com/watch?v=abc123"])
    assert result.exit_code == 0
    assert "my-video" in result.output


def test_ingest_youtube_json_mode():
    source = _make_source()
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["https://youtube.com/watch?v=abc123", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert data["slug"] == "my-video"
    assert data["uid"] == "uid-123"


def test_ingest_unsupported_type():
    with patch("cli.commands.ingest._build_ctx") as mock_settings:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["file.xyz"])
    assert result.exit_code == 1


def test_ingest_file_not_found():
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", side_effect=FileNotFoundError("not found")):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["missing.pdf"])
    assert result.exit_code == 1


def test_ingest_large_format_error():
    from core.errors import LargeFormatError
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest",
               side_effect=LargeFormatError("uid-x", 60000, 50000)):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["https://youtube.com/watch?v=abc"])
    assert result.exit_code == 1


def test_ingest_verbose_shows_elapsed():
    source = _make_source()
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["https://youtube.com/watch?v=abc", "--verbose"])
    assert result.exit_code == 0
    assert "elapsed" in result.output


def test_ingest_generate_note_flag_passed_to_workflow():
    """--generate-note passes auto_generate_note=True to the workflow."""
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-ingest-gen", slug="youtube-abc", source_type="youtube",
        status="rag_ready", url="https://youtube.com/watch?v=abc",
        date_added=date.today().isoformat(),
    )
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(
            app, ["https://youtube.com/watch?v=abc", "--generate-note"]
        )

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args
    auto = call_kwargs[1].get("auto_generate_note") if call_kwargs[1] else call_kwargs[0][3]
    assert auto is True


def test_ingest_no_generate_note_flag_passed():
    """--no-generate-note passes auto_generate_note=False to the workflow."""
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-ingest-nogen", slug="youtube-nogen", source_type="youtube",
        status="rag_ready", url="https://youtube.com/watch?v=nogen",
        date_added=date.today().isoformat(),
    )
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(
            app, ["https://youtube.com/watch?v=nogen", "--no-generate-note"]
        )

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args
    auto = call_kwargs[1].get("auto_generate_note") if call_kwargs[1] else call_kwargs[0][3]
    assert auto is False


def test_ingest_no_flag_passes_none():
    """No flag passes auto_generate_note=None (read from config)."""
    from core.schemas import Source
    from datetime import date

    source = Source(
        uid="src-ingest-cfg", slug="youtube-cfg", source_type="youtube",
        status="rag_ready", url="https://youtube.com/watch?v=cfg",
        date_added=date.today().isoformat(),
    )
    with patch("cli.commands.ingest._build_ctx") as mock_settings, \
         patch("cli.commands.ingest._run_ingest", return_value=source) as mock_run:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["https://youtube.com/watch?v=cfg"])

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args
    auto = call_kwargs[1].get("auto_generate_note") if call_kwargs[1] else (call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None)
    assert auto is None
