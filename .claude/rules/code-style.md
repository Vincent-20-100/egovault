# Code Style Conventions

## Naming

- `snake_case` for functions, variables, modules
- `PascalCase` for classes and Pydantic models
- `UPPER_SNAKE` for module-level constants
- `kebab-case` for vault slugs and tags (French, no accents)

## Docstrings

- Module: role + why it exists (2-3 lines max)
- Class/function: one line "what", not "how"
- No docstrings on unchanged code — only add when you write or modify

## Comments

- Inline comments explain **why**, never narrate **what**
- A good name replaces a comment — rename before commenting
- No TODO comments without a linked issue or deferred item

## Imports

- Standard library → third-party → project (separated by blank lines)
- `core/` imports nothing from the project
- `tools/` imports only `core/`
- `infrastructure/` imports only `core/`
- Never cross-import between tools

## Error handling

- Catch specific exceptions, not bare `except Exception`
- Every `except` must log or re-raise — no silent swallowing
- Use project error types from `core/errors.py`
- Never expose internals in user-facing errors
