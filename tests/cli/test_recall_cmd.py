from unittest.mock import patch

from typer.testing import CliRunner

from cli.main import app
from core.schemas import RecallContext, RecallSource

runner = CliRunner()


def test_recall_cmd_prints_synthesis():
    fake = RecallContext(
        synthesis="[note:n1] Title\nbody",
        sources=[RecallSource(tier="note", uid="n1", title="Title",
                              content="body", distance=0.1)],
        query="q",
    )
    with patch("cli.commands.recall._build_ctx"), \
         patch("cli.commands.recall._run_recall", return_value=fake):
        result = runner.invoke(app, ["recall", "q"])
    assert result.exit_code == 0
    assert "n1" in result.stdout
