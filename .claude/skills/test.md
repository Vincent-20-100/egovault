---
name: test
description: Run the pytest test suite
---

# /test

Run the test suite:

```bash
cd C:\Users\Vincent\GitHub\Vincent-20-100\egovault
.venv/Scripts/python -m pytest tests/ -x -q
```

If arguments are provided (e.g., `/test tests/tools/`), pass them to pytest:

```bash
.venv/Scripts/python -m pytest <args> -x -q
```

Report: X passed, Y failed, Z errors.
