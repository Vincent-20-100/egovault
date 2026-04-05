---
name: test
description: "Use when the user asks to run tests or verify the test suite."
allowed-tools: Bash(python:*), Bash(pytest:*), Bash(uv run pytest:*)
---

# Test

Run the project test suite with optional arguments.

```bash
python -m pytest tests/ $ARGUMENTS
```

Report: X passed, Y failed, Z errors. If failures, diagnose root cause.
