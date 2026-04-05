# EgoVault — Development Workflow

**Date:** 2026-03-31
**Status:** ACTIVE — this is the process we follow, no exceptions.
**Location:** Referenced from CLAUDE.md, lives here for detail.

---

## Principles

1. **No implementation without a validated spec.** Ever.
2. **No spec without a brainstorm.** Complex features need interactive design.
3. **No merge without passing audit.** The audit spec is the quality gate.
4. **Doc is updated IN the same commit as code.** Not after, not "later."
5. **Each phase produces a deliverable.** No phase is "done" until its output is committed.

---

## The 7 phases

```
BRAINSTORM → SPEC → PLAN → IMPLEMENT → TEST → AUDIT → SHIP
    ↑                                              |
    └──────── rework if audit fails ───────────────┘
```

### Phase 1 — BRAINSTORM (interactive)

**Trigger:** New feature, architecture change, or complex decision.
**Who:** User + Claude (interactive dialogue).
**Skill:** `superpowers:brainstorming`
**Output:** Discussion notes saved to `docs/superpowers/specs/<date>-<name>-notes.md`

**Rules:**
- Claude presents options, trade-offs, open questions
- User decides — Claude does NOT write specs without user input
- All decisions are recorded with rationale
- Notes are committed before moving to Phase 2

**Deliverable:** Committed notes file with all decisions.

---

### Phase 2 — SPEC (write the contract)

**Trigger:** Brainstorm notes validated by user.
**Who:** Claude writes, user validates.
**Skill:** None (direct writing based on brainstorm notes).
**Output:** Spec file `docs/superpowers/specs/<date>-<name>.md`

**Rules:**
- Spec references brainstorm notes
- Spec has: Date, Status, Supersedes (if applicable)
- Spec describes WHAT and WHY, not implementation details
- Spec lists all impacted files (file map)
- Spec lists all future work with hooks needed NOW
- Spec under 1000 lines (split if needed)
- Any prior conflicting spec is marked OBSOLETE
- User validates before moving to Phase 3

**Deliverable:** Committed spec file, user says "go."

---

### Phase 3 — PLAN (step-by-step execution order)

**Trigger:** Spec validated by user.
**Who:** Claude writes.
**Skill:** `superpowers:writing-plans`
**Output:** Plan file `docs/superpowers/plans/<date>-<name>.md`

**Rules:**
- Plan references the spec (exact filename)
- Plan breaks work into numbered steps (max 15)
- Each step has: files to touch, what to do, what to test
- Steps are ordered by dependency (no circular deps)
- **Each step includes its doc updates** — not a separate "update docs" step at the end
- Plan identifies which steps can be parallelized
- Plan includes a "pre-flight check" step: verify spec assumptions still hold

**Step template:**
```markdown
### Step N — [title]
**Files:** list of files to create/modify
**Do:** what to implement
**Test:** how to verify (specific test command or manual check)
**Doc:** what doc to update in this same commit
**Commit message:** pre-written commit message
```

**Deliverable:** Committed plan file.

---

### Phase 4 — IMPLEMENT (execute the plan)

**Trigger:** Plan committed.
**Who:** Claude executes, step by step.
**Skill:** `superpowers:executing-plans`
**Output:** Code changes, committed per step.

**Rules:**
- Follow the plan exactly — do not improvise new features
- One commit per step (code + tests + doc in same commit)
- If a step fails or reveals a problem, STOP and report to user
- Do NOT fix unrelated issues found during implementation
- Do NOT refactor code not mentioned in the plan
- Mark each step done in the plan file as you go
- Run tests after each step

**Commit message format:**
```
feat|fix|docs|chore: <description from plan>

Step N/M of <plan-name>
```

**Deliverable:** All steps committed and pushed. Tests pass.

---

### Phase 5 — TEST (verify everything works)

**Trigger:** All implementation steps committed.
**Who:** Claude runs, reports results.
**Output:** Test results in conversation.

**Rules:**
- Run full test suite: `python -m pytest tests/ -x`
- Report: X passed, Y failed, Z errors
- If failures: diagnose, fix, commit fix as separate commit
- Do NOT move to Phase 6 until all tests pass

**Deliverable:** Clean test run (or documented known failures with reasons).

---

### Phase 6 — AUDIT (verify compliance)

**Trigger:** Tests pass.
**Who:** Claude agents (parallel), using audit spec.
**Skill:** Agents execute `docs/superpowers/specs/2026-03-31-project-audit-spec.md`
**Output:** Results file `docs/superpowers/audits/audit-results-<date>.md`

**Rules:**
- Run only the audit domains relevant to the changes (not full audit every time)
- Minimum: Domain 2 (architecture), Domain 3 (guardrails), Domain 4 (impl vs spec)
- If violations found:
  - MINOR: fix in place, commit
  - MAJOR: fix in place, commit, re-run affected audit domain
  - CRITICAL: STOP, report to user, may need to go back to Phase 1

**Deliverable:** Committed audit results. Zero critical, zero major.

---

### Phase 7 — SHIP (update the record)

**Trigger:** Audit passes.
**Who:** Claude updates, user confirms.
**Output:** Updated CLAUDE.md, ARCHITECTURE.md, FUTURE-WORK.md.

**Rules:**
- Update CLAUDE.md progress section (mark feature as done)
- Update ARCHITECTURE.md if structure changed
- Update FUTURE-WORK.md if new future items discovered
- Commit all doc updates
- Push to branch
- Report to user: "Feature X complete. N commits. Audit clean."

**Deliverable:** Clean branch, all docs current, ready for PR if requested.

---

## Between-phase gates

| Gate | Condition | Who decides |
|------|-----------|-------------|
| Brainstorm → Spec | User validates notes | User |
| Spec → Plan | User says "go" | User |
| Plan → Implement | Plan committed | Automatic |
| Implement → Test | All steps committed | Automatic |
| Test → Audit | Tests pass | Automatic |
| Audit → Ship | Zero critical/major | Automatic (user if rework needed) |

---

## Agent prompts for repeatable tasks

### Audit agent prompt (per domain)

```
You are auditing the EgoVault project. RESEARCH ONLY — do not modify files.

Read the audit spec: docs/superpowers/specs/2026-03-31-project-audit-spec.md

Execute Domain [N] ([name]).

[Domain-specific instructions from audit spec]

Output findings in this format:
### [DOMAIN]-[NUMBER] — [SHORT TITLE]
- **Severity:** CRITICAL | MAJOR | MINOR
- **File:** path:line
- **Violation:** rule broken
- **Description:** what's wrong
- **Fix:** how to fix

End with count: Domain N: X critical, Y major, Z minor.
```

### Code review agent prompt

```
You are reviewing code changes for the EgoVault project. RESEARCH ONLY.

Read CLAUDE.md guardrails G1-G12.
Read the spec: [spec file path]
Read the plan: [plan file path]

Review all changes in the current commit/branch:
1. Does the code match what the spec describes?
2. Does the code follow the plan steps?
3. Are guardrails G1-G12 respected?
4. Are tests included and meaningful?
5. Is documentation updated in the same commits as code?

Output: list of issues found, or "LGTM" if clean.
```

### Doc sync agent prompt

```
You are verifying documentation accuracy for EgoVault. RESEARCH ONLY.

Check these files for consistency:
- CLAUDE.md progress section vs actual code
- ARCHITECTURE.md structure vs actual file tree
- DATABASES.md schema vs infrastructure/db.py
- system.yaml vs core/config.py
- mcp-setup.md vs mcp/server.py tools

Output: list of mismatches with file:line references, or "All synced."
```

---

## What this workflow prevents

| Problem | Prevention |
|---------|-----------|
| Specs written without brainstorm | Phase 1 gate |
| Code written without spec | Phase 2 gate |
| Implementation deviates from spec | Plan step-by-step + audit |
| Docs lag behind code | Doc updates in same commit as code |
| Unrelated refactoring creeps in | "Follow the plan exactly" rule |
| Silent failures introduced | Phase 5 full test run |
| Guardrail violations | Phase 6 audit |
| Conflicting specs | Supersession markers + OBSOLETE |
| Lost context between sessions | Every phase produces a committed file |

---

## Exceptions

- **Hotfix:** Skip brainstorm/spec for critical bugs. Still need: implement → test → audit → ship.
- **Trivial change:** Config value change, typo fix. Still need: implement → test → ship (skip audit).
- **Audit-only:** Periodic health check. Just run Phase 6 standalone.
