"""
Sources command group — list, get.

Routing layer only. No business logic.
"""

from typing import Annotated, Optional

import typer

from cli.output import print_table, print_panel, print_error

app = typer.Typer(help="Browse ingested sources.")

_TRANSCRIPT_PREVIEW_LEN = 300


def _load_settings():
    from core.config import load_settings
    return load_settings()


def _list_sources(db_path, status, limit, offset):
    from infrastructure.db import list_sources
    return list_sources(db_path, status=status, limit=limit, offset=offset)


def _get_source(db_path, uid):
    from infrastructure.db import get_source
    return get_source(db_path, uid)


@app.command("list")
def source_list(
    limit: Annotated[int, typer.Option("--limit")] = 20,
    offset: Annotated[int, typer.Option("--offset")] = 0,
    status: Annotated[Optional[str], typer.Option("--status", help="Filter: raw, rag_ready, vaulted")] = None,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """List ingested sources."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    sources = _list_sources(settings.vault_db_path, status, limit, offset)

    if verbose:
        columns = ["uid", "slug", "type", "status", "url", "date_added"]
        rows = [[s.uid, s.slug, s.source_type, s.status, s.url or "", s.date_added] for s in sources]
    else:
        columns = ["uid", "slug", "type", "status", "date_added"]
        rows = [[s.uid, s.slug, s.source_type, s.status, s.date_added] for s in sources]

    print_table(columns, rows, json_mode)


@app.command("get")
def source_get(
    uid: Annotated[str, typer.Argument(help="Source UID")],
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Get a source by UID."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    source = _get_source(settings.vault_db_path, uid)
    if source is None:
        print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)

    fields: dict = {
        "uid": source.uid,
        "slug": source.slug,
        "type": source.source_type,
        "status": source.status,
        "url": source.url,
        "title": source.title,
        "date_added": source.date_added,
    }
    if verbose and source.transcript:
        fields["transcript"] = source.transcript
    elif source.transcript:
        preview = source.transcript[:_TRANSCRIPT_PREVIEW_LEN]
        fields["transcript"] = preview + "..." if len(source.transcript) > _TRANSCRIPT_PREVIEW_LEN else preview

    print_panel(f"Source: {source.slug}", fields, json_mode)
