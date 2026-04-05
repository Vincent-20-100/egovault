"""
Output layer for the EgoVault CLI.

Centralises all rich usage. Commands never import rich directly.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()
_err_console = Console(stderr=True)


def print_table(
    columns: list[str],
    rows: list[list[Any]],
    json_mode: bool = False,
) -> None:
    """Render a table. In json_mode, print a JSON array to stdout."""
    if json_mode:
        data = [dict(zip(columns, row)) for row in rows]
        print(json.dumps(data, indent=2, default=str))
        return
    table = Table(*columns)
    for row in rows:
        table.add_row(*[str(v) if v is not None else "" for v in row])
    _console.print(table)


def print_panel(
    title: str,
    fields: dict[str, Any],
    json_mode: bool = False,
) -> None:
    """Render a detail panel. In json_mode, print a JSON object to stdout."""
    if json_mode:
        print(json.dumps(fields, indent=2, default=str))
        return
    lines = "\n".join(
        f"[bold]{k}:[/bold] {v}" for k, v in fields.items() if v is not None
    )
    _console.print(Panel(lines, title=title))


@contextmanager
def spinner(message: str) -> Iterator[None]:
    """Context manager showing an animated spinner while a block executes."""
    with _console.status(message):
        yield


def print_error(
    message: str,
    code: str,
    json_mode: bool = False,
    verbose: bool = False,
    detail: str | None = None,
) -> None:
    """Print an error to stderr (or stdout as JSON in json_mode)."""
    if json_mode:
        payload: dict[str, Any] = {"error": message, "code": code}
        if verbose and detail:
            payload["detail"] = detail
        print(json.dumps(payload))
        return
    _err_console.print(f"[red]Error:[/red] {message}")
    if verbose and detail:
        _err_console.print(f"[dim]{detail}[/dim]")
