# Error Architecture & Resilience Standard (`errors.py`)

> **Core Philosophy**: Exceptions are an explicit part of your domain contract. Never throw bare `Exception`, never swallow errors silently with `except: pass`, and never leave users/callers with a cryptic traceback and no actionable remedy.

---

## 🏛️ 1. The Centralized `errors.py` Architecture

Every production package should provide a single, well-structured `core/errors.py` defining its domain exception tree:

```
                  AppError (Base Exception)
                     │
     ┌───────────────┼───────────────┬───────────────┐
     ▼               ▼               ▼               ▼
ConfigError     DomainError     InfraError     ContractError
     │               │               │               │
     ├── MissingKey  ├── NotFound    ├── DBTimeout   └── TypeMismatch
     └── BadFormat   ├── Conflict    └── APIRateLimit
```

---

## 💻 2. Complete Reference Implementation (`core/errors.py`)

```python
"""Domain exception hierarchy with structured error codes and actionable hints."""

from typing import Any, Mapping


class AppError(Exception):
    """Root application exception for all managed domain errors.

    Attributes:
        message: Human-readable explanation of what went wrong.
        error_code: Unique uppercase machine code (e.g., ERR_DATABASE_LOCKED).
        context: Key-value dictionary containing runtime variables that caused the error.
        actionable_hint: Plain-language instructions to fix the issue.
        http_status: Suggested HTTP status code if mapped to a web API.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_INTERNAL",
        context: Mapping[str, Any] | None = None,
        actionable_hint: str | None = None,
        http_status: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = dict(context or {})
        self.actionable_hint = actionable_hint or "Review application logs for troubleshooting."
        self.http_status = http_status

    def to_dict(self) -> dict[str, Any]:
        """Serialize error for logging, API response, or IPC communication."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "actionable_hint": self.actionable_hint,
            "http_status": self.http_status,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.error_code!r}, "
            f"msg={self.message!r}, "
            f"context={self.context!r})"
        )


# ==========================================
# 1. Configuration & Startup Errors
# ==========================================

class ConfigurationError(AppError):
    """Raised when configuration loading, parsing, or validation fails."""

    def __init__(
        self,
        message: str,
        key: str | None = None,
        actionable_hint: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        if key:
            ctx["config_key"] = key
        super().__init__(
            message=message,
            error_code="ERR_CONFIG_INVALID",
            context=ctx,
            actionable_hint=actionable_hint or "Verify your config.toml or environment variables.",
            http_status=500,
        )


# ==========================================
# 2. Domain & Business Rule Errors
# ==========================================

class EntityNotFoundError(AppError):
    """Raised when a requested resource or domain entity does not exist."""

    def __init__(
        self,
        entity_name: str,
        entity_id: str | int,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        ctx.update({"entity_name": entity_name, "entity_id": str(entity_id)})
        super().__init__(
            message=f"{entity_name} with ID '{entity_id}' was not found.",
            error_code=f"ERR_{entity_name.upper()}_NOT_FOUND",
            context=ctx,
            actionable_hint="Verify the identifier and ensure the entity has been created.",
            http_status=404,
        )


class ValidationError(AppError):
    """Raised when data fails domain validation invariants."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        if field_name:
            ctx["field_name"] = field_name
        super().__init__(
            message=message,
            error_code="ERR_VALIDATION_FAILED",
            context=ctx,
            actionable_hint="Ensure the input data meets the required constraints.",
            http_status=422,
        )


# ==========================================
# 3. Infrastructure & External Services Errors
# ==========================================

class InfrastructureError(AppError):
    """Raised when third-party services, I/O, or databases fail."""

    def __init__(
        self,
        message: str,
        service_name: str,
        error_code: str = "ERR_INFRASTRUCTURE",
        context: Mapping[str, Any] | None = None,
        actionable_hint: str | None = None,
        http_status: int = 502,
    ) -> None:
        ctx = dict(context or {})
        ctx["service_name"] = service_name
        super().__init__(
            message=message,
            error_code=error_code,
            context=ctx,
            actionable_hint=actionable_hint or f"Check availability of {service_name}.",
            http_status=http_status,
        )
```

---

## 🔗 3. Exception Chaining (`raise ... from err`)

Never lose root cause stack traces. Always use Python's explicit exception chaining:

```python
import httpx
from core.errors import InfrastructureError


def fetch_remote_profile(user_id: str, api_url: str, timeout: float) -> dict:
    try:
        response = httpx.get(f"{api_url}/users/{user_id}", timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise InfrastructureError(
            message=f"Timeout connecting to remote user service for user_id={user_id}",
            service_name="UserService",
            error_code="ERR_REMOTE_TIMEOUT",
            context={"user_id": user_id, "timeout": timeout},
            actionable_hint="Check remote server network status or increase timeout_seconds in config.toml.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise InfrastructureError(
            message=f"User service returned HTTP {exc.response.status_code}",
            service_name="UserService",
            error_code=f"ERR_REMOTE_HTTP_{exc.response.status_code}",
            context={"status_code": exc.response.status_code, "body": exc.response.text[:200]},
            http_status=502,
        ) from exc
```

---

## 🔁 4. Resilience & Retry Strategy (`tenacity`)

Use robust retry policies on transient network/IO operations instead of ad-hoc `while` loops:

```bash
uv add tenacity
```

```python
"""Resilient execution with exponential backoff."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
from core.errors import InfrastructureError

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(InfrastructureError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def execute_resilient_query(query: str) -> list[dict]:
    """Execute query with automatic retries on transient infra failures."""
    ...
```

---

## 🚫 Error Anti-Patterns to Ban

* ❌ `except:` or `except Exception:` with nothing but a `pass` or `print(e)`.
* ❌ Raising generic string exceptions (`raise "Something broke"`).
* ❌ Hiding original causes without `from err` chaining.
* ❌ Returning `None` to indicate an error state instead of raising a typed exception or `Result` type.
