# Tooling & Modern Infrastructure Matrix (`uv`, `ruff`, `pytest`)

> **Core Philosophy**: Modern Python tooling has coalesced around Rust-backed ultra-fast binaries. Use `uv` for package management and `ruff` for all linting and formatting.

---

## ⚡ 1. The Core Modern Toolchain

```
   ┌─────────────────────────────────────────────────────────────┐
   │                    THE MODERN TOOLCHAIN                     │
   ├──────────────────────────────┬──────────────────────────────┤
   │ Package Manager:             │ Linter & Formatter:          │
   │ uv (Astral)                  │ ruff (Astral)                │
   ├──────────────────────────────┼──────────────────────────────┤
   │ Test Framework:              │ Data Validation:             │
   │ pytest + pytest-cov          │ pydantic >= 2.0              │
   ├──────────────────────────────┼──────────────────────────────┤
   │ Structured Logging:          │ CLI Framework:               │
   │ loguru or structlog          │ typer or click               │
   └──────────────────────────────┴──────────────────────────────┘
```

---

## 🚀 2. `uv` Quick Reference

```bash
# Initialize a new project with modern structure
uv init --lib my_package
cd my_package

# Add core runtime dependencies
uv add pydantic pydantic-settings loguru tenacity typer

# Add development dependencies
uv add --dev ruff pytest pytest-cov mypy

# Run tests or CLI inside managed virtualenv
uv run pytest
uv run ruff check . --fix
uv run ruff format .
```

---

## ⚙️ 3. Production-Grade `pyproject.toml` Template

```toml
[project]
name = "my-awesome-package"
version = "0.1.0"
description = "Clean, production-grade Python application."
readme = "README.md"
requires-python = ">=3.11"
authors = [{ name = "Engineering Team", email = "dev@example.com" }]
dependencies = [
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "loguru>=0.7.2",
    "tenacity>=8.3.0",
    "typer>=0.12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[project.scripts]
my-cli = "my_package.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# ==========================================
# Ruff Linter & Formatter Configuration
# ==========================================
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
    "PTH", # flake8-use-pathlib
    "RUF", # ruff-specific rules
]
ignore = [
    "E501", # Line length handled by formatter
]

[tool.ruff.lint.isort]
known-first-party = ["my_package"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# ==========================================
# Pytest & Coverage Configuration
# ==========================================
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = "-ra -q --cov=my_package --cov-report=term-missing"

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```
