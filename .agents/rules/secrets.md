# Secrets & Sensitive Data Prevention (`rules/secrets.md`)

> **Enforcement**: Automated via pre-commit hooks, secret scanners, and strict developer & agent discipline.

---

## 🚫 1. What Must NEVER Be Committed

- **Credentials & API Keys**: Anthropic, OpenAI, AWS, HuggingFace, database connection passwords, bearer tokens, SSH keys.
- **Private Keys & Certificates**: `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*.pfx`.
- **Environment & Secrets Files**: `.env`, `.env.local`, `.env.*.local`.
- **Proprietary Data & PII**: Un-anonymized customer data, internal analytics dumps, personal identifiable information.
- **Local Databases with Real Data**: `*.sqlite`, `*.db`, `*.duckdb`, `*.parquet` containing production-grade or sensitive information.
- **Credential Storage Dumps**: `*.kdbx`, `*.1pif`, browser profile / cookie exports.

---

## 📁 2. Canonical File Conventions

1. **`.env` (Gitignored)**:
   - Resides in the project root and is strictly included in `.gitignore`.
2. **`.env.example` (Committed)**:
   - Contains only placeholder strings and documentation for required variables:
     ```bash
     OPENAI_API_KEY=sk-...-REPLACE-ME
     DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/DBNAME
     DATA_LAKE_PATH=/path/to/local/storage
     ```
3. **Data Directories**:
   - `data/raw/`, `data/interim/`, `data/processed/` should have their contents gitignored (e.g. `data/**` ignored, with only `.gitkeep` tracked) unless tracking small, synthetic, public test fixtures.

---

## 🔍 3. Pre-Commit Verification Reflex

Before staging or committing any file:
1. Run `git status` and inspect the list of untracked and staged files.
2. Read the staged diff (`git diff --staged`) to ensure no inline token, hardcoded password, or connection string slipped into source code.
3. If unsure whether a file contains proprietary or sensitive data, treat it as sensitive by default.

---

## 🚨 4. Immediate Remediation Protocol

If a secret is inadvertently committed:
1. **Rotate the Credential Immediately**: Revoke the compromised key from the provider dashboard and issue a fresh one. A committed secret in Git history is permanently compromised.
2. **Do Not Just "Delete" in a Follow-up Commit**: The secret remains in git history.
3. **History Scrubbing**: If the repository is local/private, use tools like `git-filter-repo` or BFG to scrub the commit history before pushing.
