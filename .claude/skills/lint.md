---
name: lint
description: Run ruff check + format on the codebase
---

# /lint

Run linting and formatting:

```bash
cd C:\Users\Vincent\GitHub\Vincent-20-100\egovault
.venv/Scripts/python -m ruff check --fix .
.venv/Scripts/python -m ruff format .
```

Report: number of files changed, errors fixed, or "All clean."
