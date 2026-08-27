# Python Standards, PEP 8 & Pythonic Idioms

> **Core Philosophy**: Writing Pythonic code means respecting the conventions of the global Python community. PEP 8 is the universal visual syntax, PEP 257 governs docstring behavior, and PEP 20 (The Zen of Python) defines the mindset.

---

## 📜 1. The Core PEP Matrix

```
   ┌─────────────────────────────────────────────────────────────┐
   │                     THE CORE PEP SUITE                      │
   ├──────────────────────────────┬──────────────────────────────┤
   │ PEP 8: Style Guide           │ PEP 257: Docstrings          │
   │ Naming, Layout, Imports      │ Structure, Imperative Mood   │
   ├──────────────────────────────┼──────────────────────────────┤
   │ PEP 20: Zen of Python        │ PEP 585 & 604: Modern Types  │
   │ Architectural Philosophy     │ Generics & Union Syntax      │
   ├──────────────────────────────┼──────────────────────────────┤
   │ PEP 621: pyproject.toml      │ PEP 557: Data Classes        │
   │ Standard Project Metadata    │ Clean Typed Data Containers  │
   └──────────────────────────────┴──────────────────────────────┘
```

---

## 🏷️ 2. PEP 8 Naming Conventions (Strict Standard)

| Target | Convention | Example | Banned Anti-Pattern |
| :--- | :--- | :--- | :--- |
| **Modules / Packages** | `lowercase_with_underscores` | `market_data.py`, `core/` | `MarketData.py`, `marketData.py` |
| **Classes / Exceptions** | `PascalCase` / `CapWords` | `VolatilitySurface`, `AppError` | `volatility_surface`, `volatilitySurface` |
| **Functions / Methods** | `snake_case` | `calculate_spot_price()` | `calculateSpotPrice()`, `CalculateSpot` |
| **Global / Module Constants** | `SCREAMING_SNAKE_CASE` | `DEFAULT_TIMEOUT_SECONDS = 30` | `defaultTimeout = 30`, `timeout = 30` |
| **Internal / Private Symbols** | `_leading_underscore` | `_compute_parity_residual()` | `compute_parity_residual_private()` |
| **Avoid Name Collisions** | `trailing_underscore_` | `class_`, `id_`, `type_` | `klass`, `my_type` |

---

## 📦 3. PEP 8 Import Ordering (Enforced by `ruff` / `isort`)

Imports must strictly occur at the top of the file and be grouped into **3 distinct blocks** separated by a single blank line:

```python
# 1. Standard Library Imports
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Sequence

# 2. Related Third-Party Imports
import httpx
from loguru import logger
from pydantic import BaseModel, Field

# 3. Local Application / Library Specific Imports
from core.errors import ValidationError
from core.models import PriceSnapshot
```

---

## 🐍 4. Pythonic Idioms vs Anti-Patterns (PEP 8 & PEP 20)

### A. Equality & Identity Comparisons
```python
# ✅ Pythonic
if val is None: ...
if val is not None: ...
if not items: ...  # Empty sequence/mapping check

# ❌ Anti-Pattern
if val == None: ...
if val != None: ...
if len(items) == 0: ...
if is_valid == True: ...  # NEVER compare booleans with == True
```

### B. Type Checking
```python
# ✅ Pythonic: Respects inheritance and polymorphism
if isinstance(obj, DocumentStorage): ...

# ❌ Anti-Pattern: Fragile, breaks on subclasses
if type(obj) is DocumentStorage: ...
```

### C. Resource Management (Context Managers)
```python
# ✅ Pythonic: Guarantees file closure even on exception
with open("data.csv", "r", encoding="utf-8") as f:
    content = f.read()

# ❌ Anti-Pattern: Leak hazard on crash
f = open("data.csv")
content = f.read()
f.close()
```

### D. Dictionary Access & Fallbacks
```python
# ✅ Pythonic: EAFP (Easier to Ask for Forgiveness than Permission) or .get()
val = mapping.get("key", default_value)

# ❌ Anti-Pattern
if "key" in mapping:
    val = mapping["key"]
else:
    val = default_value
```

---

## ✍️ 5. PEP 257 — Docstring Conventions (The Imperative Mood)

* **Command Rule**: Always write the summary line in the **imperative mood** (*"Do this"*, *"Return that"*), never in the descriptive third person (*"Returns that"*, *"Calculates..."*).

```python
# ✅ Correct (PEP 257 Imperative Mood):
def calculate_forward(spot: float, carry: float, maturity: float) -> float:
    """Compute the theoretical forward price from spot and cost of carry.
    
    Args:
        spot: Current underlying reference spot price.
        carry: Annualized cost of carry rate.
        maturity: Time to expiration in year fractions.
        
    Returns:
        Theoretical forward price as a positive float.
    """
    ...

# ❌ Incorrect (Descriptive mood / lazy):
def calculate_forward(spot: float, carry: float, maturity: float) -> float:
    """Calculates forward price."""
    ...
```

---

## 🧘 6. The Zen of Python (PEP 20 in Practice)

1. **Explicit is better than implicit**: Type annotations on every signature, explicit configuration arguments, no hidden magic kwargs.
2. **Simple is better than complex**: Don't build 5-layer design patterns when a simple function suffices.
3. **Flat is better than nested**: Guard clauses (`if not condition: return`) over deep 5-level `if/else` pyramids.
4. **Errors should never pass silently**: Custom `AppError` exceptions with reason codes; never empty `except: pass`.
5. **There should be one—and preferably only one—obvious way to do it**: Standardize on `uv` + `ruff` + `pydantic`.

---

## ⚡ 7. Modern Concurrency & AsyncIO (Python 3.11+)

### A. Structured Concurrency via `asyncio.TaskGroup`
Never use unshielded `asyncio.gather()` for complex task fan-out in modern Python (unhandled task cancellations leak background work). Prefer `asyncio.TaskGroup` with `ExceptionGroup` handling:

```python
import asyncio
from core.errors import InfrastructureError


async def fetch_all_sources(source_ids: list[str]) -> list[dict]:
    """Fetch multiple resources concurrently with structured error isolation."""
    results: list[dict] = []
    
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(fetch_single_source(sid))
                for sid in source_ids
            ]
        # All tasks completed successfully
        results = [t.result() for t in tasks]
    except* InfrastructureError as eg:
        # PEP 654: Handle exception groups from concurrent failures cleanly
        logger.error("Failed to fetch one or more sources: {errors}", errors=eg.exceptions)
        raise

    return results
```

### B. Non-Blocking Event Loop Invariant
Never execute blocking synchronous I/O (`time.sleep()`, `requests.get()`, synchronous SQLite) or CPU-bound loops (>10ms) inside an `async def` function. Always delegate to worker threads:

```python
import asyncio


async def run_cpu_bound_analysis(data: list[float]) -> float:
    """Offload blocking computations without stalling the async event loop."""
    return await asyncio.to_thread(heavy_math_kernel, data)
```

### C. Async Context Propagation (`contextvars`)
Use `contextvars.ContextVar` to propagate request/trace context safely across async tasks and coroutines:

```python
import contextvars

correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
```

