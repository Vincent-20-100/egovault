"""Tests for tools/export/typst.py"""


def test_note_to_typst_escapes_quotes():
    """Titles with quotes must be escaped in Typst document()."""
    from tools.export.typst import _note_to_typst
    from unittest.mock import MagicMock

    note = MagicMock()
    note.title = 'Test "with quotes" and \\backslash'
    note.docstring = None
    note.tags = []
    note.body = "Body text"

    result = _note_to_typst(note)
    assert r'\"with quotes\"' in result
    assert r'\\backslash' in result
