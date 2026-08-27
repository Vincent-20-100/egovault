# Engineering Depth Decision Tree (Anti-Overengineering vs Anti-Vibecoding)

> **Core Philosophy**: Match architecture complexity to the actual problem scope, team size, and software lifetime. Never build a cathedral for a 50-line file conversion, and never write a single spaghetti script for a multi-tenant production engine.

---

## 🧭 The Decision Matrix

```
                    ┌──────────────────────────────────────────────┐
                    │ What is the estimated lifecycle & complexity │
                    │           of this Python software?           │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│   TIER 1 (NANO)  │             │  TIER 2 (MODULAR)│             │  TIER 3 (SYSTEM) │
│  Scripts / POC   │             │   CLI & Packages │             │ Services & Cores │
│   (<100 lines)   │             │ (100–1000 lines) │             │  (>1000 lines)   │
└────────┬─────────┘             └────────┬─────────┘             └────────┬─────────┘
         │                                │                                │
         ▼                                ▼                                ▼
• 1 `.py` file only              • `src/pkg/` layout              • Hexagonal / Clean
• Standard lib or `uv run`       • `core/` (errors, config)       • Strict `core/` isolation
• Simple `@dataclass` or inline  • `services/` (domain logic)     • `ports/` (`Protocol` ABC)
  `tomllib` config               • `cli.py` or `api.py`           • `adapters/` (infra/I/O)
• Basic `logging` (INFO/DEBUG)   • `config.toml` + Pydantic       • `pydantic-settings` + TOML
• Simple docstrings + types      • `pytest` test suite            • Structured JSON logs + spans
                                 • Google docstrings              • Comprehensive test pyramid
```

---

## 📊 Detailed Comparison by Dimension

| Dimension | Tier 1: Micro Script / POC | Tier 2: Modular Tool / CLI | Tier 3: Production System |
| :--- | :--- | :--- | :--- |
| **Typical Target** | Ad-hoc data transform, one-off automation, quick benchmark | Reusable developer tool, internal CLI, standalone Python library | Multi-team backend, microservice, long-lived core engine |
| **File Structure** | `script.py` | `src/pkg/{core, services, cli.py}` | `src/pkg/{core, ports, adapters, services, api}` |
| **Configuration** | Inline constant dict or simple `config.toml` with `tomllib` | External `config.toml` validated with Pydantic `BaseModel` | Multi-tier config (`system.yaml` + `user.toml` + Env overrides) via `pydantic-settings` |
| **Error Handling** | Dedicated exit codes + try/except with readable stderr | `errors.py` base `AppError` + domain exceptions + codes | Rich exception hierarchy (`DomainError`, `InfraError`, `ContractError`) + HTTP/gRPC mappings |
| **Logging** | `logging.basicConfig(level=logging.INFO)` | Leveled logging with contextual attributes | Structured JSON (`loguru` / `structlog`) + correlation IDs + rotation |
| **Testing** | 1-2 smoke tests or doctests | Unit tests (`tests/test_*.py`) with pytest fixtures | Unit, integration, property-based tests + mocks on ports |
| **Typing** | Essential signatures typed | 100% public APIs typed + `mypy`/`pyright` | 100% strict typing, generics, `TypeVar`, `Self`, `Protocol` |

---

## 🚫 The Anti-Pattern Traps

### Trap A: The "Vibe-Coding Slop" (Under-engineering)
* **Symptoms**:
  - Magic numbers scattered in the middle of functions (`if score > 0.73:`).
  - A 250-line `main()` function doing HTTP calls, data parsing, database insertion, and string formatting all in one loop.
  - Using `print()` as the sole debugging and output mechanism.
  - Catching `except Exception as e:` and doing nothing or printing `f"Error: {e}"`.
  - Storing state in module-level global variables.
* **Remedy**: Upgrade immediately to **Tier 2**. Extract config into `config.toml`, split into single-responsibility functions/classes, use `errors.py` and `logging`.

### Trap B: The "Abstract Astronaut" (Overengineering)
* **Symptoms**:
  - Creating `AbstractFileStrategyFactoryProviderInterface` for a 40-line CSV parser.
  - Adding 5 layers of indirection and dependency injection containers for a script that will run once.
  - Writing 500 lines of boilerplate for a 20-line utility.
* **Remedy**: Downgrade to **Tier 1** or **Tier 2**. If there is only one concrete implementation and no foreseeable polymorphism, a simple class or function with typed parameters is vastly superior to an elaborate design pattern.

---

## 🎯 The "Rule of Three" for Abstractions

1. **First time**: Write it simply and directly.
2. **Second time**: Duplicate or lightly adapt without over-abstracting.
3. **Third time**: Now and only now extract a reusable `Protocol`, base class, or generic service.

---

## 🧪 Tier 0 — Solo Exploratory / Disposable (Context Override)

Tier 0 is not a size bracket — it's a **context override** that can apply even to a 300-line file, whenever the code is written by a single person, meant to be run a handful of times, and has no expected life beyond the current session or sprint (a throwaway migration, a one-off notebook cell, a pitch prototype, an exploratory data dig).

* **Structure**: Single file or notebook cell, no package layout.
* **Config**: Inline constants are fine — no `config.toml` ceremony for values used once.
* **Errors**: Let it crash with a readable traceback. No `errors.py` hierarchy.
* **Tests**: None, or a single `assert` at the bottom if the logic has a branch worth trusting later.
* **Upgrade trigger**: The moment the script gets a second real invocation, a second maintainer, or outlives the sprint it was written for — promote it to Tier 1 or 2 on the spot, don't retrofit later.

Tier 0 does not excuse silent failures, hardcoded secrets, or destructive operations without confirmation — those rules never relax.

---

## 🚦 When NOT to Reach for Tier 3 (Counter-Cases)

Line count alone does not justify Hexagonal/Clean architecture. Stay at Tier 2 even past 1000 lines when:

* **You are the only maintainer** and expect to stay that way — the abstraction pays for itself only when someone else has to onboard onto the boundaries.
* **The software's real lifespan is short** (a migration, a one-time backfill, a conference demo) regardless of how large it grew while being written.
* **There is exactly one concrete implementation** of every port you'd define — a `Protocol` with a single implementer is a promise of future flexibility you may never redeem (see Rule of Three above).
* **Speed to a working demo is the actual success metric**, not maintainability — ship the modular version, note the debt, don't pay it upfront.

Tier 3 earns its cost when a second team, a second deployment target, or a second data source is a near-certainty — not a hypothetical.

---

## 📣 Declare Your Tier Before Writing Code

Before producing any non-trivial implementation, state the choice in one line so it's visible and correctable by the user rather than silently baked in:

```text
Tier chosen: T{0|1|2|3} — because: {one clause justifying it against the axes above}
```

If the user disagrees with the tier, that's a signal to renegotiate scope, not to silently comply — surface the trade-off.
