"""
@loggable decorator and structured JSON logging for EgoVault v2.

Every tool call is logged to tool_logs table automatically.
Zero boilerplate in tool code — just decorate with @loggable("tool_name").
"""

import json
import time
from functools import wraps
from pathlib import Path

_db_path: Path | None = None


def configure(db_path: Path | None) -> None:
    """Call at app startup with the resolved .system.db path. Pass None to disable."""
    global _db_path
    _db_path = db_path


def _serialize(obj) -> str:
    """
    Serialize tool input/output to JSON string.
    Pydantic models: model_dump(mode='json').
    Other types: json.dumps with str() fallback.
    """
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"))
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return str(obj)


def _elapsed_ms(start: float) -> int:
    """Return elapsed milliseconds since start."""
    return int((time.monotonic() - start) * 1000)


def _write_log(
    tool_name: str,
    input_json: str | None,
    output_json: str | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
) -> None:
    """Write a tool_log entry to .system.db. Redacts sensitive data before writing."""
    if _db_path is None:
        return
    try:
        from infrastructure.db import get_system_connection
        from core.uid import generate_uid
        from core.sanitize import redact_sensitive

        conn = get_system_connection(_db_path)
        conn.execute(
            """INSERT INTO tool_logs (uid, tool_name, input_json, output_json, duration_ms, status, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_uid(), tool_name,
             redact_sensitive(input_json),
             redact_sensitive(output_json),
             duration_ms, status,
             redact_sensitive(error)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # logging must never crash the tool


def loggable(tool_name: str):
    """
    Decorator: logs every tool call to tool_logs table.

    Tools MUST accept their primary input as first positional arg or as 'input' kwarg.
    Input/output serialized via _serialize() (Pydantic-aware).
    Duration and status recorded automatically.

    Usage:
        @loggable("transcribe")
        def transcribe(input: TranscribeInput) -> TranscriptResult: ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            input_obj = args[0] if args else kwargs.get("input")
            try:
                result = func(*args, **kwargs)
                _write_log(
                    tool_name, _serialize(input_obj),
                    _serialize(result), _elapsed_ms(start), "success"
                )
                return result
            except Exception as e:
                _write_log(
                    tool_name, _serialize(input_obj),
                    None, _elapsed_ms(start), "failed", str(e)
                )
                raise
        return wrapper
    return decorator
