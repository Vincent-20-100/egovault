import pytest
from core import logging as ev_logging


def test_serialize_pydantic_model():
    from core.schemas import TranscriptResult
    result = TranscriptResult(text="hello", language="fr", duration_seconds=10.5)
    serialized = ev_logging._serialize(result)
    assert '"text": "hello"' in serialized
    assert '"language": "fr"' in serialized


def test_serialize_plain_dict():
    assert ev_logging._serialize({"key": "value"}) == '{"key": "value"}'


def test_serialize_non_serializable_fallback():
    class Unserializable:
        def __str__(self): return "custom-repr"
    result = ev_logging._serialize(Unserializable())
    assert result == "custom-repr"


def test_loggable_calls_function():
    @ev_logging.loggable("test_tool")
    def my_tool(x: int) -> int:
        return x * 2

    assert my_tool(3) == 6


def test_loggable_captures_exception():
    @ev_logging.loggable("failing_tool")
    def broken_tool(x: int) -> int:
        raise ValueError("oops")

    with pytest.raises(ValueError, match="oops"):
        broken_tool(1)


def test_loggable_writes_to_db_when_configured(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "log_test.db"
    init_db(db_file)
    ev_logging.configure(db_file)

    @ev_logging.loggable("my_logged_tool")
    def add(a: int, b: int) -> int:
        return a + b

    add(1, 2)

    conn = get_vault_connection(db_file)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'my_logged_tool'").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    assert rows[0]["duration_ms"] >= 0

    # cleanup: reset _db_path to avoid polluting other tests
    ev_logging.configure(None)


def test_loggable_writes_failed_status_to_db(tmp_path):
    from infrastructure.db import init_db, get_vault_connection
    db_file = tmp_path / "log_test2.db"
    init_db(db_file)
    ev_logging.configure(db_file)

    @ev_logging.loggable("bad_tool")
    def always_fails(x: int) -> int:
        raise RuntimeError("bad")

    with pytest.raises(RuntimeError):
        always_fails(5)

    conn = get_vault_connection(db_file)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'bad_tool'").fetchall()
    conn.close()

    assert rows[0]["status"] == "failed"
    assert "bad" in rows[0]["error"]
    ev_logging.configure(None)


def test_loggable_writes_to_system_db(tmp_path):
    from infrastructure.db import init_system_db, get_system_connection
    from core.logging import loggable, configure

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)
    configure(system_db)

    @loggable("test_tool")
    def my_tool(x: int) -> int:
        return x * 2

    my_tool(5)

    conn = get_system_connection(system_db)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'test_tool'").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    configure(None)


def test_loggable_logs_failure_to_system_db(tmp_path):
    from infrastructure.db import init_system_db, get_system_connection
    from core.logging import loggable, configure

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)
    configure(system_db)

    @loggable("failing_tool")
    def bad_tool(x: int) -> int:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        bad_tool(1)

    conn = get_system_connection(system_db)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'failing_tool'").fetchall()
    conn.close()
    assert rows[0]["status"] == "failed"
    assert rows[0]["error"] == "boom"
    configure(None)


def test_write_log_redacts_sensitive_data(tmp_path, monkeypatch):
    """Tool logs must redact API keys before writing."""
    from core import logging as log_mod
    from core.sanitize import redact_sensitive

    db_path = tmp_path / ".system.db"

    # Init system DB
    from infrastructure.db import init_system_db
    init_system_db(db_path)
    log_mod.configure(db_path)

    # Write a log entry with a fake API key
    log_mod._write_log(
        tool_name="test_tool",
        input_json='{"api_key": "sk-abc123def456ghi789jkl012mno345pqr678"}',
        output_json=None,
        duration_ms=100,
        status="success",
        error=None,
    )

    # Read back and check redaction
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT input_json FROM tool_logs ORDER BY rowid DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    assert "sk-abc123" not in row[0]
    assert "***REDACTED***" in row[0]
