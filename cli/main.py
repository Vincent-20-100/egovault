"""
EgoVault CLI — entry point.

Assembles all command groups. Routing layer only.
"""

import typer

from cli.commands.ingest import ingest as _ingest
from cli.commands.search import search_cmd as _search
from cli.commands.notes import app as notes_app
from cli.commands.sources import app as sources_app
from cli.commands.status import status as _status
from cli.commands.purge import app as purge_app

app = typer.Typer(
    name="egovault",
    help="EgoVault — personal memory infrastructure.",
    no_args_is_help=True,
)

# Single-command groups: register the function directly to avoid double-nesting
app.command("ingest")(_ingest)
app.command("search")(_search)
app.command("status")(_status)

# Multi-command groups: add_typer works correctly here
app.add_typer(notes_app, name="note")
app.add_typer(sources_app, name="source")
app.add_typer(purge_app, name="purge")


if __name__ == "__main__":
    app()
