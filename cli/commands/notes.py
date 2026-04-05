"""
Notes command group — list, get, create, update.

Routing layer only. No business logic.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from cli.output import print_table, print_panel, print_error

app = typer.Typer(help="Manage notes in the vault.")


def _load_settings():
    from core.config import load_settings
    return load_settings()


def _list_notes(db_path, note_type, tags, limit, offset, status=None):
    from infrastructure.db import list_notes
    return list_notes(db_path, note_type=note_type, tags=tags, limit=limit, offset=offset, status=status)


def _get_note(db_path, uid):
    from infrastructure.db import get_note
    return get_note(db_path, uid)


def _get_existing_slugs(db_path) -> set[str]:
    from infrastructure.db import get_vault_connection
    conn = get_vault_connection(db_path)
    slugs = {row[0] for row in conn.execute("SELECT slug FROM notes").fetchall()}
    conn.close()
    return slugs


def _create_note(content, system_fields, settings):
    from tools.vault.create_note import create_note
    return create_note(content, system_fields, settings)


def _update_note(uid, fields, settings):
    from tools.vault.update_note import update_note
    return update_note(uid, fields, settings)


def _get_source(db_path, source_uid):
    from infrastructure.db import get_source
    return get_source(db_path, source_uid)


def _finalize_source(source_uid, settings):
    from tools.vault.finalize_source import finalize_source
    return finalize_source(source_uid, settings)


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
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    notes = _list_notes(settings.vault_db_path, note_type, tag_list, limit, offset, status=status)

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
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    note = _get_note(settings.vault_db_path, uid)
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
    from core.schemas import NoteContentInput, NoteSystemFields
    from core.uid import generate_uid, make_unique_slug
    from pydantic import ValidationError
    from datetime import date

    try:
        settings = _load_settings()
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
        content = NoteContentInput.model_validate(raw, context={"taxonomy": settings.taxonomy})
    except (ValidationError, Exception) as e:
        print_error("Invalid note fields.", "validation_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        existing_slugs = _get_existing_slugs(settings.vault_db_path)

        system_fields = NoteSystemFields(
            uid=generate_uid(),
            date_created=date.today().isoformat(),
            source_uid=source_uid,
            slug=make_unique_slug(content.title, existing_slugs),
            generation_template=None,
        )

        result = _create_note(content, system_fields, settings)
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
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        result = _update_note(uid, fields, settings)
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
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    note = _get_note(settings.vault_db_path, uid)
    if note is None:
        print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)

    try:
        result = _update_note(uid, {"status": "active"}, settings)
    except Exception as e:
        print_error("Failed to approve note.", "approve_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    finalized = False
    if note.source_uid:
        source = _get_source(settings.vault_db_path, note.source_uid)
        if source and source.status == "rag_ready":
            try:
                _finalize_source(note.source_uid, settings)
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
