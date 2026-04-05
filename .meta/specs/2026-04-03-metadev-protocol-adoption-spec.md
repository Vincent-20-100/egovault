# Spec — metadev-protocol adoption

**Date:** 2026-04-03
**Status:** DRAFT — pending user validation
**Brainstorm:** `docs/superpowers/specs/2026-04-03-metadev-protocol-adoption-notes.md`
**Supersedes:** Nothing (new process layer, no code changes)

---

## 1. Goal

Adopt the best patterns from metadev-protocol and obra/superpowers into EgoVault's
development workflow. This is a **process-only change** — no application code is modified.

**Why now:** CLAUDE.md is 408 lines. LLMs lose track of rules buried in a large file.
The split + reorganization makes the project portable and easier for any LLM to follow.

---

## 2. What changes

### 2.1 Split CLAUDE.md (Decision C)

**Current:** CLAUDE.md = 408 lines containing identity, structure, rules, conventions, workflow refs, status refs.

**After:**
- **CLAUDE.md** (≤80 lines) — "the law": identity, tech stack, structure, commands, automatisms, output paths, pointer to GUIDELINES.md
- **`.meta/GUIDELINES.md`** (~150 lines) — "the mentor": G1-G13 rules with examples, pre-commit checklist, conventions, document map, architecture details (G4 VaultContext pattern)

**Rule:** CLAUDE.md says `Apply all rules from .meta/GUIDELINES.md`. LLM reads it at session start.

### 2.2 Rename `docs/superpowers/` → `.meta/` (Decision D)

Move the entire directory tree. Update all references in:
- CLAUDE.md
- `.meta/GUIDELINES.md` (the moved content)
- `PROJECT-STATUS.md`
- `SESSION-CONTEXT.md`
- Development workflow spec
- Project audit spec

**New structure:**
```
.meta/
├── GUIDELINES.md          ← Rules G1-G13 (the mentor)
├── specs/                 ← Active specs
│   └── future/            ← Validated, deferred specs
├── plans/                 ← Active plans
├── scratch/               ← Drafts from brainstorm/plan skills (gitignored)
├── audits/                ← Audit results
└── archive/               ← Implemented specs and plans
    ├── specs/
    └── plans/
```

**Add `.meta/scratch/` to `.gitignore`.**

### 2.3 Superpowers output paths in CLAUDE.md (Decision B)

Add a section telling Superpowers (and any LLM) where to write outputs:

```
Brainstorm drafts → .meta/scratch/spec-<topic>.md
Plan drafts → .meta/scratch/plan-<topic>.md
Validated specs → .meta/specs/<date>-<topic>.md
Validated plans → .meta/plans/<date>-<topic>.md
Audits → .meta/audits/audit-results-<date>.md
```

### 2.4 Project-specific skills (Decision A — updated)

Create 3 skills in `.claude/skills/`:

| Skill | File | Role |
|-------|------|------|
| `/save-progress` | `.claude/skills/save-progress.md` | End-of-session checklist: update PROJECT-STATUS.md + SESSION-CONTEXT.md, commit, push |
| `/lint` | `.claude/skills/lint.md` | Run `ruff check --fix . && ruff format .` |
| `/test` | `.claude/skills/test.md` | Run `pytest tests/` with optional args |

**No fallback skills** — Superpowers is assumed installed for brainstorm/plan workflows.

### 2.5 Hooks (Decision E)

Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "ruff check --fix $FILE && ruff format $FILE"
      }
    ]
  }
}
```

This auto-formats Python files after every edit. Non-Python files are ignored by ruff.

---

## 3. What does NOT change

- **No application code** — tools/, workflows/, infrastructure/, api/, mcp/, cli/ untouched
- **No test changes** — tests/ untouched
- **PROJECT-STATUS.md stays at root** — must be immediately visible
- **SESSION-CONTEXT.md stays at root** — must be immediately visible
- **The 7-phase workflow stays** — only the spec's file path changes
- **G1-G13 rules stay identical** — they just move to GUIDELINES.md
- **Superpowers plugin remains external** — installed per-machine, not in repo

---

## 4. File map

### New files
| File | Content |
|------|---------|
| `.meta/GUIDELINES.md` | G1-G13 rules, conventions, document map, architecture details |
| `.claude/skills/save-progress.md` | End-of-session skill |
| `.claude/skills/lint.md` | Ruff lint+format skill |
| `.claude/skills/test.md` | Pytest runner skill |

### Modified files
| File | Change |
|------|--------|
| `CLAUDE.md` | Rewrite to ≤80 lines (law only) |
| `.claude/settings.json` | Add hooks section |
| `.gitignore` | Add `.meta/scratch/` |
| `PROJECT-STATUS.md` | Update paths, mark this task done |
| `SESSION-CONTEXT.md` | Update paths, current state |

### Moved files (all under `docs/superpowers/` → `.meta/`)
| From | To |
|------|-----|
| `docs/superpowers/specs/*` | `.meta/specs/*` |
| `docs/superpowers/plans/*` | `.meta/plans/` (empty — all archived) |
| `docs/superpowers/audits/*` | `.meta/audits/*` |
| `docs/superpowers/archive/*` | `.meta/archive/*` |

### Files with path references to update
| File | References to fix |
|------|-------------------|
| `.meta/specs/2026-03-31-development-workflow.md` | Output paths, audit spec path |
| `.meta/specs/2026-03-31-project-audit-spec.md` | Self-reference paths |
| `.meta/GUIDELINES.md` | Document map paths |

### Deleted
| Path | Reason |
|------|--------|
| `docs/superpowers/` | Replaced by `.meta/` |

---

## 5. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Git history broken by rename | Use `git mv` for traceability |
| CLAUDE.md too terse after split | Test: can a fresh LLM context understand the project from CLAUDE.md alone? If not, add lines |
| Ruff hook fails on non-Python files | Ruff ignores non-Python files by default — no risk |
| Skills not found by Claude Code | Verify `.claude/skills/` is the correct path per Claude Code docs |

---

## 6. Success criteria

- [ ] CLAUDE.md ≤80 lines
- [ ] `.meta/GUIDELINES.md` contains all G1-G13 rules
- [ ] `docs/superpowers/` no longer exists
- [ ] All internal path references updated (zero broken refs)
- [ ] 3 skills created and functional
- [ ] Ruff hook fires on Python file edits
- [ ] `.meta/scratch/` is gitignored
- [ ] All existing tests still pass (no code changes = no regressions)
