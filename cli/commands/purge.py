"""
Purge command — permanently removes all pending_deletion items.

Routing layer only. No business logic.
"""

from typing import Annotated
import typer
from cli.output import print_panel, print_error, print_table

app = typer.Typer(help="Purge all items marked for deletion.")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _run_purge(ctx):
    from tools.vault.purge import purge
    return purge(ctx)


def _list_pending(ctx):
    return (
        ctx.db.list_notes_pending_deletion(),
        ctx.db.list_sources_pending_deletion(),
    )


@app.command()
def purge_cmd(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="List what would be purged without deleting")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Permanently delete all items currently marked for deletion."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    pending_notes, pending_sources = _list_pending(ctx)

    if dry_run:
        typer.echo(f"Pending deletion: {len(pending_notes)} notes, {len(pending_sources)} sources")
        if verbose and pending_notes:
            print_table(["uid", "title"], [[n.uid, n.title] for n in pending_notes], json_mode)
        if verbose and pending_sources:
            print_table(["uid", "slug"], [[s.uid, s.slug] for s in pending_sources], json_mode)
        raise typer.Exit(0)

    if not pending_notes and not pending_sources:
        typer.echo("Nothing to purge.")
        raise typer.Exit(0)

    if not yes:
        typer.echo(f"About to permanently delete {len(pending_notes)} notes and {len(pending_sources)} sources.")
        if not typer.confirm("Confirm purge? This cannot be undone."):
            raise typer.Exit(0)

    try:
        result = _run_purge(ctx)
    except Exception as e:
        print_error("Purge failed.", "purge_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    print_panel("Purge complete", {
        "notes_purged": result.notes_purged,
        "sources_purged": result.sources_purged,
        "media_files_deleted": result.media_files_deleted,
    }, json_mode)
