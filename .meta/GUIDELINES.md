# EgoVault — Guidelines

> **The mentor.** Best practices drawn from real incidents. Apply naturally, suggest when relevant.
> These are hard constraints, not suggestions — but they live here to keep CLAUDE.md lean.

---

## Architecture rules (G1–G13)

### G1 — No implementation details in public-facing strings

Public-facing = MCP docstrings, API descriptions, error messages, CLI help, README, docs.
Describe **capabilities** (what), never **tools/libraries** (how).

| Wrong | Right |
|-------|-------|
| `"Transcribe using faster-whisper"` | `"Transcribe using the configured engine"` |
| `"Stored in sqlite-vec"` | `"Stored in the vector index"` |

### G2 — Describe WHAT, not HOW

Docstrings state purpose and behavior, not mechanism or parameter values.

| Wrong | Right |
|-------|-------|
| `"Splits text using a sliding window of 800 tokens"` | `"Splits text into overlapping chunks"` |
| `"Queries sqlite-vec with cosine similarity"` | `"Semantic search over the vault"` |

### G3 — Config-driven, not code-driven

Every tunable value comes from config (`system.yaml`, `user.yaml`, `install.yaml`). Never hardcode
algorithm parameters, provider names, model IDs, file paths, taxonomy values, or locale settings.

### G4 — Context-based dependency injection (VaultContext)

```
core/           ← schemas, interfaces, VaultContext — imports NOTHING from project
tools/          ← atomic functions — receive VaultContext, import core/ only
workflows/      ← orchestrate tools/ — import tools/ + core/
infrastructure/ ← concrete implementations — import core/ only
mcp/            ← thin routing — build VaultContext via infrastructure/, call tools/
api/            ← thin routing — build VaultContext via infrastructure/, call tools/ + workflows/
```

**Hard rules:**
- A tool **never imports** `infrastructure/` — it receives what it needs via `VaultContext`
- A tool **never imports another tool** — if needed, the tool boundary is wrong
- `core/` has **zero imports** from any other project package
- `mcp/server.py` and `api/` routers contain **zero business logic** — routing only
- New Pydantic models go in `core/schemas.py`

### G5 — No over-engineering

- No abstractions, helpers, or utilities for single-use operations
- No error handling for impossible scenarios
- No feature flags, backwards-compat shims, or re-exports
- No docstrings/comments/type annotations added to unchanged code
- No new files when editing existing ones would suffice
- 3 similar lines > 1 premature abstraction

### G6 — Error handling discipline

- **Every `except` block must log or re-raise.** No silent swallowing.
- **Catch specific exceptions** — `except ValueError`, not `except Exception` when the failure mode is known
- **Never expose internals in user-facing errors** — no stack traces, file paths, SQL, library names
- **Use project error types** from `core/errors.py`
- **Log levels:** `error` = needs attention, `warning` = recoverable, `debug` = tracing. Never `print()`.

### G7 — Language and naming discipline

- **Code, SQL, comments, config keys:** English. Always.
- **Vault content** (notes, tags, slugs): French by default (configurable).
- Use **exact glossary terms** from `ARCHITECTURE.md` §1.3 — `note` not `document`, `source` not `file`.
- Casing: `snake_case` Python, `kebab-case` vault slugs/tags.

### G8 — Test discipline

- Test files **mirror source structure**: `tools/vault/search.py` → `tests/tools/vault/test_search.py`
- Test **behavior**, not implementation
- Every new tool or workflow **must** have a corresponding test file
- Do not add tests for unchanged code (unless explicitly asked)

### G9 — Pydantic everywhere at boundaries

- Tool input/output crossing a boundary (MCP, API, config) **must** be a Pydantic model
- No raw dicts as public function signatures
- Validation at the **boundary** (MCP/API), not deep inside tools
- New models in `core/schemas.py`, naming: `*Input`, `*Result`, `*Filters`

### G10 — Security by default

- **Never log** user content, API keys, or file paths at INFO or above
- **Always validate file paths** against allowed directories before I/O
- **Parameterized SQL exclusively** — `?` placeholders for all values
- **No `eval()`, `exec()`, or dynamic import tricks**
- See `ARCHITECTURE.md` §10 for the full security model

### G11 — MCP/API are routing layers only

- **Zero business logic** — delegate everything to `tools/` or `workflows/`
- **Return** `model.model_dump(mode="json")` — never construct dicts manually
- **Function bodies** should be <15 lines (build context, call tool, return result)

### G12 — No duplicated documentation

- A fact exists in **one place only**. Config values → `system.yaml`. Architecture → `ARCHITECTURE.md`.
- On contradiction: **config/arch wins** — fix the docstring

### G13 — Code comments: concise, surgical, no dead weight

- **Module docstring:** role + why it exists (2-3 lines max)
- **Class/function docstring:** one line "what", not "how"
- **Inline comments:** only when the "why" isn't obvious. Never narrate the "what"
- **A good name replaces a comment.** If you need a comment to explain a variable, rename it first

---

## Pre-commit checklist

Before any change is considered complete:

- [ ] G1: No library names in public strings
- [ ] G2: Docstrings describe what, not how
- [ ] G3: No hardcoded values
- [ ] G4: Architecture boundaries respected
- [ ] G5: No unnecessary abstractions
- [ ] G6: Every except logs or re-raises
- [ ] G7: English code, French vault content
- [ ] G8: Tests mirror source structure
- [ ] G9: Pydantic at boundaries
- [ ] G10: No security anti-patterns
- [ ] G11: Routing layers are thin
- [ ] G12: No duplicated docs
- [ ] G13: Code is properly commented

---

## Conventions

### Python
- `core/` = interfaces + shared models — never called directly by a client
- `tools/` = atomic functions: typed input → typed output, no side-effects beyond ctx
- `workflows/` = ordered sequences of tool calls — no own business logic
- `infrastructure/` = concrete implementations of `core/` interfaces

### Vault
- Note slugs: `kebab-case`, no accents, lowercase (e.g. `elasticite-prix.md`)
- Tags: French, lowercase, no accents, hyphens (e.g. `biais-cognitifs`)

### Scripts
- One-shot / throwaway scripts go in `.meta/scratch/` (gitignored) — NOT
  `scripts/temp/` (deleted 2026-05-17, SCRIPT-M2) and never `scripts/setup/`
  (reserved for init) nor the project root
- Durable maintenance scripts live in `scripts/` (e.g. `reembed.py`)

### Git commits
- **ASCII-only commit messages.** No accented chars, em/en-dashes (`—`/`–`),
  curly quotes, or emoji. Use `-`, `"`, `'`. Conventional prefixes
  (`feat:`/`fix:`/`docs:`/`chore:`) per CLAUDE.md §5.
- **Why:** on the Windows dev shell, non-ASCII passed to `git commit -m`
  via the Bash tool is double-mojibake'd (`é`→`Ã©`, `—`→`â€"`) and persisted
  corrupted **in git history** (verified: `é` → bytes `c3 83 c2 a9`). This is
  shell/encoding-level — the `force_git_author` hook does NOT prevent it.
- **If corruption slips in:** recover + re-ASCII a message with
  `msg.encode('cp1252').decode('utf-8')` then transliterate; rewrite history
  with `git filter-branch --msg-filter` over the affected range ONLY (never
  touch commits that are ancestors of OpenTimestamps tags `v0.X.0` —
  rewriting them invalidates the `.timestamps/*.ots` antériorité proofs).
  Precedent: 8 commits cleaned 2026-05-18 (all post-`v0.3.0`, OTS safe).

---

## Document map

### Permanent documents (always current)

| Document | Role |
|----------|------|
| `CLAUDE.md` | Entry point — the law |
| `.meta/GUIDELINES.md` | Rules G1-G13 — the mentor |
| `docs/architecture/ARCHITECTURE.md` | Technical architecture, glossary |
| `docs/architecture/DATABASES.md` | DB schema reference |
| `config/system.yaml` | All tunable parameters |
| `core/config.py` | Pydantic models for config |
| `.meta/specs/2026-03-31-development-workflow.md` | 7-phase development process |
| `.meta/specs/2026-03-31-project-audit-spec.md` | Reusable audit method |

### Process workspace (`.meta/`)

```
.meta/
├── specs/              ← Active specs and brainstorm notes
│   └── future/         ← Validated specs NOT YET implemented
├── plans/              ← Active implementation plans
├── scratch/            ← Drafts, Superpowers outputs (gitignored)
├── audits/             ← Audit results (dated)
├── archive/            ← Implemented or obsolete specs and plans
└── GUIDELINES.md       ← This file
```

**Lifecycle:** Draft starts in `scratch/`. Once validated → `specs/` or `plans/`.
Once implemented → `archive/`. Deferred → `specs/future/`.

### Reference documents (stable)

| Document | Role |
|----------|------|
| `docs/VISION.md` | Strategic vision, north star |
| `docs/FUTURE-WORK.md` | Ideas backlog |
| `docs/mcp-setup.md` | MCP client setup guide |

---

## Advanced Claude Code options (deferred)

These options are documented here for future activation. They are NOT currently enabled.

| Option | Effect | When to enable |
|--------|--------|----------------|
| `enabledPlugins: ["obra/superpowers"]` | Force Superpowers plugin load | When plugin is stable enough to auto-load |
| `autoDreamEnabled: true` | Background memory consolidation | When project is large enough to benefit |
| `autoMemoryDirectory: ".meta/"` | Redirect Claude memory files to .meta/ | With autoDream |
| Plan mode (`Shift+Tab`) | Forces Claude to plan before acting | Already enforced via automatisme #2 |
| `statusLine` | Custom status bar content | When useful metrics are identified |
| Subagent persistent memory | Share context across spawned agents | When multi-agent workflows are needed |
