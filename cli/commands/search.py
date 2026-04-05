"""
Search command — semantic search over the vault.

Routing layer only. No business logic.
"""

import time
from typing import Annotated

import typer

from cli.output import print_table, print_error

app = typer.Typer(help="Semantic search over the vault.")

_VALID_MODES = ("chunks", "notes")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _run_search(query: str, ctx, mode: str, limit: int):
    from tools.vault.search import search
    return search(query, ctx, mode=mode, limit=limit)


@app.command()
def search_cmd(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of results")] = 10,
    mode: Annotated[str, typer.Option("--mode", help="Search mode: chunks or notes")] = "chunks",
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show distance, chunk_uid, execution time")] = False,
) -> None:
    """Semantic search over the vault."""
    if not query.strip():
        print_error("Query must not be empty.", "empty_query", json_mode, verbose)
        raise typer.Exit(1)

    if mode not in _VALID_MODES:
        print_error(f"Invalid mode '{mode}'. Use 'chunks' or 'notes'.", "invalid_mode", json_mode, verbose)
        raise typer.Exit(1)

    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found. Run the setup script first.", "config_error",
                    json_mode, verbose, str(e))
        raise typer.Exit(1)

    start = time.time()
    try:
        results = _run_search(query, ctx, mode, limit)
    except Exception as e:
        print_error("Search failed.", "search_error", json_mode, verbose, str(e))
        raise typer.Exit(1)
    elapsed = time.time() - start

    if not results:
        if json_mode:
            import json as _json
            print(_json.dumps([]))
        else:
            typer.echo("No results found.")
        return

    if verbose:
        columns = ["title", "score", "distance", "chunk_uid", "note_uid", "excerpt"]
        rows = [
            [
                r.title,
                f"{round(1 - r.distance, 4)}",
                f"{r.distance:.4f}",
                r.chunk_uid or "",
                r.note_uid or "",
                (r.content[:100] + "...") if r.content else "",
            ]
            for r in results
        ]
        if not json_mode:
            typer.echo(f"[{elapsed:.2f}s]")
    else:
        columns = ["title", "score", "excerpt"]
        rows = [
            [
                r.title,
                f"{round(1 - r.distance, 4)}",
                (r.content[:120] + "...") if r.content else "",
            ]
            for r in results
        ]

    if json_mode:
        import json as _json
        data = [dict(zip(columns, row)) for row in rows]
        print(_json.dumps(data, indent=2))
    else:
        print_table(columns, rows, json_mode=False)
