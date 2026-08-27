# Logging & Observability Standard (Structured & Contextual Logs)

> **Golden Rule**: Never use `print()` for internal control flow, metrics, or error tracking. Treat logs as structured audit events that allow operators to reconstruct the exact timeline of events during a post-mortem.

---

## 🚫 1. Why `print()` is the Hallmark of Vibe-Coding

* **No Severity Levels**: Cannot differentiate between routine progress (`INFO`), slow queries (`WARNING`), or system crashes (`ERROR`).
* **Zero Context**: Lacks timestamps, process/thread IDs, module names, or correlation IDs.
* **Non-Redirectable**: Cannot be rotated, serialized to JSON, or ingested by observability tools (Datadog, Loki, CloudWatch).
* **Pollutes Standard Output**: Breaks CLI piping (e.g. `my-tool --json | jq .`).

---

## 🏛️ 2. Package / Library vs Standalone Application Governance

```
┌─────────────────────────────────────────────────────────────┐
│                    LOGGING ARCHITECTURE                     │
├──────────────────────────────┬──────────────────────────────┤
│ REUSABLE LIBRARY / CORE      │ STANDALONE APP / SERVICE     │
│ Standard library `logging`   │ `loguru` or `structlog`      │
│ `logging.getLogger(__name__)`│ Structured JSON + File sink  │
│ Attach `NullHandler()`       │ Handlers bound at startup    │
│ Never configure root handlers│ Automatic log rotation (20MB)│
└──────────────────────────────┴──────────────────────────────┘
```

### A. Reusable Packages & Core Libraries (Zero Side-Effects)
If writing a reusable library, SDK, or pure core package, **never configure handlers or enforce third-party logging engines**:
```python
"""Package root logging initialization (e.g., src/my_pkg/__init__.py)."""

import logging

# Attach NullHandler to prevent "No handler found" warnings without hijacking root
logging.getLogger("my_pkg").addHandler(logging.NullHandler())
```

Inside library modules, always use standard named loggers:
```python
import logging

logger = logging.getLogger(__name__)

def process_item(item_id: str) -> None:
    logger.debug("Processing item %s", item_id)
```

### B. Standalone Applications, CLI & Microservices
Applications configure concrete handlers at the application composition root (`main.py` / `cli.py`).

---

## 🚀 3. The Modern Application Standard: `loguru` & `structlog`

For standalone applications, `loguru` provides the highest ergonomics for colored console and rotating JSON logs:

```bash
uv add loguru
```

### Complete Logging Setup (`core/logger.py`):

```python
"""Centralized structured logger configuration."""

from pathlib import Path
import sys
from loguru import logger


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | str | None = None,
    serialize_json: bool = False,
    retention_days: int = 14,
    rotation_size: str = "20 MB",
) -> None:
    """Configure application-wide logging handlers.

    Args:
        log_level: Minimum severity level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Optional directory to store rotating log files.
        serialize_json: If True, formats file outputs as structured JSON lines.
        retention_days: Number of days before old log files are pruned.
        rotation_size: Maximum size per log file before rotation.
    """
    # Remove default handler
    logger.remove()

    # 1. Human-readable console handler (colored, clean)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format=console_format,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 2. File handler with automatic rotation & retention
    if log_dir:
        dir_path = Path(log_dir)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / "app_{time:YYYY-MM-DD}.log"

        logger.add(
            str(file_path),
            level="DEBUG",  # Capture all granular events to disk
            rotation=rotation_size,
            retention=f"{retention_days} days",
            compression="zip",
            serialize=serialize_json,  # JSON lines for automated analysis
            enqueue=True,  # Thread-safe async writing
            backtrace=True,
        )


__all__ = ["logger", "setup_logging"]
```

---

## 🏷️ 4. Contextual Logging & Trace IDs

Attach metadata to log records to follow a workflow across multiple functions or sub-processes:

```python
from core.logger import logger
import uuid


def process_user_pipeline(user_id: str, raw_payload: dict) -> dict:
    correlation_id = str(uuid.uuid4())[:8]

    # Bind contextual variables to the logger
    context_logger = logger.bind(
        correlation_id=correlation_id,
        user_id=user_id,
        payload_size=len(raw_payload),
    )

    context_logger.info("Starting processing pipeline")

    try:
        # Business logic...
        result = {"status": "success"}
        context_logger.info("Pipeline completed successfully")
        return result
    except Exception as exc:
        context_logger.exception("Pipeline execution failed unexpectedly")
        raise
```

---

## ⏱️ 5. Execution Timing & Tracing Decorators

Wrap performance-critical or entrypoint functions with automated tracing:

```python
"""Observability decorators for tracing execution time and exceptions."""

import functools
import time
from typing import Any, Callable, TypeVar
from loguru import logger

F = TypeVar("F", bound=Callable[..., Any])


def trace_execution(level: str = "DEBUG") -> Callable[[F], F]:
    """Decorator to log function entry, exit, arguments count, and elapsed time.

    Args:
        level: Log level used to output the execution trace.

    Returns:
        Decorated callable.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__
            start_time = time.perf_counter()

            logger.log(
                level,
                "Entering {func_name} with {arg_count} positional args and {kwarg_count} kwargs",
                func_name=func_name,
                arg_count=len(args),
                kwarg_count=len(kwargs),
            )

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.log(
                    level,
                    "Exited {func_name} in {elapsed_ms:.2f}ms",
                    func_name=func_name,
                    elapsed_ms=elapsed_ms,
                )
                return result
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.error(
                    "Failed {func_name} after {elapsed_ms:.2f}ms with error: {error}",
                    func_name=func_name,
                    elapsed_ms=elapsed_ms,
                    error=str(exc),
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
```

---

## 📊 6. Log Levels Governance

| Level | When to Use | Example |
| :--- | :--- | :--- |
| `DEBUG` | Granular developer details, payload shapes, loop step diagnostics. | `Query executed in 4.2ms: SELECT * FROM items WHERE id=5` |
| `INFO` | Major business milestones, service startup, completed batches. | `Loaded 1,420 records from config.toml. Server started on port 8000.` |
| `WARNING` | Degraded mode, retries, fallback usage, deprecation warnings. | `Database connection timed out (attempt 1/3). Retrying in 1.5s...` |
| `ERROR` | A specific operation failed, but application continues running. | `Failed to process user_id=45. Skipping entity.` |
| `CRITICAL` | Unrecoverable crash requiring immediate human intervention. | `Database storage volume is 100% full. Aborting execution.` |

