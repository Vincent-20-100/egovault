"""
Status command — recent API jobs from .system.db.

Note: shows jobs created by the API (async path).
CLI ingestion runs are synchronous and not recorded as jobs.
Routing layer only. No business logic.
"""

import json
from typing import Annotated

import typer

from cli.output import print_table, print_panel, print_error

app = typer.Typer(help="Show recent API job activity.")

_ID_SHORT_LEN = 8


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _list_jobs(db_path, limit):
    from infrastructure.db import list_jobs
    return list_jobs(db_path, limit=limit)


@app.callback(invoke_without_command=True)
def status(
    limit: Annotated[int, typer.Option("--limit", help="Max jobs to show")] = 10,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show full job_id and timestamps")] = False,
) -> None:
    """Show recent API job activity from .system.db."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    jobs = _list_jobs(ctx.settings.system_db_path, limit)

    if not jobs:
        if json_mode:
            print(json.dumps([]))
        else:
            typer.echo("No jobs found.")
        return

    if json_mode:
        print(json.dumps(jobs, indent=2, default=str))
        return

    if verbose:
        for j in jobs:
            fields = {
                "job_id": j["id"],
                "type": j["job_type"],
                "status": j["status"],
                "created_at": j.get("created_at", ""),
                "started_at": j.get("started_at") or "",
                "completed_at": j.get("completed_at") or "",
                "result": str(j.get("result") or j.get("error") or ""),
            }
            print_panel(f"Job: {j['id']}", fields, json_mode=False)
    else:
        columns = ["job_id", "type", "status", "created_at", "result"]
        rows = [
            [
                j["id"][:_ID_SHORT_LEN] + "...",
                j["job_type"],
                j["status"],
                j.get("created_at", "")[:19],
                str(j.get("result") or j.get("error") or ""),
            ]
            for j in jobs
        ]
        print_table(columns, rows, json_mode=False)
