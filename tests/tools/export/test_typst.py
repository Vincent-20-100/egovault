import pytest
from datetime import date
from pathlib import Path
from core.schemas import Note, ExportResult
import unittest.mock as mock


def _make_note():
    return Note(
        uid="n1", slug="test-note", title="Test Note",
        body="## Section\n\nContent here.", docstring="A test note.",
        tags=["tag1"], note_type="synthese", source_type="youtube",
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
        generation_template="standard",
    )


def test_export_typst_creates_file(tmp_settings, tmp_db, tmp_path):
    from tools.export.typst import export_typst
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note())

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_typst("n1", tmp_settings)

    assert isinstance(result, ExportResult)
    assert result.format == "typst"
    assert Path(result.output_path).exists()
    assert result.output_path.endswith(".typ")


def test_export_typst_contains_title(tmp_settings, tmp_db, tmp_path):
    from tools.export.typst import export_typst
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note())

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_typst("n1", tmp_settings)

    content = Path(result.output_path).read_text()
    assert "Test Note" in content


def test_export_typst_not_found_raises(tmp_settings, tmp_db, tmp_path):
    from tools.export.typst import export_typst

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        with pytest.raises(ValueError, match="not found"):
            export_typst("nonexistent", tmp_settings)
