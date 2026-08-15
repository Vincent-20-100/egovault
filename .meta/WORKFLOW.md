# EgoVault — Engineering Development Workflow (.meta/WORKFLOW.md)

**Status:** LIVING STANDARD — The non-negotiable software engineering protocol for EgoVault.  
**Referenced From:** `AGENTS.md`, `CLAUDE.md`, `.meta/GUIDELINES.md`

---

## 1. Core Principles

1. **No Implementation Without a Validated Spec & Plan:** Never jump into code. Architectural clarity precedes code execution.
2. **No Spec Without Interactive Brainstorming:** Design decisions, trade-offs, and open questions must be aligned with the user first.
3. **Zero-Hardcode & Strict Parameterization:** Every tunable value must be exposed in `config/` (`system.yaml`, `user.yaml`, or `install.yaml`).
4. **Documentation Updates in the Same Commit:** Docs are load-bearing code. If code changes user-facing behavior, docs must update simultaneously.
5. **Adversarial Peer Review as Quality Gate:** Every plan and significant PR must pass adversarial review before merging.

---

## 2. The 7-Phase Engineering Lifecycle

```
BRAINSTORM → SPEC → PLAN → IMPLEMENT (TDD) → TEST → AUDIT → SHIP
     ↑                                                 │
     └───────────── Rework if review/audit fails ──────┘
```

### Phase 1 — BRAINSTORM (Interactive Design)
- **Trigger:** New feature, architectural pivot, or complex refactoring.
- **Output:** Discussion notes in `.meta/scratch/spec-<topic>-notes.md` or `.meta/references/`.
- **Goal:** Surface trade-offs, edge cases, algorithmic options, and user preferences. User validates before moving forward.

### Phase 2 — SPEC (The Functional Contract)
- **Trigger:** Brainstorm validated.
- **Output:** Spec file in `.meta/specs/<date>-<topic>-spec.md`.
- **Requirements:**
  - Clearly states WHAT and WHY, mathematical formulas, and architectural boundaries.
  - Lists all impacted files, database schemas, and configuration keys.
  - Formally marks any obsolete or superseded specs.
  - Written 100% in technical English.

### Phase 3 — PLAN (Step-by-Step Implementation Blueprint)
- **Trigger:** Spec validated.
- **Output:** Plan file in `.meta/plans/<date>-<topic>-plan.md`.
- **Requirements:**
  - Breaks implementation into cohesive, numbered tasks with explicit file paths.
  - Each task specifies: *Files to touch*, *Actions to perform*, *Tests to write*, and *Docs to update*.
  - Identifies dependencies, lock mechanisms, and migration scripts.

### Phase 4 — IMPLEMENT (Spec-Driven TDD)
- **Trigger:** Plan approved by user.
- **Agent Persona:** **Builder / Implementer** (follows active plan strictly, writes tests first, never improvises).
- **Execution:**
  - Write tests first (`tests/` mirroring project structure).
  - Implement minimum clean code satisfying the test.
  - Follow the plan strictly — no scope creep or ad hoc refactoring.
  - Commit atomically: `feat:`, `fix:`, `docs:`, `chore:` in English.

### Phase 5 — TEST (Automated Quality Gate)
- **Trigger:** All plan tasks implemented.
- **Execution:** Full suite execution via `uv run pytest`.
- **Requirement:** 100% green suite (0 failed, 0 errors, deterministic results).

### Phase 6 — AUDIT (Adversarial Compliance Review)
- **Trigger:** Tests pass.
- **Agent Persona:** **Adversarial Reviewer** (hunts for race conditions, broken contracts, missing tests, and hardcodes).
- **Execution:** Subagent executes [`.meta/AUDIT-SPEC.md`](AUDIT-SPEC.md) across all 8 domains.
- **Requirement:** Zero Critical violations, zero Major violations.

### Phase 7 — SHIP (State Consolidation)
- **Trigger:** Audit clean.
- **Execution:**
  - Update `PROJECT-STATUS.md` and rewrite `SESSION-CONTEXT.md`.
  - Update `docs/architecture/` and `docs/user-guide/`.
  - Archive completed specs and plans to `.meta/archive/`.

---

## 3. Between-Phase Quality Gates

| Transition Gate | Condition Required to Advance | Decided By |
|---|---|---|
| **Brainstorm → Spec** | User approves design direction and notes | User |
| **Spec → Plan** | Spec reviewed, zero ambiguities, mathematically sound | User |
| **Plan → Implement** | Plan passes adversarial review and user gives explicit "Go" | User |
| **Implement → Test** | All tasks executed and committed | Agent |
| **Test → Audit** | 100% automated pytest suite passes | Agent |
| **Audit → Ship** | Audit clean (0 Critical, 0 Major) | User + Agent |
