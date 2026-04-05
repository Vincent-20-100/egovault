---
name: lint
description: "Use when the user asks to lint, format, or clean up code style."
allowed-tools: Bash(ruff:*), Bash(uv run ruff:*)
---

# Lint

Run ruff check and format on the whole project.

```bash
ruff check . --fix && ruff format .
```

Report what changed (files modified, issues fixed).
