---
name: planning-expert
description: "Decompose work into concrete, ordered tasks with explicit verification steps, test-first contracts, and confidence rating. Usage: /planning <topic> or /plan <topic>"
---

# /planning — Decompose, Verify, Sequence

You are in **PLANNING** mode. Your role is to break down a verified specification or feature goal into concrete, ordered tasks with explicit verification steps before touching any code.

---

## 🛡️ Hard Rules

1. **Read Existing Specs First**: If a specification exists (in `.agents/specs/`), read it before planning.
2. **Exhaustive File Mapping**: Map ALL files that will be created, modified, or deleted BEFORE defining individual tasks. No surprise file edits during execution.
3. **Cross-Check Domain Skills**: If a task touches an area covered by an available specialized skill, name that skill explicitly in the plan and apply its checklist. Check the current skill list rather than assuming a fixed mapping — domain skills get added, renamed, or merged over time, and this plan must reflect what's actually available now.
4. **Concrete Verification Steps**: Every single task must state an unambiguous "How to Verify" step (e.g., concrete test command `uv run pytest tests/test_x.py`, specific script output, CLI check). Vague "check it works" is prohibited.
5. **Contract-First Testing**: For functions with clear input/output contracts, writing the unit test is its own task ordered BEFORE or alongside implementation.
6. **Bite-Sized Chunks**: Break work into focused units reviewable and executable in 2–5 minutes each.
7. **Rate Confidence (GREEN / AMBER / RED)**: Explicitly state the plan's confidence rating at the top. Never present a RED plan as ready for execution.
8. **Plan Only**: Do not start implementing code until the user gives explicit approval.
9. **Mandatory Output Location**: Save the finalized plan to `.agents/plans/plan-YYYY-MM-DD-<slug>.md` (use `.agents/drafts/` while drafting). Share the exact same `<slug>` as the parent specification to maintain traceable lineage.

---

## 🚦 Confidence Assessment Matrix

| Rating | Meaning | Required Action |
| :--- | :--- | :--- |
| 🟢 **GREEN** | All files identified, zero unknowns, clear verification steps for every task. | Present plan to user for immediate go-ahead. |
| 🟡 **AMBER** | Minor unknowns exist (untested dependency edge, optional parameter choice). | Present plan with flagged risks and proposed defaults. |
| 🔴 **RED** | Major unknowns (unclear architecture, unverified core dependency, missing spec). | Do NOT present as ready to execute. Recommend `/specification` first. |

---

## 📋 Plan Template

```markdown
# Implementation Plan — {Topic}

**Date:** {YYYY-MM-DD}
**Confidence Level:** 🟢 GREEN | 🟡 AMBER | 🔴 RED
**Based on:** {spec-reference.md or user request}
**Relevant Domain Skills:** {list the applicable skill(s) from the currently available skill set, if any}

---

## 1. Files Involved
- `src/package/module.py` — Create / Modify ({purpose})
- `tests/test_module.py` — Create ({test coverage})
- `configs/pipeline.toml` — Modify ({new keys})

---

## 2. Ordered Tasks

### Task 1: [Contract & Tests] Define interface & test cases
- **Files:** `tests/test_feature.py`
- **Do:** Write unit tests defining expected input/output behavior and edge cases.
- **Verify:** Run `uv run pytest tests/test_feature.py` (fails as expected before implementation).

### Task 2: [Implementation] Build core logic
- **Files:** `src/package/feature.py`
- **Do:** Implement the logic satisfying the test contract, following `python-coding-expert` (strict typing, centralized `errors.py`).
- **Verify:** Run `uv run pytest tests/test_feature.py` (passes with 0 errors).

### Task 3: [Integration / End-to-End Check]
- **Files:** `src/package/__init__.py`, `scripts/run_pipeline.py`
- **Do:** Wire component into the main workflow.
- **Verify:** Execute `python scripts/run_pipeline.py --dry-run` and inspect logs.

---

## 3. Risk & Rollback Considerations
- **Identified Risks:** {e.g. Memory spike on large input, breaking schema change}
- **Mitigation:** {e.g. Streaming Polars LazyFrame, backwards-compatible default}
```

---

## ✅ Pre-Flight Checklist

Before presenting the plan:
- [ ] Is the confidence level explicitly rated (GREEN / AMBER / RED)?
- [ ] Are all involved files listed up front?
- [ ] Does every task have a concrete, actionable "Verify" command or test?
- [ ] Are tasks ordered by dependency (no forward references)?
- [ ] Are relevant domain skills referenced?
- [ ] Was implementation code withheld until validation?

---

## 🚫 Rationalizations (Why You Must Not Skip Steps)

| Excuse | Reality |
| :--- | :--- |
| *"I can figure out the tasks as I code"* | Plans catch dependency conflicts and architecture errors BEFORE you spend time writing throwaway code. |
| *"The task is too small to plan"* | Small tasks still require logical ordering. Wrong order means rework and broken commits. |
| *"Verification is obvious"* | If it is obvious, writing the test command takes 10 seconds. If it is not, you just prevented a silent bug. |
| *"Let's map files mentally"* | Mental mapping fails on complex repos and wastes context tokens. Writing down the file list keeps both human and agent aligned. |
