"""
Notes command group — list, get, create, update.

Routing layer only. No business logic.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from cli.output import print_table, print_panel, print_error

app = typer.Typer(help="Manage notes in the vault.")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _list_notes(db_path, note_type, tags, limit, offset, status=None):
    from infrastructure.db import list_notes
    return list_notes(db_path, note_type=note_type, tags=tags, limit=limit, offset=offset, status=status)


def _get_note(db_path, uid):
    from infrastructure.db import get_note
    return get_note(db_path, uid)


def _create_note(content, ctx, source_uid=None):
    from tools.vault.create_note import create_note_from_content
    return create_note_from_content(content, ctx, source_uid=source_uid)


def _update_note(uid, fields, ctx):
    from tools.vault.update_note import update_note
    return update_note(uid, fields, ctx)


def _get_source(db_path, source_uid):
    from infrastructure.db import get_source
    return get_source(db_path, source_uid)


def _finalize_source(source_uid, ctx):
    from tools.vault.finalize_source import finalize_source
    return finalize_source(source_uid, ctx)


@app.command("list")
def note_list(
    limit: Annotated[int, typer.Option("--limit", help="Max results")] = 20,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    note_type: Annotated[Optional[str], typer.Option("--type", help="Filter by note_type")] = None,
    tags: Annotated[Optional[str], typer.Option("--tags", help="Comma-separated tags to filter by")] = None,
    status: Annotated[Optional[str], typer.Option("--status", help="Filter by approval status: draft or active")] = None,
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show all fields")] = False,
) -> None:
    """List notes in the vault."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    notes = _list_notes(ctx.settings.vault_db_path, note_type, tag_list, limit, offset, status=status)

    if verbose:
        columns = ["uid", "title", "type", "source_uid", "date_created"]
        rows = [[n.uid, n.title, n.note_type or "", n.source_uid or "", n.date_created] for n in notes]
    else:
        columns = ["uid", "title", "type", "date_created"]
        rows = [[n.uid, n.title, n.note_type or "", n.date_created] for n in notes]

    print_table(columns, rows, json_mode)


@app.command("get")
def note_get(
    uid: Annotated[str, typer.Argument(help="Note UID")],
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show all fields")] = False,
) -> None:
    """Get a note by UID."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    note = _get_note(ctx.settings.vault_db_path, uid)
    if note is None:
        print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)

    fields: dict = {
        "uid": note.uid,
        "title": note.title,
        "type": note.note_type,
        "tags": ", ".join(note.tags),
        "date_created": note.date_created,
        "date_modified": note.date_modified,
    }
    if verbose:
        fields.update({
            "source_uid": note.source_uid,
            "generation_template": note.generation_template,
            "sync_status": note.sync_status,
            "docstring": note.docstring,
            "body": note.body,
        })

    print_panel(f"Note: {note.slug}", fields, json_mode)


@app.command("create")
def note_create(
    from_file: Annotated[Path, typer.Option("--from-file", help="Path to YAML file with note fields")],
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show all fields")] = False,
) -> None:
    """Create a note from a YAML file."""
    import yaml
    from core.schemas import NoteContentInput
    from pydantic import ValidationError

    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if not from_file.exists():
        print_error(f"File not found: {from_file}", "file_not_found", json_mode, verbose)
        raise typer.Exit(1)

    try:
        raw = yaml.safe_load(from_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        print_error("Invalid YAML file.", "yaml_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if not isinstance(raw, dict):
        print_error("YAML file must contain a mapping.", "yaml_error", json_mode, verbose)
        raise typer.Exit(1)

    source_uid = raw.pop("source_uid", None)

    try:
        content = NoteContentInput.model_validate(raw, context={"taxonomy": ctx.settings.taxonomy})
    except (ValidationError, Exception) as e:
        print_error("Invalid note fields.", "validation_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _create_note(content, ctx, source_uid=source_uid)
    except Exception as e:
        print_error("Note creation failed.", "create_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    fields = {
        "uid": result.note.uid,
        "slug": result.note.slug,
        "markdown_path": result.markdown_path,
    }
    print_panel("Note created", fields, json_mode)


@app.command("update")
def note_update(
    uid: Annotated[str, typer.Argument(help="Note UID")],
    title: Annotated[Optional[str], typer.Option("--title")] = None,
    docstring: Annotated[Optional[str], typer.Option("--docstring")] = None,
    body: Annotated[Optional[str], typer.Option("--body")] = None,
    note_type: Annotated[Optional[str], typer.Option("--type")] = None,
    source_type: Annotated[Optional[str], typer.Option("--source-type")] = None,
    rating: Annotated[Optional[int], typer.Option("--rating", min=1, max=5)] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    status: Annotated[Optional[str], typer.Option("--status", help="Set approval status: draft or active")] = None,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Update editable fields of an existing note."""
    fields: dict = {}
    if title is not None:
        fields["title"] = title
    if docstring is not None:
        fields["docstring"] = docstring
    if body is not None:
        fields["body"] = body
    if note_type is not None:
        fields["note_type"] = note_type
    if source_type is not None:
        fields["source_type"] = source_type
    if rating is not None:
        fields["rating"] = rating
    if url is not None:
        fields["url"] = url
    if status is not None:
        if status not in ("draft", "active"):
            print_error("Invalid status. Must be 'draft' or 'active'.", "validation_error",
                        json_mode, verbose)
            raise typer.Exit(1)
        fields["status"] = status

    if not fields:
        print_error("No fields to update. Provide at least one option.", "no_fields",
                    json_mode, verbose)
        raise typer.Exit(1)

    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _update_note(uid, fields, ctx)
    except Exception as e:
        from core.errors import NotFoundError
        if isinstance(e, NotFoundError):
            print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        else:
            print_error("Note update failed.", "update_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    out_fields = {
        "uid": result.note.uid,
        "slug": result.note.slug,
        "date_modified": result.note.date_modified,
    }
    print_panel("Note updated", out_fields, json_mode)


@app.command("approve")
def note_approve(
    uid: Annotated[str, typer.Argument(help="Note UID to approve")],
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show all fields")] = False,
) -> None:
    """Approve a draft note and finalize its linked source if applicable."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    note = _get_note(ctx.settings.vault_db_path, uid)
    if note is None:
        print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)

    try:
        result = _update_note(uid, {"status": "active"}, ctx)
    except Exception as e:
        print_error("Failed to approve note.", "approve_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    finalized = False
    if note.source_uid:
        source = _get_source(ctx.settings.vault_db_path, note.source_uid)
        if source and source.status == "rag_ready":
            try:
                _finalize_source(note.source_uid, ctx)
                finalized = True
            except Exception as e:
                print_error("Note approved but source finalization failed.",
                            "finalize_error", json_mode, verbose, str(e))
                raise typer.Exit(1)

    out_fields: dict = {
        "uid": result.note.uid,
        "slug": result.note.slug,
        "status": result.note.status,
    }
    if finalized:
        out_fields["source_finalized"] = note.source_uid

    print_panel("Note approved", out_fields, json_mode)


def _delete_note(uid, ctx, force):
    from tools.vault.delete_note import delete_note
    return delete_note(uid, ctx, force=force)


def _restore_note(uid, ctx):
    from tools.vault.restore_note import restore_note
    return restore_note(uid, ctx)


def _delete_source_tool(source_uid, ctx):
    from tools.vault.delete_source import delete_source
    return delete_source(source_uid, ctx, force=True)


@app.command("delete")
def note_delete(
    uid: Annotated[str, typer.Argument(help="Note UID to delete")],
    force: Annotated[bool, typer.Option("--force", help="Hard-delete immediately (irreversible)")] = False,
    delete_source: Annotated[bool, typer.Option("--delete-source", help="Also delete linked source")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation prompt")] = False,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Delete a note. Soft-delete by default; use --force for immediate removal."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    # Pre-fetch source_uid for cascade before note is deleted
    source_uid_to_delete = None
    if delete_source and force:
        note_before = _get_note(ctx.settings.vault_db_path, uid)
        if note_before and note_before.source_uid:
            source_uid_to_delete = note_before.source_uid

    if force and not yes:
        note = _get_note(ctx.settings.vault_db_path, uid)
        summary = f"Note: {note.title if note else uid}"
        if source_uid_to_delete:
            summary += f"\nLinked source: {source_uid_to_delete} (and all its chunks, media)"
        typer.echo(f"This will permanently delete:\n  {summary}")
        if not typer.confirm("Confirm permanent deletion?"):
            raise typer.Exit(0)

    try:
        result = _delete_note(uid, ctx, force=force)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Delete failed.", "delete_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    if source_uid_to_delete:
        try:
            _delete_source_tool(source_uid_to_delete, ctx)
            result = result.model_copy(update={"deleted_source_uid": source_uid_to_delete})
        except Exception as e:
            print_error(f"Note deleted but source deletion failed: {e}", "source_error", json_mode, verbose)

    fields = {"uid": result.uid, "action": result.action}
    print_panel("Note deleted", fields, json_mode)


@app.command("restore")
def note_restore(
    uid: Annotated[str, typer.Argument(help="Note UID to restore")],
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Restore a note previously marked for deletion."""
    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _restore_note(uid, ctx)
    except Exception as e:
        from core.errors import NotFoundError, ConflictError
        if isinstance(e, NotFoundError):
            print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        elif isinstance(e, ConflictError):
            print_error(str(e), "conflict", json_mode, verbose)
        else:
            print_error("Restore failed.", "restore_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    print_panel("Note restored", {"uid": result.uid, "sync_status": result.restored_sync_status}, json_mode)
