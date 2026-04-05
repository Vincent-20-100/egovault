# Contributing to EgoVault

Thank you for your interest in contributing to EgoVault!

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [Ollama](https://ollama.ai/) running locally with `nomic-embed-text` model pulled
- SQLite 3.40+ (ships with Python)

## Development Setup

```bash
# Clone and install dependencies
git clone https://github.com/Vincent-20-100/egovault.git
cd egovault
uv sync

# Initialize user data directory
.venv/Scripts/python scripts/setup/init_user_dir.py

# Run tests
.venv/Scripts/python -m pytest tests/
```

## Code Conventions

- **Code, SQL, comments, config keys:** English
- **Vault content (notes, tags, slugs):** French (configurable via `user.yaml`)
- **Architecture:** `core/` (interfaces), `tools/` (atomic functions), `workflows/` (orchestration), `infrastructure/` (implementations)
- A tool **never imports** another tool
- See `docs/architecture/ARCHITECTURE.md` for the full reference

## Commit Messages

Format: `prefix: description in English`

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Maintenance, refactoring, CI |
| `test:` | Test-only changes |

## Pull Request Process

1. Fork the repo and create a branch from `main`
2. Add tests for any new functionality
3. Ensure all tests pass: `.venv/Scripts/python -m pytest tests/`
4. Update `docs/architecture/ARCHITECTURE.md` if you changed behavior, schema, or contracts
5. Open a PR with a clear description of what and why

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities. **Do not open public issues for security bugs.**
