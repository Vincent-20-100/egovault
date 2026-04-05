import pytest
from core import logging as ev_logging


# ---------------------------------------------------------------------------
# Helper — builds a writer callback backed by a real system DB.
# ---------------------------------------------------------------------------
def _make_log_writer(system_db_path):
    from infrastructure.db import get_system_connection

    def writer(uid, tool_name, input_json, output_json, duration_ms, status, error,
               run_id=None, token_count=None, provider=None):
        conn = get_system_connection(system_db_path)
        conn.execute(
            """INSERT INTO tool_logs
               (uid, run_id, tool_name, input_json, output_json, duration_ms,
                token_count, provider, status, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, run_id, tool_name, input_json, output_json, duration_ms,
             token_count, provider, status, error),
        )
        conn.commit()
        conn.close()
    return writer


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
    from infrastructure.db import init_system_db, get_system_connection
    db_file = tmp_path / "log_test.db"
    init_system_db(db_file)
    ev_logging.configure(_make_log_writer(db_file))

    @ev_logging.loggable("my_logged_tool")
    def add(a: int, b: int) -> int:
        return a + b

    add(1, 2)

    conn = get_system_connection(db_file)
    rows = conn.execute("SELECT * FROM tool_logs WHERE tool_name = 'my_logged_tool'").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    assert rows[0]["duration_ms"] >= 0

    ev_logging.configure(None)


def test_loggable_writes_failed_status_to_db(tmp_path):
    from infrastructure.db import init_system_db, get_system_connection
    db_file = tmp_path / "log_test2.db"
    init_system_db(db_file)
    ev_logging.configure(_make_log_writer(db_file))

    @ev_logging.loggable("bad_tool")
    def always_fails(x: int) -> int:
        raise RuntimeError("bad")

    with pytest.raises(RuntimeError):
        always_fails(5)

    conn = get_system_connection(db_file)
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
    configure(_make_log_writer(system_db))

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
    configure(_make_log_writer(system_db))

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


def test_write_log_redacts_sensitive_data(tmp_path):
    from core import logging as log_mod
    from infrastructure.db import init_system_db

    db_path = tmp_path / ".system.db"
    init_system_db(db_path)
    log_mod.configure(_make_log_writer(db_path))

    log_mod._write_log(
        tool_name="test_tool",
        input_json='{"api_key": "sk-abc123def456ghi789jkl012mno345pqr678"}',
        output_json=None,
        duration_ms=100,
        status="success",
        error=None,
    )

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT input_json FROM tool_logs ORDER BY rowid DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    assert "sk-abc123" not in row[0]
    assert "***REDACTED***" in row[0]
    log_mod.configure(None)


# ---------------------------------------------------------------------------
# NEW — run_id, token_count, provider
# ---------------------------------------------------------------------------


def test_run_id_propagation(tmp_path):
    """run_id set via contextvars is automatically captured in tool_logs."""
    from infrastructure.db import init_system_db, get_system_connection
    from core.logging import loggable, configure, set_run_id, reset_run_id

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)
    configure(_make_log_writer(system_db))

    @loggable("tracked_tool")
    def my_tool(x: int) -> int:
        return x + 1

    token = set_run_id("run-123")
    try:
        my_tool(5)
    finally:
        reset_run_id(token)

    conn = get_system_connection(system_db)
    row = conn.execute("SELECT run_id FROM tool_logs WHERE tool_name = 'tracked_tool'").fetchone()
    conn.close()
    assert row["run_id"] == "run-123"
    configure(None)


def test_run_id_none_when_not_set(tmp_path):
    """Without set_run_id, run_id is NULL."""
    from infrastructure.db import init_system_db, get_system_connection
    from core.logging import loggable, configure

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)
    configure(_make_log_writer(system_db))

    @loggable("untracked_tool")
    def my_tool(x: int) -> int:
        return x

    my_tool(1)

    conn = get_system_connection(system_db)
    row = conn.execute("SELECT run_id FROM tool_logs WHERE tool_name = 'untracked_tool'").fetchone()
    conn.close()
    assert row["run_id"] is None
    configure(None)


def test_token_count_extracted_from_result(tmp_path):
    """token_count is auto-extracted from result's token_count attribute."""
    from infrastructure.db import init_system_db, get_system_connection
    from core.logging import loggable, configure
    from pydantic import BaseModel

    class ResultWithTokens(BaseModel):
        value: str
        token_count: int

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)
    configure(_make_log_writer(system_db))

    @loggable("token_tool")
    def my_tool(x: str) -> ResultWithTokens:
        return ResultWithTokens(value=x, token_count=42)

    my_tool("hello")

    conn = get_system_connection(system_db)
    row = conn.execute("SELECT token_count FROM tool_logs WHERE tool_name = 'token_tool'").fetchone()
    conn.close()
    assert row["token_count"] == 42
    configure(None)


def test_provider_captured_from_decorator(tmp_path):
    """provider param from @loggable is stored in tool_logs."""
    from infrastructure.db import init_system_db, get_system_connection
    from core.logging import loggable, configure

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)
    configure(_make_log_writer(system_db))

    @loggable("embed_tool", provider="ollama")
    def my_embed(text: str) -> list:
        return [0.1, 0.2]

    my_embed("test")

    conn = get_system_connection(system_db)
    row = conn.execute("SELECT provider FROM tool_logs WHERE tool_name = 'embed_tool'").fetchone()
    conn.close()
    assert row["provider"] == "ollama"
    configure(None)


# ---------------------------------------------------------------------------
# Workflow run DB functions
# ---------------------------------------------------------------------------


def test_workflow_run_crud(tmp_path):
    from infrastructure.db import (
        init_system_db, create_workflow_run, close_workflow_run,
        get_workflow_runs, get_workflow_run_detail, get_workflow_run_cost,
    )

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)

    create_workflow_run(system_db, "run-1", "ingest_youtube", source_uid="src-1")

    runs = get_workflow_runs(system_db)
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-1"
    assert runs[0]["status"] == "running"

    close_workflow_run(system_db, "run-1", "success")
    runs = get_workflow_runs(system_db, status="success")
    assert len(runs) == 1
    assert runs[0]["ended_at"] is not None

    detail = get_workflow_run_detail(system_db, "run-1")
    assert detail is not None
    assert detail["run"]["workflow"] == "ingest_youtube"
    assert detail["tool_logs"] == []

    cost = get_workflow_run_cost(system_db, "run-1")
    assert cost["total_tokens"] == 0
    assert cost["tool_count"] == 0


def test_workflow_run_not_found(tmp_path):
    from infrastructure.db import init_system_db, get_workflow_run_detail, get_workflow_run_cost

    system_db = tmp_path / ".system.db"
    init_system_db(system_db)

    assert get_workflow_run_detail(system_db, "nonexistent") is None
    assert get_workflow_run_cost(system_db, "nonexistent") is None
