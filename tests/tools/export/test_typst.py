import pytest
from datetime import date
from pathlib import Path
from core.schemas import Note, ExportResult


def _make_note():
    return Note(
        uid="n1", slug="test-note", title="Test Note",
        body="## Section\n\nContent here.", docstring="A test note.",
        tags=["tag1"], note_type="synthese", source_type="youtube",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        generation_template="standard",
    )


def test_export_typst_creates_file(ctx):
    from tools.export.typst import export_typst

    ctx.db.insert_note(_make_note())

    result = export_typst("n1", ctx)

    assert isinstance(result, ExportResult)
    assert result.format == "typst"
    assert Path(result.output_path).exists()
    assert result.output_path.endswith(".typ")


def test_export_typst_contains_title(ctx):
    from tools.export.typst import export_typst

    ctx.db.insert_note(_make_note())

    result = export_typst("n1", ctx)

    content = Path(result.output_path).read_text()
    assert "Test Note" in content


def test_export_typst_not_found_raises(ctx):
    from tools.export.typst import export_typst

    with pytest.raises(ValueError, match="not found"):
        export_typst("nonexistent", ctx)
