# Code Style & Architecture Conventions (`rules/code_style.md`)

> **Enforcement**: Automated via formatters/linters (`ruff check`, `ruff format`) and senior engineering discipline.

---

## 1. Modern Typing & Signatures
- Strict type annotations on all function, method, and constructor signatures (parameters and return types).
- Use modern Python 3.10+ union and container syntax: `str | None`, `list[int]`, `dict[str, float]`, `tuple[int, ...]`.
- Avoid untyped `Any` — use explicit generic types, `TypeVar`, or `typing.Protocol` interfaces for structural typing.

---

## 2. Data Contracts, Functional Programming & Composition
- **Strict Typing is Non-Negotiable**: Never pass raw, untyped dictionaries (`dict[str, Any]`) across module boundaries.
- **Inheritance is Prohibited for Logic**: Deep class hierarchies create fragile coupling. Favor **Composition over Inheritance**, `typing.Protocol` interfaces, and pure functions.
- **Apply Functional Programming (FP) Ideas**:
  - Treat data transformations as pure mathematical mappings: immutable inputs $\implies$ deterministic outputs.
  - Zero in-place DataFrame mutations (`inplace=True` is banned; use Polars expression chains).
- **Domain-Driven Isolation (DDD)**: Keep pure domain rules and calculation logic in `core/` isolated from external databases, networks, and storage adapters in `adapters/`.
- **Pipelines as Build Systems**: Design data transformations with build system semantics (DAG dependency tracking, idempotent partitions, deterministic caching, atomic writes).

---

## 3. Configuration vs Code
- Business parameters, thresholds, model hyperparameters, file paths, and external endpoints belong in configuration files (`.toml`, `.yaml`, or environment variables via `pydantic-settings`), never hardcoded in source logic.
- Technical, module-internal constants stay in code as `SCREAMING_SNAKE_CASE`.

---

## 4. Filesystem & Path Operations
- Always use `pathlib.Path` for all path manipulations and file I/O.
- Never use raw string concatenation (`path + "/file.csv"`) or legacy `os.path`.

---

## 5. Reuse Over Reinvention (Library-First)
- Before writing a new utility, check the existing repository (`src/`, `scripts/`) to avoid duplicate logic.
- Before writing custom logic for standard engineering challenges (parsing, retries, HTTP, CLI parsing, data validation), check whether an established, actively maintained library covers it (e.g. `pydantic`, `tenacity`, `httpx`, `typer`, `sqlglot`).

---

## 6. Determinism & Reproducibility
- Never rely on unseeded randomness or unparameterized wall-clock calls (`datetime.now()`, `random.random()`) inside core logic.
- Inject seeds and reference timestamps as explicit parameters to guarantee reproducible behavior in tests and production.

---

## 7. Logging & Clean Output
- Never use raw `print()` statements inside reusable packages (`src/`) — use standard `logging` or structured loggers.
- **Log Level Discipline**:
  - `ERROR`: Accompanying an actual failure with context.
  - `WARNING`: Recoverable anomalies (retries, skipped malformed records, deprecations).
  - `INFO`: Milestone progress (stage start/finish, processed row counts, throughput).
  - `DEBUG`: Verbose internal state, off by default.
- Never log secrets, credentials, API keys, or personally identifiable information (PII).
- Log at batch/milestone level in data loops, never per-row on large datasets.

---

## 8. Naming & Language Conventions
- **Language**: All code, function names, docstrings, comments, and commit messages must be in **English**.
- **Files & Modules**: `snake_case.py` (e.g. `data_cleaner.py`).
- **Functions & Variables**: `snake_case` (e.g. `compute_daily_returns`).
- **Classes & Models**: `PascalCase` (e.g. `MarketDataFeed`).
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g. `MAX_RETRY_ATTEMPTS`).
- **Private helpers**: `_leading_underscore` (e.g. `_sanitize_token`).
- **Docstrings**: Google-style or NumPy-style docstrings describing **WHAT** and **WHY** on public APIs. Skip redundant docstrings on trivial one-liners.

---

## 9. Error Architecture & Fail-Fast
- **Fail Fast at Boundaries**: Validate untrusted inputs, external APIs, and raw files immediately upon ingestion; trust validated internal domain objects.
- **No Silent Error Swallowing**: Every `try...except` must either log at `ERROR` level with contextual diagnostics or re-raise. Bare `except: pass` is prohibited.
- **Specific Exceptions**: Always catch specific exception classes (`ValueError`, `FileNotFoundError`), never bare `except:`.
- **Safe Command Construction**: Never build SQL or shell commands via string interpolation. Use parameterized queries and `subprocess.run(["cmd", "arg"], shell=False)`.

### Centralized Exception Hierarchy
Define domain-specific exceptions in a single `errors.py` module per package:

```python
class ProjectError(Exception):
    """Base exception for all domain-specific errors in this project."""


class DataContractViolationError(ProjectError):
    """Raised when incoming dataset violates required schema invariants.
    
    Debug: verify input columns and types against schema definition in contracts.py.
    """
```
