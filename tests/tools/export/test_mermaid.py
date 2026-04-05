import pytest
from datetime import date
from pathlib import Path
from core.schemas import Note, ExportResult
import unittest.mock as mock


def _make_note(uid, slug, tags):
    return Note(
        uid=uid, slug=slug, title=f"Note {uid}",
        body="Body content here.", docstring="Docstring.",
        tags=tags,
        date_created=date.today().isoformat(), date_modified=date.today().isoformat(),
    )


def test_export_mermaid_by_note_uid(tmp_settings, tmp_db, tmp_path):
    from tools.export.mermaid import export_mermaid
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note("n1", "note-one", ["bitcoin", "finance"]))
    insert_note(tmp_db, _make_note("n2", "note-two", ["bitcoin"]))

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_mermaid(tmp_settings, note_uid="n1")

    assert isinstance(result, ExportResult)
    assert result.format == "mermaid"
    assert Path(result.output_path).exists()
    content = Path(result.output_path).read_text()
    assert "graph" in content.lower() or "flowchart" in content.lower()


def test_export_mermaid_by_tag(tmp_settings, tmp_db, tmp_path):
    from tools.export.mermaid import export_mermaid
    from infrastructure.db import insert_note

    insert_note(tmp_db, _make_note("n1", "note-one", ["bitcoin"]))
    insert_note(tmp_db, _make_note("n2", "note-two", ["bitcoin"]))

    with mock.patch.object(type(tmp_settings), "vault_db_path",
                           new_callable=lambda: property(lambda self: tmp_db)), \
         mock.patch.object(type(tmp_settings), "media_path",
                           new_callable=lambda: property(lambda self: tmp_path)):
        result = export_mermaid(tmp_settings, tag="bitcoin")

    content = Path(result.output_path).read_text()
    assert "note-one" in content or "Note n1" in content or "n1" in content


def test_export_mermaid_no_args_raises(tmp_settings):
    from tools.export.mermaid import export_mermaid

    with pytest.raises(ValueError, match="note_uid.*tag"):
        export_mermaid(tmp_settings)
