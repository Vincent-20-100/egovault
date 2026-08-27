# Living Documentation & Memory Maintenance (`rules/memory.md`)

> **Enforcement**: Engineering discipline across multi-session AI agent workflows.

---

## 🧠 1. Core Principle

> **False context causes far more damage than missing context.**

An AI agent reading an obsolete or contradictory context document will confidently execute in the wrong direction. An AI agent starting with an empty context will inspect files or ask questions — which is easily recoverable.

At the end of every delivered milestone: **remove stale, superseded, or contradictory notes before adding new ones.**

---

## 📌 2. Living Context Document Rules (`SESSION-CONTEXT.md` / `ACTIVE-TASKS.md`)

1. **Rewrite Over Blind Appending**:
   - Do not use context documents as an endless chronological append-log.
   - When a milestone lands or architecture changes, rewrite the context to reflect current reality.
   - Delete reasoning that has already been implemented or superseded.
2. **Keep it Skimmable (<1 Minute Read)**:
   - Structure context with clear bullet points, current state, active blocker (if any), and next concrete milestone.
   - If deep investigative notes are produced during a session, move them to a separate artifact (e.g. `docs/investigations/` or `.meta/active/`) and link to it concisely.
3. **Explicitly Track Decisions & Invariants**:
   - Record WHY a particular architectural path or library was chosen to prevent future sessions from re-exploring rejected paths.

---

## 🗺️ 3. Long-Term Project Roadmap (`PILOT.md` / `ROADMAP.md`)

1. **Update Upon Status Changes**:
   - Mark completed deliverables as `[x] DONE` and refine immediate next priorities.
   - Clean up scope sections that no longer reflect the project's actual trajectory.
2. **Commit Context With Code**:
   - Always commit updated context and documentation files alongside the code changes that made them relevant.

---

## ⚡ 4. Session Length & Token Budget Warning (Mise en garde)

- **The Context Snowball Effect**: As sessions grow beyond 15–20 turns, re-sending the accumulated conversation history on every message causes exponential token consumption and induces attention degradation (*context rot*).
- **Milestone Reset & Compaction Reflex**:
  - When completing a substantial milestone or when context grows heavy, proactively suggest running `/compact` or opening a clean session for the next milestone.
  - Keep the conversation agile: offload heavy research to subagents (`research_worker`) and heavy refactoring to execution workers (`data_dev_worker`).

---

## ✅ 5. End-of-Milestone Checklist

Before concluding a session:
- [ ] Are obsolete plans and temporary notes pruned?
- [ ] Does the living context document reflect the true current state?
- [ ] Are all newly introduced architecture decisions or config keys documented?
- [ ] Are context files staged and committed with the code deliverable?
- [ ] Has `/compact` or a fresh session been suggested if a major milestone was reached?
