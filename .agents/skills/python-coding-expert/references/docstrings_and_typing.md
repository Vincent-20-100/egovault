# Docstrings, Modern Typing & OOP Standards

> **Core Philosophy**: Code is read 10x more often than it is written. Clear Google-style docstrings and strict static type hints turn code into a self-documenting, statically verifiable contract.

---

## 📝 1. Google-Style Docstring Standard

Every public module, class, and function must include complete Google-style docstrings:

```python
"""Module for cryptographic token hashing and verification.

This module provides high-performance hashing utilities backed by SHA-256
with configurable salt rounds.
"""

from typing import Sequence


class TokenHasher:
    """Computes and verifies salted cryptographic hashes for security tokens.

    Attributes:
        salt_rounds: Number of iterations used in key derivation.
        algorithm: Name of the hashing algorithm (e.g., 'sha256').
    """

    def __init__(self, salt_rounds: int = 12, algorithm: str = "sha256") -> None:
        """Initialize TokenHasher with security parameters.

        Args:
            salt_rounds: Integer between 4 and 31 defining work factor.
            algorithm: Supported hash algorithm name.

        Raises:
            ValueError: If salt_rounds is outside the allowed range.
        """
        if not 4 <= salt_rounds <= 31:
            raise ValueError(f"salt_rounds must be in [4, 31], got {salt_rounds}")
        self.salt_rounds = salt_rounds
        self.algorithm = algorithm

    def hash_batch(self, tokens: Sequence[str]) -> list[str]:
        """Hash a sequence of token strings.

        Args:
            tokens: Sequence of raw token strings to hash.

        Returns:
            List of hexadecimal digested strings in corresponding order.

        Raises:
            ValidationError: If any token is empty or whitespace-only.

        Example:
            >>> hasher = TokenHasher(salt_rounds=10)
            >>> hasher.hash_batch(["secret_token_1", "secret_token_2"])
            ['a1b2c3...', 'd4e5f6...']
        """
        ...
```

---

## 🎯 2. Modern Python 3.11+ Type System (PEPs 484, 585, 604, 673)

### Union Syntax (PEP 604)
```python
# Modern (Python 3.10+)
def find_user(name: str) -> User | None: ...
def process_data(val: int | float | str) -> bool: ...

# Legacy (Avoid)
from typing import Optional, Union
def find_user(name: str) -> Optional[User]: ...
```

### Native Generics (PEP 585) & Immutable Parameter Types
```python
from collections.abc import Sequence, Mapping, Iterable, Callable

# Good: Accept general/immutable collections in parameters, return concrete types
def compute_scores(records: Sequence[Record]) -> list[float]: ...
def parse_headers(raw: Mapping[str, str]) -> dict[str, str]: ...

# Bad: Forcing caller to pass mutable list when any sequence would work
def compute_scores(records: list[Record]) -> list[float]: ...
```

### Self Type (PEP 673) for Fluent Interfaces & Factories
```python
from typing import Self

class QueryBuilder:
    def __init__(self) -> None:
        self._filters: list[str] = []

    def where(self, condition: str) -> Self:
        self._filters.append(condition)
        return self

    @classmethod
    def from_string(cls, raw: str) -> Self:
        instance = cls()
        instance._filters.append(raw)
        return instance
```

---

## 🏗️ 3. OOP: Dataclasses vs Pydantic Models

| Use Case | Recommended Tool | Why |
| :--- | :--- | :--- |
| **Internal Domain Entities & Context** | `@dataclass(frozen=True, slots=True)` | Ultra-fast, lightweight, zero runtime dependency overhead, immutable. |
| **I/O Boundaries (API, TOML, User Input)** | Pydantic `BaseModel` | Automatic parsing, coercion, rich validation errors, schema export. |

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class UserSession:
    """Internal immutable session entity."""
    session_id: str
    user_id: str
    is_admin: bool = False
```

---

## 🚫 Typing Anti-Patterns to Ban

* ❌ **Lazy `Any`**: Using `data: Any` or `def process(x):` without types. If the type is genuinely dynamic, use `object` with `isinstance()` checks or a generic `TypeVar`.
* ❌ **Mutable Default Arguments**: `def append_item(item: str, target: list = []):` (Always use `target: list[str] | None = None`).
* ❌ **Missing Return Types**: Every function must annotate `-> None`, `-> int`, etc.
