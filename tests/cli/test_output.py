import json
import pytest
from unittest.mock import patch
from io import StringIO


def test_print_table_json_mode():
    from cli.output import print_table
    captured = StringIO()
    with patch("builtins.print", side_effect=lambda s: captured.write(s + "\n")):
        print_table(["uid", "title"], [["abc", "My Note"]], json_mode=True)
    data = json.loads(captured.getvalue())
    assert data == [{"uid": "abc", "title": "My Note"}]


def test_print_panel_json_mode():
    from cli.output import print_panel
    captured = StringIO()
    with patch("builtins.print", side_effect=lambda s: captured.write(s + "\n")):
        print_panel("Test", {"uid": "abc", "title": "My Note"}, json_mode=True)
    data = json.loads(captured.getvalue())
    assert data == {"uid": "abc", "title": "My Note"}


def test_print_error_json_mode():
    from cli.output import print_error
    captured = StringIO()
    with patch("builtins.print", side_effect=lambda s: captured.write(s + "\n")):
        print_error("Something failed", "test_error", json_mode=True)
    data = json.loads(captured.getvalue())
    assert data["error"] == "Something failed"
    assert data["code"] == "test_error"


def test_print_error_verbose_json_mode():
    from cli.output import print_error
    captured = StringIO()
    with patch("builtins.print", side_effect=lambda s: captured.write(s + "\n")):
        print_error("Something failed", "test_error", json_mode=True, verbose=True, detail="extra info")
    data = json.loads(captured.getvalue())
    assert data["detail"] == "extra info"
