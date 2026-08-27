# Testing & Verification Conventions (`rules/testing.md`)

> **Enforcement**: Fast local test execution via `uv run pytest` before every commit.

---

## 🏗️ 1. Test Suite Structure
- **Mirrored Layout**: Test files strictly mirror the `src/` hierarchy:
  ```text
  src/my_package/transform.py  ──▶  tests/test_transform.py
  src/my_package/io/loader.py  ──▶  tests/io/test_loader.py
  ```
- **Shared Fixtures**: Place shared test fixtures, sample datasets, and mock factories in `tests/conftest.py`.
- **Granularity**: One test function per individual behavior/scenario, avoiding bloated monolithic test functions.

---

## 🏷️ 2. Naming Conventions
- **Test Files**: `test_<module_name>.py`.
- **Test Functions**: `test_<function_or_class>_<expected_behavior>_<condition>()`
  - *Example*: `test_parse_contract_raises_error_when_column_missing()`
  - *Example*: `test_compute_sharpe_ratio_returns_zero_on_constant_returns()`

---

## 🧪 3. Fixtures & Test Data Hygiene
- **Filesystem Isolation**: Always use pytest's built-in `tmp_path` fixture for reading/writing temporary files during tests.
- **External Mocking**: Mock all network calls, external APIs, and remote database connections. Tests must never fail due to network outages or external credentials.
- **Synthetic Micro-Fixtures**: Prefer small, deterministic in-memory datasets (e.g. 5–10 rows) over multi-megabyte binary dumps in the test suite.

---

## ⏱️ 4. When to Write Tests

Match testing timing to code maturity:

1. **Deterministic Contracts & Business Logic** (Parsers, transformers, metrics, validators):
   - Write test cases **BEFORE or alongside** implementation during `/planning`.
   - Clear input $\to$ expected output pairs ensure unambiguous verification.
2. **Exploratory Notebooks & POCs**:
   - Focus on discovery first. Add automated unit tests once the pipeline logic stabilizes and is extracted into `src/`.

---

## 🚀 5. Execution Commands

```bash
uv run pytest                                # Run full test suite
uv run pytest tests/test_transform.py        # Run single test file
uv run pytest -k "test_parse_contract"       # Run tests matching expression
uv run pytest -v --tb=short                  # Verbose mode with concise tracebacks
```

---

## 🛡️ 6. Pre-Commit Gate
- All tests must pass before committing: `uv run pytest`.
- A failing test blocks the commit. Fix the underlying bug or mark with `@pytest.mark.skip(reason="...")` with an explicit issue reference.
