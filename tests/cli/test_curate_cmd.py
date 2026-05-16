from unittest.mock import patch

from typer.testing import CliRunner

from cli.main import app
from core.schemas import CuratedContext, CuratedSource

runner = CliRunner()


def test_curate_cmd_prints_synthesis():
    fake = CuratedContext(
        synthesis="[note:n1] Title\nbody",
        sources=[CuratedSource(tier="note", uid="n1", title="Title",
                               content="body", distance=0.1)],
        query="q",
    )
    with patch("cli.commands.curate._build_ctx"), \
         patch("cli.commands.curate._run_curate", return_value=fake):
        result = runner.invoke(app, ["curate", "q"])
    assert result.exit_code == 0
    assert "n1" in result.stdout
