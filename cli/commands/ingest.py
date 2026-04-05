"""
Ingest command — dispatches to the right workflow based on input type.

Routing layer only. No business logic.
"""

import time
from pathlib import Path
from typing import Annotated

import typer

from cli.output import print_panel, print_error, spinner

app = typer.Typer(help="Ingest a YouTube URL, audio file, or PDF into the vault.")

_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}
_YOUTUBE_PATTERNS = ("youtube.com", "youtu.be")


def _build_ctx():
    from core.config import load_settings
    from infrastructure.context import build_context
    return build_context(load_settings())


def _detect_type(target: str) -> str:
    if any(p in target for p in _YOUTUBE_PATTERNS):
        return "youtube"
    ext = Path(target).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in _AUDIO_EXTENSIONS:
        return "audio"
    raise ValueError(f"Unsupported input: '{target}'. Provide a YouTube URL, audio file, or PDF.")


def _run_ingest(input_type: str, target: str, ctx, auto_generate_note=None):
    if input_type == "youtube":
        from workflows.ingest_youtube import ingest_youtube
        return ingest_youtube(target, ctx, auto_generate_note=auto_generate_note)
    elif input_type == "audio":
        from workflows.ingest_audio import ingest_audio
        return ingest_audio(target, ctx, auto_generate_note=auto_generate_note)
    else:
        from workflows.ingest_pdf import ingest_pdf
        return ingest_pdf(target, ctx, auto_generate_note=auto_generate_note)


@app.command()
def ingest(
    target: Annotated[str, typer.Argument(help="YouTube URL or path to audio/PDF file")],
    generate_note: Annotated[
        bool | None,
        typer.Option("--generate-note/--no-generate-note",
                     help="Generate a draft note after ingestion. Default: reads user.yaml.")
    ] = None,
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show step timings and details")] = False,
) -> None:
    """Ingest a YouTube URL, audio file, or PDF into the vault."""
    from core.errors import LargeFormatError

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
                                 auto_generate_note=generate_note)
    except LargeFormatError as e:
        print_error(
            "Source is too large for automatic note generation. "
            "It has been indexed and is searchable. Create the note manually.",
            "large_format",
            json_mode, verbose,
            f"token_count={e.token_count}, threshold={e.threshold}, source_uid={e.source_uid}",
        )
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
