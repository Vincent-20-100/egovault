"""
@loggable decorator and structured JSON logging for EgoVault v2.

Every tool call is logged automatically — zero boilerplate in tool code.
Uses a callback injected at startup so core/ stays free of infrastructure imports (G4).
"""

import json
import time
from functools import wraps
from typing import Callable

# Callback injected at app startup — signature matches _write_log's call site.
# Kept as None when logging is disabled (e.g. tests that don't need DB writes).
_log_writer: Callable | None = None


def configure(log_writer: Callable | None) -> None:
    """
    Call at app startup with a writer callback, or None to disable logging.

    Expected signature:
        writer(uid, tool_name, input_json, output_json, duration_ms, status, error) -> None
    """
    global _log_writer
    _log_writer = log_writer


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
    """Write a tool_log entry via the injected writer callback. Redacts sensitive data first."""
    if _log_writer is None:
        return
    try:
        from core.uid import generate_uid
        from core.sanitize import redact_sensitive

        _log_writer(
            generate_uid(),
            tool_name,
            redact_sensitive(input_json),
            redact_sensitive(output_json),
            duration_ms,
            status,
            redact_sensitive(error),
        )
    except Exception:
        pass  # logging must never crash the tool


def loggable(tool_name: str):
    """
    Decorator: logs every tool call to the tool_logs table.

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
