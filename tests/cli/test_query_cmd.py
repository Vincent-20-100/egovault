from unittest.mock import patch

from typer.testing import CliRunner

from cli.main import app
from core.schemas import CuratedContext, CuratedSource

runner = CliRunner()


def test_query_cmd_prints_synthesis():
    fake = CuratedContext(
        synthesis="[note:n1] Title\nbody",
        sources=[CuratedSource(tier="note", uid="n1", title="Title",
                               content="body", distance=0.1)],
        query="q",
    )
    with patch("cli.commands.query._build_ctx"), \
         patch("cli.commands.query._run_query", return_value=fake):
        result = runner.invoke(app, ["query", "q"])
    assert result.exit_code == 0
    assert "n1" in result.stdout

