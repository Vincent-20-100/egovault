import pytest
from datetime import date
from pathlib import Path
from core.schemas import Note, ExportResult


def _make_note(uid, slug, tags):
    return Note(
        uid=uid, slug=slug, title=f"Note {uid}",
        body="Body content here.", docstring="Docstring.",
        tags=tags,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )


def test_export_mermaid_by_note_uid(ctx):
    from tools.export.mermaid import export_mermaid

    ctx.db.insert_note(_make_note("n1", "note-one", ["bitcoin", "finance"]))
    ctx.db.insert_note(_make_note("n2", "note-two", ["bitcoin"]))

    result = export_mermaid(ctx, note_uid="n1")

    assert isinstance(result, ExportResult)
    assert result.format == "mermaid"
    assert Path(result.output_path).exists()
    content = Path(result.output_path).read_text()
    assert "graph" in content.lower() or "flowchart" in content.lower()


def test_export_mermaid_by_tag(ctx):
    from tools.export.mermaid import export_mermaid

    ctx.db.insert_note(_make_note("n1", "note-one", ["bitcoin"]))
    ctx.db.insert_note(_make_note("n2", "note-two", ["bitcoin"]))

    result = export_mermaid(ctx, tag="bitcoin")

    content = Path(result.output_path).read_text()
    assert "note-one" in content or "Note n1" in content or "n1" in content


def test_export_mermaid_no_args_raises(ctx):
    from tools.export.mermaid import export_mermaid

    with pytest.raises(ValueError, match="note_uid.*tag"):
        export_mermaid(ctx)
