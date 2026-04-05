# Testing Conventions

## Structure

- Test files mirror source: `tools/vault/search.py` → `tests/tools/vault/test_search.py`
- One test file per module, prefixed `test_`
- Test functions: `test_<behavior_description>()`

## Fixtures

- Shared fixtures in `tests/conftest.py` (ctx, tmp_path, source/note factories)
- API fixtures in `tests/api/conftest.py` (client, seeded DB)
- Use `ctx` fixture for VaultContext — never build context manually in tests

## Running tests

```bash
python -m pytest tests/                    # all tests
python -m pytest tests/tools/vault/        # one module
python -m pytest tests/ -k "test_search"   # by name
python -m pytest tests/ -x                 # stop on first failure
```

## Principles

- Test **behavior**, not implementation details
- Mock at boundaries (DB, LLM, external APIs), not internal functions
- Background thread tests MUST mock `_submit_job` to avoid DB locks
- Use `patch.dict(sys.modules, ...)` for unavailable optional deps (e.g. pypdf)
- Every new tool or workflow must have a corresponding test file
