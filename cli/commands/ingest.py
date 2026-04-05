"""
Ingest command — dispatches to the right workflow based on input type.

Routing layer only. No business logic.
"""

import time
from pathlib import Path
from typing import Annotated

import typer

from cli.output import print_panel, print_error, spinner

app = typer.Typer(help="Ingest a URL, audio file, PDF, text, or HTML file into the vault.")

_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}
_YOUTUBE_PATTERNS = ("youtube.com", "youtu.be")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _detect_type(target: str) -> str:
    if any(p in target for p in _YOUTUBE_PATTERNS):
        return "youtube"
    if target.startswith(("http://", "https://")):
        return "web"
    ext = Path(target).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in _AUDIO_EXTENSIONS:
        return "audio"
    if ext == ".txt":
        return "texte"
    if ext in {".html", ".htm"}:
        return "html"
    raise ValueError(f"Unsupported input: '{target}'. Provide a URL, audio file, PDF, text, or HTML file.")


def _run_ingest(input_type: str, target: str, ctx, auto_generate_note=None, title=None):
    from workflows.ingest import ingest
    if input_type in ("texte", "html") and Path(target).is_file():
        target = Path(target).read_text(encoding="utf-8")
    return ingest(input_type, target, ctx, title=title, auto_generate_note=auto_generate_note)


@app.command()
def ingest(
    target: Annotated[str, typer.Argument(help="URL or path to audio, PDF, text, or HTML file")],
    generate_note: Annotated[
        bool | None,
        typer.Option("--generate-note/--no-generate-note",
                     help="Generate a draft note after ingestion. Default: reads user.yaml.")
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Title for the source (used for text/HTML input)")] = None,
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show step timings and details")] = False,
) -> None:
    """Ingest a URL, audio file, PDF, text, or HTML file into the vault."""
    from core.errors import IngestError, LargeFormatError

    try:
        ctx = _build_ctx()
    except Exception as e:
        print_error("Configuration not found. Run the setup script first.", "config_error",
                    json_mode, verbose, str(e))
        raise typer.Exit(1)

    try:
        input_type = _detect_type(target)
    except ValueError as e:
        print_error(str(e), "unsupported_type", json_mode, verbose)
        raise typer.Exit(1)

    start = time.time()
    try:
        with spinner(f"Ingesting {input_type}..."):
            source = _run_ingest(input_type, target, ctx,
                                 auto_generate_note=generate_note, title=title)
    except LargeFormatError as e:
        print_error(
            "Source is too large for automatic note generation. "
            "It has been indexed and is searchable. Create the note manually.",
            "large_format",
            json_mode, verbose,
            f"token_count={e.token_count}, threshold={e.threshold}, source_uid={e.source_uid}",
        )
        raise typer.Exit(1)
    except IngestError as e:
        print_error(e.user_message, e.error_code, json_mode, verbose)
        raise typer.Exit(1)
    except FileNotFoundError as e:
        print_error(f"File not found: {target}", "file_not_found", json_mode, verbose, str(e))
        raise typer.Exit(1)
    except Exception as e:
        print_error("Ingestion failed.", "ingest_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    elapsed = time.time() - start

    fields: dict = {
        "uid": source.uid,
        "slug": source.slug,
        "status": source.status,
        "type": source.source_type,
    }
    if verbose:
        fields["title"] = source.title
        fields["elapsed"] = f"{elapsed:.1f}s"

    print_panel("Ingestion complete", fields, json_mode)
