# Autonomous Execution & Security Doctrine (`rules/autonomy.md`)

> **Enforcement**: Automated via lifecycle hooks (`hooks.json` / `security_gate.py`) and agent behavioral directives.
> Applicable across all AI coding agent environments (Antigravity, Claude Code, Gemini CLI, Cursor, Cline).

---

## 1. Autonomous Execution Principles

1. **Continuous Execution & Zero Micromanagement**:
   - Once a plan, specification, or user request is formulated, proceed end-to-end autonomously.
   - Do NOT stop to ask permission or trigger interactive confirmation tools (`ask_question`) for routine technical decisions, syntax choices, directory creation, or running tests.
   - Take sensible engineering defaults aligned with project conventions (`AGENTS.md`) and proceed until task completion.

2. **Self-Correcting Feedback Loop**:
   - When encountering a test failure or linter warning, inspect the error output, fix the root cause, and re-run tests autonomously without waiting for human intervention.
   - Iterate within reasonable bounds before declaring a blocking issue.

---

## 2. Automated Safety & Escalation Boundaries

Security is strictly enforced through automated deterministic hooks:

| Level | Policy | Actions / Scope |
| :--- | :--- | :--- |
| **🟢 ALLOW** | **Autonomous execution** | `uv`, `pytest`, `ruff`, `python`, `mkdir`, `mv`, `ls`, `dir`, `cat`, `git status`, `git add`, `git commit`, `git diff`, `git checkout`, `git switch`, `git stash`, file edits in project |
| **🟡 ASK** | **Human confirmation required** | `git push` (never push upstream without human sign-off), `git reset --hard`, `git restore .`, database drops |
| **🔴 DENY** | **Hard blocked by security gate** | `rm -rf`, `sudo`, `dd`, `mkfs`, `format`, forkbombs, `curl \| sh`, accessing/writing secrets (`~/.ssh`, `~/.aws`, `~/.gnupg`, `.env` except `.env.example`, `.git/` internals) |

---

## 3. Reporting Protocol

- Report back concise, high-signal summaries only upon **full task completion** or upon encountering an **unresolvable fatal blocker**.
- Always include direct file links and cite concrete verification evidence (test outputs, execution results).
