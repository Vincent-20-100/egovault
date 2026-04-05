"""
Document export tool — generates print-ready output from a note.

Input  : note uid
Output : ExportResult (path to .typ file)
No DB write.
"""

from pathlib import Path

from core.context import VaultContext
from core.schemas import ExportResult
from core.logging import loggable


def _note_to_typst(note) -> str:
    """Generate Typst source from a Note record."""
    safe_title = note.title.replace("\\", "\\\\").replace('"', '\\"')
    lines = [
        f'#set document(title: "{safe_title}")',
        '#set page(margin: 2cm)',
        '#set text(font: "Linux Libertine", size: 11pt)',
        '',
        f'= {note.title}',
        '',
    ]
    if note.docstring:
        lines += [f'#quote[{note.docstring}]', '']
    if note.tags:
        lines += [f'#text(gray)[Tags: {", ".join(note.tags)}]', '']
    lines += ['---', '', note.body]
    return '\n'.join(lines)


@loggable("export_typst")
def export_typst(note_uid: str, ctx: VaultContext) -> ExportResult:
    """
    Export a note to Typst format (.typ file).
    Reads note from DB, generates a print-ready document.
    Output written to media/<slug>/<slug>.typ.
    No DB write.
    """
    note = ctx.db.get_note(note_uid)
    if note is None:
        raise ValueError(f"Note not found: {note_uid}")

    output_dir = ctx.media_path / note.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{note.slug}.typ"
    output_path.write_text(_note_to_typst(note), encoding="utf-8")

    return ExportResult(output_path=str(output_path), format="typst")
