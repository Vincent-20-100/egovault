"""
Document export tool — generates print-ready Typst source from a note.

Input  : note uid
Output : ExportResult (path to .typ file)
No DB write.

Defensive defaults follow the typst-clean skill (Typst 0.14.x):
font fallback chain, explicit lang, breakable raw/figure, readable spacing.
"""

from pathlib import Path

from core.context import VaultContext
from core.schemas import ExportResult
from core.logging import loggable


_ESCAPE_CHARS = ("\\", "#", "$", "@", "*", "[", "]", "<", "`")


def _escape_typst(s: str) -> str:
    """Escape characters that would otherwise be parsed as Typst markup."""
    for ch in _ESCAPE_CHARS:
        s = s.replace(ch, "\\" + ch)
    return s


def _escape_typst_string(s: str) -> str:
    """Escape for inside a Typst "..." string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _note_to_typst(note, lang: str, font: str) -> str:
    """Generate Typst source from a Note record."""
    title_markup = _escape_typst(note.title)
    title_string = _escape_typst_string(note.title)
    region = lang.upper() if len(lang) == 2 else "FR"

    fallback_chain = ", ".join(
        f'"{f}"' for f in (
            font,
            "DejaVu Serif",
            "Segoe UI Symbol",
            "Segoe UI Emoji",
            "DejaVu Sans",
        )
    )

    lines = [
        f'#set document(title: "{title_string}")',
        '#set page(paper: "a4", margin: (x: 2.2cm, y: 2.4cm), numbering: "1 / 1", number-align: center)',
        f'#set text(lang: "{lang}", region: "{region}", font: ({fallback_chain}), size: 10.5pt, fallback: true)',
        '#set par(justify: true, leading: 0.72em, spacing: 0.95em, linebreaks: "optimized")',
        '#set list(spacing: 0.55em, indent: 0.6em)',
        '#set enum(spacing: 0.55em, indent: 0.6em)',
        '#set heading(numbering: "1.1")',
        '#show figure: set block(breakable: true)',
        '#set table(stroke: 0.4pt + luma(60%), inset: 6pt)',
        '#show table: set text(size: 9pt)',
        '#show raw.where(block: true): it => block(breakable: true, width: 100%, fill: luma(245), inset: 8pt, radius: 3pt, text(font: ("Consolas", "DejaVu Sans Mono"), size: 9pt, it))',
        '#show raw.where(block: false): it => box(fill: luma(245), inset: (x: 3pt, y: 0pt), outset: (y: 2pt), radius: 2pt, text(font: ("Consolas", "DejaVu Sans Mono"), size: 0.95em, it))',
        '#show link: set text(fill: rgb("#0b5394"))',
        '',
        f'= {title_markup}',
        '',
    ]
    if note.docstring:
        lines += [f'#quote[{_escape_typst(note.docstring)}]', '']
    if note.tags:
        tags_esc = ", ".join(_escape_typst(t) for t in note.tags)
        lines += [f'#text(gray)[Tags: {tags_esc}]', '']
    lines += ['#line(length: 100%, stroke: 0.5pt + luma(70%))', '', note.body]
    return '\n'.join(lines)


@loggable("export_typst")
def export_typst(
    note_uid: str,
    ctx: VaultContext,
    lang: str = "fr",
    font: str = "Times New Roman",
) -> ExportResult:
    """Export a note to a print-ready Typst document."""
    note = ctx.db.get_note(note_uid)
    if note is None:
        raise ValueError(f"Note not found: {note_uid}")

    output_dir = ctx.media_path / note.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{note.slug}.typ"
    output_path.write_text(_note_to_typst(note, lang=lang, font=font), encoding="utf-8")

    return ExportResult(output_path=str(output_path), format="typst")
