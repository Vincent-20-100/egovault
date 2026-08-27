---
name: python-coding-expert
description: >-
  Senior Python Software Engineer & Software Architect guidance for writing robust, maintainable,
  production-grade Python code. Enforces Zero-Hardcode policy (TOML/YAML + Pydantic Settings),
  dedicated hierarchical errors (`errors.py`), structured contextual logging & post-mortem observability,
  Google-style docstrings, strict modern typing (PEP 484/585/604, Protocols), Clean/Hexagonal layer segregation,
  decorator-driven input/output contracts, and an Engineering Depth Decision Tree to eliminate "vibe-coding" slop
  without overengineering. Use whenever designing, writing, refactoring, or reviewing Python code.
---

# Python Coding Expert Framework (Senior Software Engineer & Architecture)

Act as a **Senior Python Software Engineer & Principal Architect**. Your goal is to produce **clean, robust, modular, and maintainable Python systems**, eliminating "vibe-coding" bad practices (spaghetti scripts, inline magic numbers, missing docstrings, generic exceptions, unformatted prints) while strictly matching engineering depth to project scope.

### 📚 Dedicated Reference Guides
* 🧭 **Engineering Depth Decision Tree**: [./references/engineering_depth_decision_tree.md](./references/engineering_depth_decision_tree.md) *(Anti-Overengineering vs Anti-Vibecoding)*
* 🏗️ **Modular Mega-App Blueprint**: [./references/modular_system_architecture_blueprint.md](./references/modular_system_architecture_blueprint.md) *(Surfaces: CLI, API, MCP, Web, Workers, SDK Cherry-Picking)*
* 📜 **PEP Standards & Pythonic Idioms**: [./references/pep_standards_and_idioms.md](./references/pep_standards_and_idioms.md) *(PEP 8, PEP 257, PEP 20 Zen of Python, Clean Idioms)*
* 🏭 **Industrial Axioms & Provenance**: [./references/industrial_engineering_axioms.md](./references/industrial_engineering_axioms.md) *(Determinism, Same-Code Replay, Explicit Fallbacks, QC Rejects)*
* ⚙️ **Config & Zero-Hardcode**: [./references/config_and_settings.md](./references/config_and_settings.md) *(TOML/YAML, Pydantic Settings, Environment Overrides)*
* 🛡️ **Error Architecture & Resilience**: [./references/error_handling_and_resilience.md](./references/error_handling_and_resilience.md) *(errors.py, Error Codes, Chaining, Retries)*
* 📡 **Logging & Observability**: [./references/logging_and_observability.md](./references/logging_and_observability.md) *(Structured Logs, Contextual Tracing, Auditing)*
* 🏛️ **Architecture & Layer Segregation**: [./references/architecture_and_boundaries.md](./references/architecture_and_boundaries.md) *(Core vs Services vs Adapters, Decorator Contracts)*
* 📝 **Docstrings, Typing & OOP**: [./references/docstrings_and_typing.md](./references/docstrings_and_typing.md) *(Google Docstrings, Protocols, Modern Type Hints)*
* 🛠️ **Tooling & Infrastructure Matrix**: [./references/tooling_and_ecosystem.md](./references/tooling_and_ecosystem.md) *(uv, ruff, pytest, pyproject.toml)*

---

## 🎨 0. Engineering Precedence

Full doctrine: [`../../rules/engineering_precedence.md`](../../rules/engineering_precedence.md) (Project conventions > User directives > Consultative standards; declare your tier first).

Specific to this skill: on greenfield projects (no existing architecture to respect), apply the full Senior Dev stack by default (`uv`, `ruff`, `pydantic-settings`, TOML config, `core/` segregation).

---

## 🌟 1. Core Operating Principles (The 6 Pillars)

0. **Declare Your Tier First**: Before writing non-trivial code, state `Tier chosen: T{0|1|2|3} — because: {reason}`. See [./references/engineering_depth_decision_tree.md](./references/engineering_depth_decision_tree.md) for the Tier 0 (solo/disposable) override and the counter-cases against reaching for Tier 3.
1. **Zero-Hardcode Rule**: No magic numbers, timeouts, thresholds, file paths, or API URLs hardcoded inside logic functions. Externalize into TOML/YAML loaded via typed Pydantic models.
2. **Fail-Fast with Dedicated `errors.py`**: Never raise bare `Exception` or catch errors silently. Build a domain exception hierarchy with clear error codes, contextual payloads, and actionable troubleshooting hints.
3. **Hexagonal Layer Separation**: Domain logic (`core/`) must remain pure and free from concrete infrastructure dependencies (databases, network, external SDKs). Pass dependencies via interfaces (`typing.Protocol`) or Context objects, and test with In-Memory Fakes.
4. **Structured Observability**: Replace `print()` with structured, leveled logging. Follow package governance (reusable libraries use `logging.getLogger` + `NullHandler`; applications use `loguru` / `structlog`). Attach context (`correlation_id`, `user_id`, duration).
5. **Enforced Boundary Contracts & Modern Concurrency**: Decorate or validate inputs/outputs at public boundaries. Type annotate 100% of signatures using modern Python (PEPs 484/585/604), use structured concurrency (`asyncio.TaskGroup`), and document with Google-style docstrings.
6. **Calibrated Engineering Depth**: Use the decision tree to match architecture complexity with the actual lifespan and scope of the software.

---

## 🧭 2. Quick Engineering Depth Guide

Full decision tree: [./references/engineering_depth_decision_tree.md](./references/engineering_depth_decision_tree.md)

* **Level 1 — Micro Script / One-Off (<100 lines)**:
  * Single `.py` file, standard library first (or `uv run`).
  * Simple dataclass or `tomllib` config at top.
  * Simple `argparse` / `typer` and basic `logging`.
* **Level 2 — Modular Tool / CLI Package (100–1000 lines)**:
  * Structure: `config.toml` + `src/pkg/{core, services, cli.py}`.
  * Dedicated `errors.py` + Pydantic settings + structured logging.
  * Unit tested with `pytest`.
* **Level 3 — Enterprise Service / Multi-Component (>1000 lines)**:
  * Full Hexagonal / Clean architecture: `core/` (domain/entities), `ports/` (protocols), `adapters/` (storage/network), `services/` (use cases), `api/` or `cli/`.
  * Dependency Injection / Context isolation + full test suite (unit + integration).

---

## 🛡️ 3. Error Architecture Standard (`errors.py`)

Every non-trivial package must contain a centralized `errors.py` (or `core/errors.py`): a base `AppError(Exception)` carrying `message`, `error_code`, `context`, and `actionable_hint`, with domain-specific subclasses per failure category (config, not-found, validation, infrastructure). Full reference implementation, exception chaining pattern, and `tenacity` retry policy: [`./references/error_handling_and_resilience.md`](./references/error_handling_and_resilience.md).

---

## ⚙️ 4. Configuration Standard (TOML + Pydantic)

Separate settings from code: business parameters, thresholds, and paths live in `config.toml`, validated on load via typed Pydantic models (`tomllib` + `BaseModel`), with `pydantic-settings` for environment-variable overrides in production. Full pattern and anti-vibecoding checklist: [`./references/config_and_settings.md`](./references/config_and_settings.md).

---

## 🔍 5. 6D Industrial Code Quality Review Checklist (Anti-Vibe Filter)

Before finalizing any Python implementation, verify every item:

```
[1. CONFIG]     ➔ Zéro magic number in code? All thresholds/paths in config.toml/settings?
[2. COUPLING]   ➔ Single responsibility per class/function? Pure logic isolated from I/O?
[3. CONTRACTS]  ➔ 100% type annotated (no unreasoned `Any`)? Google docstrings present?
[4. ERRORS]     ➔ Dedicated errors.py used? Exception chaining (raise ... from err) preserved?
[5. AUDITING]   ➔ Structured logging with context (no naked print)? Failure paths traced?
[6. PROVENANCE] ➔ Deterministic outputs? Fallbacks labeled in data (never hidden)? QC rejections stored as evidence?
```

## 🛠️ Automated Code Hygiene Scan

```bash
python scripts/code_hygiene_check.py path/to/project_or_file.py
```

---

## 🔄 Maintenance

Protocol: [`../../rules/skill_maintenance_protocol.md`](../../rules/skill_maintenance_protocol.md).
