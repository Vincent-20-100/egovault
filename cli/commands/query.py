"""
Query command — Librarian working memory retrieval.

Routing layer only. No business logic.
"""

from typing import Annotated

import typer

from cli.output import print_error

app = typer.Typer(help="Query working memory context over the vault.")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _run_query(query: str, ctx, limit: int):
    from tools.vault.query_vault import query_vault
    return query_vault(query, ctx, limit=limit)


@app.command(name="query")
def query_cmd(
    query: Annotated[str, typer.Argument(help="Knowledge question")],
    limit: Annotated[int, typer.Option("--limit", help="Max sources")] = 5,
) -> None:
    """Librarian working memory retrieval over the vault."""
    if not query.strip():
        print_error("Query must not be empty.", "empty_query", False, False)
        raise typer.Exit(1)

    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found. Run the setup script first.",
                    "config_error", False, False, str(e))
        raise typer.Exit(1)

    try:
        result = _run_query(query, ctx, limit)
    except Exception as e:
        print_error("Query failed.", "query_error", False, False, str(e))
        raise typer.Exit(1)

    if not result.sources:
        typer.echo("No results found.")
        return

    typer.echo(result.synthesis)
    typer.echo("\n--- sources ---")
    for s in result.sources:
        typer.echo(f"[{s.tier}:{s.uid}] {s.title}  (distance={s.distance:.4f})")
