# Architecture & Layer Boundaries (Hexagonal Isolation & Contract Decorators)

> **Golden Rule**: Maintain strict one-way dependency flow. Domain business logic must never directly import database drivers, UI frameworks, or low-level external SDKs.

---

## 🏛️ 1. The Hexagonal / Clean Package Layout

```
src/my_project/
├── core/                  # ZERO dependencies on other packages
│   ├── config.py          # Pydantic Settings & TOML loader
│   ├── errors.py          # Hierarchical domain exceptions
│   ├── models.py          # Domain entities & Pydantic data schemas
│   ├── protocols.py       # Structural typing interfaces (typing.Protocol)
│   └── context.py         # Application Context container
├── services/              # Pure domain logic & orchestration
│   ├── document_parser.py # Transforms data using core protocols
│   └── indexer.py         # Business workflows
├── adapters/              # Concrete I/O implementations
│   ├── storage_sqlite.py  # Implements StorageProtocol via SQLite
│   └── http_client.py     # Implements APIProtocol via httpx
└── cli/ or api/           # Thin user/machine interfaces
    ├── main.py            # Typer CLI or FastAPI routes
    └── formatters.py      # Output rendering (Rich / JSON)
```

### Dependency Flow (Strictly Acyclic):
```
[ CLI / API / Web ] ──▶ [ Services / Use Cases ] ──▶ [ Core (Models, Protocols, Errors) ]
                               │                               ▲
                               ▼                               │
                      [ Adapters / Infra ] ────────────────────┘
```

---

## 🔌 2. Interfaces via `typing.Protocol` (Dependency Inversion)

Define what your domain needs in `core/protocols.py` without importing concrete databases or SDKs:

```python
"""Domain interface protocols."""

from typing import Protocol, Sequence, runtime_checkable
from core.models import Document, DocumentId


@runtime_checkable
class DocumentStorage(Protocol):
    """Contract for document persistence engines."""

    def save(self, document: Document) -> None:
        """Persist a single document.

        Raises:
            InfrastructureError: On database write failure.
        """
        ...

    def get_by_id(self, doc_id: DocumentId) -> Document | None:
        """Retrieve a document by identifier."""
        ...

    def search(self, query: str, limit: int = 10) -> Sequence[Document]:
        """Search documents by keyword."""
        ...
```

The SQLite adapter implements this interface implicitly (*duck typing*) without needing to subclass it directly:

```python
"""Concrete SQLite adapter satisfying DocumentStorage protocol."""

import sqlite3
from core.models import Document, DocumentId
from core.errors import InfrastructureError


class SQLiteDocumentStorage:
    """SQLite implementation of DocumentStorage protocol."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def save(self, document: Document) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO docs (id, title, body) VALUES (?, ?, ?)",
                    (document.id, document.title, document.body),
                )
        except sqlite3.Error as exc:
            raise InfrastructureError(
                message=f"Failed to save document {document.id} to SQLite",
                service_name="SQLiteStorage",
                context={"doc_id": document.id},
            ) from exc

### 🧪 2.1. Testing with In-Memory Fakes over Fragile Mocks

When domain interfaces use `Protocol`, write **In-Memory Fakes** for unit and integration testing rather than scattering fragile `MagicMock` calls:

```python
"""In-memory test fake implementing DocumentStorage protocol."""

from core.models import Document, DocumentId


class InMemoryDocumentStorage:
    """High-fidelity fake storage for unit tests."""

    def __init__(self) -> None:
        self.docs: dict[DocumentId, Document] = {}

    def save(self, document: Document) -> None:
        self.docs[document.id] = document

    def get_by_id(self, doc_id: DocumentId) -> Document | None:
        return self.docs.get(doc_id)

    def search(self, query: str, limit: int = 10) -> list[Document]:
        return [
            doc for doc in self.docs.values()
            if query.lower() in doc.title.lower() or query.lower() in doc.body.lower()
        ][:limit]
```

* **Why Fakes beat Mocks**:
  1. **Contract fidelity**: The fake exercises real domain workflows and catches subtle contract regressions.
  2. **Refactoring resilience**: Internal refactorings won't break mock expectations (`assert_called_once_with`).
  3. **Speed**: In-memory dictionaries run in microseconds with zero network or filesystem locks.
  4. Reserve `unittest.mock.patch` exclusively for external network boundaries (e.g. third-party HTTP endpoints) or system clocks.

---

## 🎁 3. Boundary Contract Decorators

Use decorators at the edges (services, CLI, API) to guarantee validated inputs, sanitized outputs, and execution safety:

### Example: Pydantic's `@validate_call`

```python
from pydantic import validate_call, Field
from core.models import Document


@validate_call
def ingest_record(
    title: str = Field(min_length=3, max_length=120),
    tags: list[str] = Field(default_factory=list, max_length=10),
    confidence: float = Field(ge=0.0, le=1.0, default=1.0),
) -> Document:
    """Type and value enforced automatically at runtime."""
    ...
```

### Example: Custom Boundary Sanitizer & Guard Decorator

```python
"""Custom boundary decorator for sanitizing input strings and handling errors."""

import functools
from typing import Any, Callable, TypeVar
from core.errors import AppError, ValidationError

F = TypeVar("F", bound=Callable[..., Any])


def enforce_boundary_contract(func: F) -> F:
    """Decorator to sanitize string args and convert unhandled exceptions to AppError."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Sanitize whitespace on string arguments
        cleaned_kwargs = {
            k: (v.strip() if isinstance(v, str) else v)
            for k, v in kwargs.items()
        }
        try:
            return func(*args, **cleaned_kwargs)
        except AppError:
            # Re-raise known domain errors directly
            raise
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                message=f"Invalid parameter passed to {func.__name__}: {exc}",
                context={"function": func.__name__},
            ) from exc

    return wrapper  # type: ignore[return-value]
```

---

## 🧰 4. Application Context Container (`core/context.py`)

Pass initialized adapters and settings through a single context object rather than global singletons:

```python
"""Unified application execution context."""

from dataclasses import dataclass
from core.config import Settings
from core.protocols import DocumentStorage


@dataclass(frozen=True)
class AppContext:
    """Immutable runtime dependency bundle."""

    settings: Settings
    storage: DocumentStorage
```
