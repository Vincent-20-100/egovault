# AGENTS.md — EgoVault (Personal Knowledge Compiler & Cognitive Memory Engine)

> Universal working contract and high-level guardrails automatically read by AI coding agents (Antigravity, Claude Code, Cursor, Codex, etc.) at session start.

---

## 🎯 1. Project Context & Intent

EgoVault is a **personal knowledge compiler and cognitive memory engine** designed around human neuroscience principles (memory consolidation, spreading activation, working memory constraints):

```
Tier 1: Hippocampal Chunks        → Raw, chronological, verbatim evidence in SQLite + chunks_vec
Tier 2: Neocortical Notes         → Distilled conceptual nuclei in Obsidian Markdown + notes_vec
Tier 3: Prefrontal Working Memory → Curated high-density context (4-7 slots) via curate() / query_vault()
```

- **Core Vision:** `docs/VISION-KNOWLEDGE-COMPILER.md` & `docs/VISION.md`
- **Core Motto:** *RAG retrieves then forgets. EgoVault consolidates, densifies, and connects.*

---

## 🏛️ 2. Hard Architecture Rules (Non-Negotiable)

```
core/           ← schemas, errors, config, context (VaultContext), uid, logging, security, sanitize (imports NOTHING from project)
tools/          ← atomic functions — receive VaultContext, import core/ only
workflows/      ← orchestrate tools/ — import tools/ + core/
infrastructure/ ← concrete SQLite, vector, and model providers — import core/ only
api/            ← thin routing layer — builds VaultContext, calls tools/ & workflows/
mcp/            ← thin routing layer — exposes tools/ via Model Context Protocol (FastMCP)
cli/            ← thin terminal UI — delegates to tools/ & workflows/
config/         ← 3-tier configuration: system.yaml, user.yaml, install.yaml
```

1. **G1 — Public Strings Describe WHAT, Not HOW:** Never leak library names (`faster-whisper`, `sqlite-vec`, `pypdf`) in docstrings, error messages, or CLI help.
2. **G3 — Zero-Hardcode Policy:** Every parameter, model name, threshold, timeout, and buffer size comes from `ctx.settings` (`system.yaml`, `user.yaml`, `install.yaml`). **Zero magic numbers in code.**
3. **G4 — Hexagonal Context Isolation:** Tools never import `infrastructure/` directly. They receive all dependencies through [`VaultContext`](core/context.py).
4. **G6 — Error Architecture V2:** Every exception inherits from `EgoVaultError` and supplies `error_code`, `user_message`, `actionable_hint`, and `http_status`.
5. **G7 — Language Boundary:** All code, SQL, docstrings, comments, config keys, and specs are in **English**. Vault notes and slugs default to French (configurable via `user.yaml`).
6. **G9 — Pydantic at Boundaries:** All data entering or exiting tools, API, and MCP must be typed Pydantic models in `core/schemas.py`.

---

## 🧠 3. The 1 Source → N Notes Segmentation Principle

- Chunks are **mechanical cuts** (text position); notes are **semantic cuts** (one nucleus of meaning = one vector).
- `embed_note()` produces **one vector per note** (title + docstring + body concatenated).
- A multi-topic source **MUST NEVER** be reduced to 1 bloated note (which destroys retrieval recall via semantic averaging). It must be segmented into $N$ cohesive candidates via deterministic cosine TextTiling (`note_candidates`).

---

## 🧭 4. Core Behavioral Reflexes

1. **Think Before Acting**: Understand requirements, check existing tools and schemas before writing new code.
2. **Execution Loop & Quality Gates**:
   - `Understand` (`/spec`) $\implies$ Propose architecture, check existing schemas and contracts.
   - `Plan` (`/plan`) $\implies$ Ordered task decomposition, sequence steps, rate confidence.
   - `Test-First (TDD)` $\implies$ Write unit & integration tests; verify with `uv run pytest`.
   - `Implement` $\implies$ Build minimal, clean code (strict typing, fail-fast with `errors.py`, zero hardcoding).
   - `Review` (`/review`) $\implies$ Inspect diff against acceptance criteria and regression guards.
   - `Commit` $\implies$ Conventional commit (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
3. **Living Documentation**: Keep `docs/` and `.agents/` synchronized in the same commit that modifies behavior.
4. **Honesty Constraint**: Never claim a test passed without running `uv run pytest` and inspecting output.

---

## ⚡ 5. Token Economy & Context Shield (Guidelines & Warnings)

To maintain high reasoning precision and avoid unnecessary token inflation:

1. **Airgap Heavy Ingestion (No Raw Web/Doc Dumps)**:
   - **NEVER fetch multi-page web docs, large raw media dumps, or massive transcripts directly into the main conversation.**
   - Delegate web scraping, external API exploration, or bulk data schema analysis to the **`research_worker` subagent** running on a fast/cheap model (`flash` / `mini`).
   - The subagent processes the large payload in its isolated sandbox and returns **ONLY a 10-line high-density distillation**.
2. **The "Ponytail" Principle (Senior Minimalism)**:
   - *"The best code is the code you never wrote."*
   - Avoid bespoke 100-line wheels when existing tools in `tools/` or standard library suffice.
3. **The "Caveman" Communication Standard**:
   - Zero polite fluff or conversational filler ("Certainly! I'd be delighted to...").
   - Maximum signal-to-token ratio: concise explanations, exact commands, surgical code diffs.
4. **Subagent Delegation Heuristic**:
   - *$\le 1$ file / localized tweak*: Execute inline immediately.
   - *Multi-file build / large refactoring / test suites*: Delegate to **`data_dev_worker`**.
   - *Multi-page research / web search / schema parsing*: Delegate to **`research_worker`**.

---

## 🧰 6. Available Skills & Subagents

### Isolated Subagents (`.agents/agents/`)
- `data_dev_worker` — Autonomous code & test execution worker in an isolated sandbox.
- `research_worker` — Fast web/doc ingestion worker that returns clean 10-line distillations without context pollution.

### Workflow & Meta-Skills (`.agents/skills/`)
- `specification-expert` (`/spec`) — Reason through fuzzy goals, evaluate architectural alternatives, and write structured specs.
- `planning-expert` (`/plan`) — Decompose work into concrete, ordered tasks with explicit verification steps.
- `review-expert` (`/review`) — Adversarial diff inspection, quality gates, and regression prevention.

### Domain & Engineering Skills (`.agents/skills/`)
- `python-coding-expert` — Hexagonal patterns, centralized `errors.py`, strict modern typing, zero-hardcode configuration.
- `data-engineering-expert` — SQLite schema, vector storage, ingestion pipeline, idempotency, data contracts.
- `eda-dataviz-expert` — Visual clarity, metric distribution, clean dashboards.
- `applied-ml-expert` — Embeddings, ranking formulas, cosine segmentation, ANN benchmarks.
- `quant-stats-expert` — Lookahead prevention, time series integrity.

### Shared Engineering Rules (`.agents/rules/`)
- `engineering_precedence.md` — Priority chain: Project conventions > User directives > Advisory standards.
- `code_style.md` — Typing, functional style, naming, logging, error architecture.
- `memory.md` — Living documentation — rewrite over append, avoid stale context.
- `secrets.md` — What never gets committed — API keys, `.env`, credentials, vault personal data.
- `autonomy.md` — Autonomous execution policy & security boundaries.
- `skill_maintenance_protocol.md` — Rules for maintaining and updating skills.
- `testing.md` — Mirrored layout, test-first, mocked externals, `pytest` gate.

---

## 📁 7. Project Layout & Tooling

```text
egovault/
├── api/                       # FastAPI REST backend & SSE endpoints
├── cli/                       # Typer CLI commands (ingest, curate, notes, sources)
├── core/                      # Domain kernel (context, schemas, errors, config, security)
├── infrastructure/            # Storage implementations (SQLite, sqlite-vec, embeddings, LLM)
├── mcp/                       # FastMCP server exposing tools over MCP
├── tools/                     # Atomic business tools (vault, text, media, export, web)
├── workflows/                 # Ingestion & curation orchestration flows
├── tests/                     # 540+ automated unit & integration tests
├── config/                    # 3-tier YAML configuration (system, user, install)
├── docs/                      # Technical & product documentation (user guide, architecture, vision)
├── .agents/                   # Living memory, governance, skills, and tools
│   ├── PROJECT-STATUS.md      # Strategic milestones & system state
│   ├── SESSION-CONTEXT.md     # Living session context
│   ├── GUIDELINES.md          # Working practices & guidelines
│   ├── WORKFLOW.md            # Engineering lifecycle specification
│   ├── decisions/             # ADRs
│   ├── archive/               # Historical plans, specs, audit records
│   ├── rules/                 # 7 engineering rules
│   ├── agents/                # data_dev_worker, research_worker
│   ├── skills/                # 8 specialized expert skills
│   ├── scripts/               # security_gate.py, auto_format.py
│   └── hooks.json             # Quality gate hook configuration
├── lefthook.yml               # Fast local pre-commit git hooks
├── pyproject.toml             # uv project dependencies & configuration
├── uv.lock                    # Dependency lockfile
├── README.md                  # Project overview & quickstart
└── AGENTS.md                  # This working contract
```

### Essential Commands

```bash
# Install and synchronize dependencies
uv sync

# Run the full test suite
uv run pytest

# Run linting checks
uv run ruff check

# Run code formatting
uv run ruff format
```
