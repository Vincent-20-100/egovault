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


def _generate_note_from_source(source_uid, settings, template="standard"):
    from tools.vault.generate_note_from_source import generate_note_from_source
    return generate_note_from_source(source_uid, settings, template=template)


@app.command("generate-note")
def source_generate_note(
    uid: Annotated[str, typer.Argument(help="Source UID")],
    template: Annotated[str, typer.Option("--template",
                        help="Generation template name")] = "standard",
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Generate a draft note from an ingested source via the configured LLM."""
    from core.errors import NotFoundError, ConflictError

    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _generate_note_from_source(uid, settings, template=template)
    except NotFoundError:
        print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)
    except ConflictError:
        print_error(f"A note already exists for source: {uid}", "conflict",
                    json_mode, verbose)
        raise typer.Exit(1)
    except Exception as e:
        print_error("Note generation failed.", "generation_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if json_mode:
        import json
        print(json.dumps(result.model_dump(mode="json")))
    else:
        fields: dict = {
            "note_uid": result.note.uid,
            "slug": result.note.slug,
            "status": result.note.status,
            "template": result.note.generation_template,
        }
        if verbose:
            fields["markdown_path"] = result.markdown_path
        print_panel("Draft note generated", fields, json_mode)


def _delete_source(uid, settings, force):
    from tools.vault.delete_source import delete_source
    return delete_source(uid, settings, force=force)


def _restore_source(uid, settings):
    from tools.vault.restore_source import restore_source
    return restore_source(uid, settings)


@app.command("delete")
def source_delete(
    uid: Annotated[str, typer.Argument(help="Source UID to delete")],
    force: Annotated[bool, typer.Option("--force", help="Hard-delete immediately (irreversible)")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Delete a source. Soft-delete by default; use --force for immediate removal."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if force and not yes:
        source = _get_source(settings.vault_db_path, uid)
        summary = f"Source: {source.title or source.slug if source else uid}"
        if source and source.media_path:
            summary += f"\nMedia file: {source.media_path}"
        summary += "\nAll chunks and embeddings"
        typer.echo(f"This will permanently delete:\n  {summary}")
        if not typer.confirm("Confirm permanent deletion?"):
            raise typer.Exit(0)

    try:
        result = _delete_source(uid, settings, force=force)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Delete failed.", "delete_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    fields: dict = {"uid": result.uid, "action": result.action}
    if result.orphaned_note_uids:
        fields["orphaned_notes"] = ", ".join(result.orphaned_note_uids)
    print_panel("Source deleted", fields, json_mode)


@app.command("restore")
def source_restore(
    uid: Annotated[str, typer.Argument(help="Source UID to restore")],
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Restore a source previously marked for deletion."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _restore_source(uid, settings)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Source not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Restore failed.", "restore_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    print_panel("Source restored", {"uid": result.uid, "status": result.restored_status}, json_mode)
