# metadev-protocol Adoption — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize EgoVault's process layer — split CLAUDE.md, rename docs/superpowers/ → .meta/, add skills and hooks.

**Architecture:** Process-only change. No application code modified. CLAUDE.md becomes a ≤80-line "law" file pointing to `.meta/GUIDELINES.md` for the full G1-G13 ruleset. All specs/plans/audits move from `docs/superpowers/` to `.meta/`.

**Tech Stack:** Markdown, Claude Code skills (.md), Claude Code hooks (settings.json), ruff.

**Spec:** `docs/superpowers/specs/2026-04-03-metadev-protocol-adoption-spec.md`
**Brainstorm:** `docs/superpowers/specs/2026-04-03-metadev-protocol-adoption-notes.md`

---

## Pre-flight check

- [ ] Confirm `docs/superpowers/` exists with specs/, plans/ (empty), audits/, archive/
- [ ] Confirm `.meta/` does NOT exist yet
- [ ] Confirm `.claude/skills/` does NOT exist yet
- [ ] Confirm all tests pass (baseline — no code changes in this plan)

Run: `.venv/Scripts/python -m pytest tests/ -x -q`

---

### Task 1: Rename `docs/superpowers/` → `.meta/`

This must happen first — all subsequent tasks reference `.meta/` paths.

**Files:**
- Move: `docs/superpowers/` → `.meta/`
- Create: `.meta/scratch/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Move the directory**

```bash
git mv docs/superpowers .meta
```

- [ ] **Step 2: Create scratch directory + gitkeep**

```bash
mkdir -p .meta/scratch
touch .meta/scratch/.gitkeep
```

- [ ] **Step 3: Add `.meta/scratch/` to `.gitignore`**

Add after the existing `.worktrees/` line in `.gitignore`:

```
# Meta — scratch drafts (ephemeral)
.meta/scratch/
!.meta/scratch/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git add .meta/ .gitignore
git commit -m "chore: rename docs/superpowers/ → .meta/

Decision D from metadev-protocol adoption spec."
```

---

### Task 2: Update path references in active documents

All active documents that reference `docs/superpowers/` must be updated to `.meta/`.

**Files:**
- Modify: `.meta/specs/2026-03-31-development-workflow.md`
- Modify: `.meta/specs/2026-03-31-project-audit-spec.md`
- Modify: `docs/architecture/ARCHITECTURE.md`
- Modify: `docs/architecture/CONTRACTS.md`
- Modify: `SECURITY.md`
- Modify: `PROJECT-STATUS.md`
- Modify: `SESSION-CONTEXT.md`

- [ ] **Step 1: Update development-workflow.md**

Replace all `docs/superpowers/` → `.meta/` in `.meta/specs/2026-03-31-development-workflow.md`:

| Line | Old | New |
|------|-----|-----|
| 32 | `docs/superpowers/specs/<date>-<name>-notes.md` | `.meta/specs/<date>-<name>-notes.md` |
| 49 | `docs/superpowers/specs/<date>-<name>.md` | `.meta/specs/<date>-<name>.md` |
| 70 | `docs/superpowers/plans/<date>-<name>.md` | `.meta/plans/<date>-<name>.md` |
| 142 | `docs/superpowers/specs/2026-03-31-project-audit-spec.md` | `.meta/specs/2026-03-31-project-audit-spec.md` |
| 143 | `docs/superpowers/audits/audit-results-<date>.md` | `.meta/audits/audit-results-<date>.md` |
| 195 | `docs/superpowers/specs/2026-03-31-project-audit-spec.md` | `.meta/specs/2026-03-31-project-audit-spec.md` |

- [ ] **Step 2: Update project-audit-spec.md**

Replace all `docs/superpowers/` → `.meta/` in `.meta/specs/2026-03-31-project-audit-spec.md`:

| Line | Old | New |
|------|-----|-----|
| 29 | `docs/superpowers/specs/*.md` | `.meta/specs/*.md` |
| 30 | `docs/superpowers/specs/*.md` | `.meta/specs/*.md` |
| 34 | `docs/superpowers/plans/*.md` | `.meta/plans/*.md` |

- [ ] **Step 3: Update ARCHITECTURE.md**

Replace all `docs/superpowers/specs/` → `.meta/specs/` in `docs/architecture/ARCHITECTURE.md`.
There are ~10 references (lines 432, 436, 457, 467, 492, 503, 521, 618).
Use `replace_all` for the substitution.

- [ ] **Step 4: Update CONTRACTS.md**

Replace `docs/superpowers/specs/2026-03-27-api-design.md` → `.meta/specs/2026-03-27-api-design.md` in `docs/architecture/CONTRACTS.md` (line 238).

- [ ] **Step 5: Update SECURITY.md**

Replace `docs/superpowers/specs/2026-03-29-security-design.md` → `.meta/specs/2026-03-29-security-design.md` in `SECURITY.md` (line 27).

- [ ] **Step 6: Update PROJECT-STATUS.md**

Replace `docs/superpowers/specs/` → `.meta/specs/` in `PROJECT-STATUS.md` (line 15).
Also update the active specs table (line 26-28) to use `.meta/` paths.

- [ ] **Step 7: Update archive files (bulk)**

Replace all `docs/superpowers/` → `.meta/` in files under `.meta/archive/`. These are historical but should still have correct paths for traceability.

```bash
# Verify the replacements first
grep -r "docs/superpowers" .meta/archive/ --include="*.md" -l
```

Then apply `replace_all` on each file found.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: update all docs/superpowers/ references to .meta/

Step 2 of metadev-protocol adoption."
```

---

### Task 3: Split CLAUDE.md into law + GUIDELINES.md

The core task. CLAUDE.md becomes ≤80 lines (the law). G1-G13, conventions, document map details, and architecture details move to `.meta/GUIDELINES.md`.

**Files:**
- Rewrite: `CLAUDE.md` (408 → ≤80 lines)
- Create: `.meta/GUIDELINES.md` (~150 lines)

- [ ] **Step 1: Write `.meta/GUIDELINES.md`**

Extract from current CLAUDE.md and adapt:
- §3 Document map (permanent vs provisional) — update paths to `.meta/`
- §6 Architecture rules G1-G13 with all examples
- §6 Pre-commit checklist
- §8 Conventions (Python, Vault, Scripts)
- §4 G4 VaultContext pattern details

Header:
```markdown
# EgoVault — Development Guidelines

> **The mentor.** Read this file at the start of every session.
> These rules exist because LLMs consistently make the same mistakes.
> Every rule was triggered by a real incident. Hard constraints, not suggestions.
```

- [ ] **Step 2: Rewrite CLAUDE.md**

New CLAUDE.md structure (≤80 lines):

```markdown
# EgoVault — Claude Code Entry Point

> The law. Always loaded. ≤80 lines.

## 1. Identity
EgoVault: personal knowledge vault — ingest, embed, search, generate notes.
Portfolio-grade architecture. Reusable template.

## 2. Tech stack
[6 lines — same as current]

## 3. Structure
[project tree — ~20 lines, same as current]

## 4. Commands
[3 commands — same as current]

## 5. Rules
Apply all rules from `.meta/GUIDELINES.md` — read it at session start.

## 6. Workflow
7-phase process: BRAINSTORM → SPEC → PLAN → IMPLEMENT → TEST → AUDIT → SHIP
Full spec: `.meta/specs/2026-03-31-development-workflow.md`

## 7. Context files
- `PROJECT-STATUS.md` — live state, next action, debt, roadmap
- `SESSION-CONTEXT.md` — WHY decisions were made, traps, open questions
Read both at session start. Update both at session end.

## 8. Output paths (for Superpowers and all LLMs)
- Brainstorm drafts → `.meta/scratch/spec-<topic>.md`
- Plan drafts → `.meta/scratch/plan-<topic>.md`
- Validated specs → `.meta/specs/<date>-<topic>.md`
- Validated plans → `.meta/plans/<date>-<topic>.md`
- Audits → `.meta/audits/audit-results-<date>.md`
```

- [ ] **Step 3: Verify line count**

```bash
wc -l CLAUDE.md
```

Expected: ≤80 lines. If over, trim tree or merge sections.

- [ ] **Step 4: Verify GUIDELINES.md contains all G1-G13**

```bash
grep -c "^### G" .meta/GUIDELINES.md
```

Expected: 13 (G1 through G13).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md .meta/GUIDELINES.md
git commit -m "docs: split CLAUDE.md into law (≤80 lines) + .meta/GUIDELINES.md

Decision C from metadev-protocol adoption. CLAUDE.md is the law (always loaded).
GUIDELINES.md is the mentor (read at session start)."
```

---

### Task 4: Create project-specific skills

Three skills in `.claude/skills/`. Each is a standalone markdown file.

**Files:**
- Create: `.claude/skills/save-progress.md`
- Create: `.claude/skills/lint.md`
- Create: `.claude/skills/test.md`

- [ ] **Step 1: Create `/save-progress` skill**

Write `.claude/skills/save-progress.md`:

```markdown
---
name: save-progress
description: End-of-session checklist — update context files, commit, push
---

# /save-progress — End of Session

Run this before ending a work session.

## Checklist

1. **Update `PROJECT-STATUS.md`:**
   - Move completed items from "Pending tasks" to "Implemented features"
   - Update "Next action" to reflect what comes next
   - Add a row to "Session history" with today's date, branch, and summary

2. **Rewrite `SESSION-CONTEXT.md`:**
   - Update "Current state" section
   - Update "Architecture decisions still active" (add new, remove stale)
   - Update "Traps to avoid" (add new learnings)
   - Update "Deferred items" table
   - Update "Open questions" (add new, resolve answered)
   - Remove reasoning that is no longer relevant

3. **Commit and push:**
   ```bash
   git add PROJECT-STATUS.md SESSION-CONTEXT.md
   git commit -m "docs: update project status and session context"
   git push
   ```

4. **Report to user:** "Session saved. Safe to close."
```

- [ ] **Step 2: Create `/lint` skill**

Write `.claude/skills/lint.md`:

```markdown
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
```

- [ ] **Step 3: Create `/test` skill**

Write `.claude/skills/test.md`:

```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/
git commit -m "feat: add project skills — /save-progress, /lint, /test

Decision A from metadev-protocol adoption spec."
```

---

### Task 5: Add ruff hook

**Files:**
- Modify: `.claude/settings.json`

- [ ] **Step 1: Add hooks section to settings.json**

Current content has only `permissions`. Add a `hooks` key:

```json
{
  "permissions": {
    ...existing...
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "ruff check --fix \"$FILE\" && ruff format \"$FILE\""
      }
    ]
  }
}
```

Note: Quotes around `$FILE` for paths with spaces (Windows).

- [ ] **Step 2: Verify hook syntax**

Check that the JSON is valid:

```bash
python -c "import json; json.load(open('.claude/settings.json'))"
```

- [ ] **Step 3: Commit**

```bash
git add .claude/settings.json
git commit -m "chore: add ruff PostToolUse hook for auto-formatting

Decision E from metadev-protocol adoption spec."
```

---

### Task 6: Clean stale references

**Files:**
- Modify: `.meta/GUIDELINES.md` (or CLAUDE.md if ref survived the split)

- [ ] **Step 1: Remove stale unified-ingest spec reference**

Current CLAUDE.md line 226 references:
```
See `docs/superpowers/specs/2026-03-31-unified-ingest-architecture.md` §2.
```

This spec is archived. The G4 section in GUIDELINES.md should reference the VaultContext pattern directly (it's implemented now, not "spec pending"). Remove the "spec pending" note and the stale path.

- [ ] **Step 2: Verify no remaining `docs/superpowers` references in active files**

```bash
grep -r "docs/superpowers" --include="*.md" . | grep -v ".meta/archive/" | grep -v ".meta/specs/2026-04-03-metadev"
```

Expected: zero results (archive files are ok, brainstorm notes are ok).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: clean stale spec references in guidelines"
```

---

### Task 7: Final verification + context update

- [ ] **Step 1: Run tests (baseline check — no code changed)**

```bash
.venv/Scripts/python -m pytest tests/ -x -q
```

Expected: 374 tests pass (same as before — no code was modified).

- [ ] **Step 2: Verify success criteria**

```bash
# CLAUDE.md ≤80 lines
wc -l CLAUDE.md

# GUIDELINES.md has all 13 rules
grep -c "^### G" .meta/GUIDELINES.md

# docs/superpowers/ no longer exists
ls docs/superpowers/ 2>&1

# .meta/scratch/ is gitignored
git status .meta/scratch/

# Skills exist
ls .claude/skills/

# Hook is valid JSON
python -c "import json; json.load(open('.claude/settings.json'))"
```

- [ ] **Step 3: Update PROJECT-STATUS.md**

Mark "metadev-protocol adoption" as done in pending tasks and implemented features.
Update "Next action" to "B2 — Security Phase 2".

- [ ] **Step 4: Update SESSION-CONTEXT.md**

Rewrite with current state. Remove metadev decisions from "NEW" — they're now implemented.

- [ ] **Step 5: Commit**

```bash
git add PROJECT-STATUS.md SESSION-CONTEXT.md
git commit -m "docs: update project status — metadev-protocol adoption complete"
```

---

## Task dependency graph

```
Task 1 (rename)
    ↓
Task 2 (update refs)
    ↓
Task 3 (split CLAUDE.md) ─── depends on Task 1 (GUIDELINES.md goes in .meta/)
    ↓                         depends on Task 2 (refs already updated)
Task 4 (skills) ──────── independent after Task 1
Task 5 (hooks) ───────── independent
Task 6 (clean refs) ──── depends on Task 3 (stale ref is in GUIDELINES.md)
    ↓
Task 7 (verify + context)
```

**Parallelizable:** Tasks 4 + 5 can run in parallel after Task 2.
**Sequential:** 1 → 2 → 3 → 6 → 7.
