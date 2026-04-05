"""
@loggable decorator and structured JSON logging for EgoVault v2.

Every tool call is logged automatically — zero boilerplate in tool code.
Uses a callback injected at startup so core/ stays free of infrastructure imports (G4).
run_id propagated via contextvars — thread-safe, async-safe, zero tool signature changes.
"""

import json
import time
from contextvars import ContextVar, Token
from functools import wraps
from typing import Callable

_log_writer: Callable | None = None

_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)


def set_run_id(run_id: str) -> Token:
    """Set the current workflow run_id. Returns a token for reset."""
    return _run_id.set(run_id)


def reset_run_id(token: Token) -> None:
    """Reset run_id to its previous value."""
    _run_id.reset(token)


def get_run_id() -> str | None:
    """Get the current workflow run_id (or None)."""
    return _run_id.get()


def configure(log_writer: Callable | None) -> None:
    """
    Call at app startup with a writer callback, or None to disable logging.

    Expected signature:
        writer(uid, tool_name, input_json, output_json, duration_ms, status, error,
               run_id=None, token_count=None, provider=None) -> None
    """
    global _log_writer
    _log_writer = log_writer


def _serialize(obj) -> str:
    """Serialize tool input/output to JSON string."""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"))
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return str(obj)


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _extract_token_count(result) -> int | None:
    """Auto-extract token_count from result if available."""
    for attr in ("token_count", "tokens_used", "total_tokens"):
        val = getattr(result, attr, None)
        if isinstance(val, int):
            return val
    if isinstance(result, dict):
        for key in ("token_count", "tokens_used", "total_tokens"):
            val = result.get(key)
            if isinstance(val, int):
                return val
    return None


def _write_log(
    tool_name: str,
    input_json: str | None,
    output_json: str | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
    token_count: int | None = None,
    provider: str | None = None,
) -> None:
    """Write a tool_log entry via the injected writer callback."""
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
            run_id=_run_id.get(),
            token_count=token_count,
            provider=provider,
        )
    except Exception:
        pass  # logging must never crash the tool


def loggable(tool_name: str, provider: str | None = None):
    """
    Decorator: logs every tool call to the tool_logs table.

    Automatically captures run_id (from contextvars), token_count (from result),
    and provider (from decorator arg or None).
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
                    _serialize(result), _elapsed_ms(start), "success",
                    token_count=_extract_token_count(result),
                    provider=provider,
                )
                return result
            except Exception as e:
                _write_log(
                    tool_name, _serialize(input_obj),
                    None, _elapsed_ms(start), "failed", str(e),
                    provider=provider,
                )
                raise
        return wrapper
    return decorator
