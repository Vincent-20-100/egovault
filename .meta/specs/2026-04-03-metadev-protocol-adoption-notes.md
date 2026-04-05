# Brainstorm Notes — Adopting metadev-protocol patterns into EgoVault

**Date:** 2026-04-03
**Status:** VALIDATED — ready for spec
**Context:** User discovered metadev-protocol (a Copier template for AI-assisted Python projects) and obra/superpowers (Claude Code plugin with 14 dev workflow skills). Both align strongly with EgoVault's existing patterns. Decision: adopt the best ideas without migrating.

---

## Source documents

- **metadev-protocol philosophy:** shared by user in conversation (DOC 1 — "The Meta Protocol — Philosophy & Design")
- **metadev-protocol guide:** shared by user in conversation (DOC 2 — "Guide — {{ project_name }}")
- **obra/superpowers:** https://github.com/obra/superpowers — Claude Code plugin, 14 skills, installable via `/plugin install superpowers@claude-plugins-official`

---

## Key discovery: Superpowers is already in use

EgoVault's CLAUDE.md already references 5 Superpowers skills:
- `superpowers:brainstorming`
- `superpowers:writing-plans`
- `superpowers:executing-plans`
- `superpowers:requesting-code-review`
- `superpowers:systematic-debugging`

These work because the user has the Superpowers plugin installed on their machine. The skills are NOT defined in the repo — they come from the plugin.

### Superpowers provides 14 skills total

| Skill | Category | Already used by EgoVault |
|-------|----------|------------------------|
| `brainstorming` | Collaboration | Yes |
| `writing-plans` | Collaboration | Yes |
| `executing-plans` | Collaboration | Yes |
| `requesting-code-review` | Collaboration | Yes |
| `systematic-debugging` | Debugging | Yes |
| `dispatching-parallel-agents` | Collaboration | No (available) |
| `subagent-driven-development` | Collaboration | No (available) |
| `receiving-code-review` | Collaboration | No (available) |
| `using-git-worktrees` | Collaboration | No (available) |
| `finishing-a-development-branch` | Collaboration | No (available) |
| `test-driven-development` | Testing | No (available) |
| `verification-before-completion` | Debugging | No (available) |
| `using-superpowers` | Meta | No (available) |
| `writing-skills` | Meta | No (available) |

### Superpowers output paths are configurable

Superpowers respects user preferences in CLAUDE.md for output locations:

```
# Default (Superpowers convention):
docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md

# Can be overridden in CLAUDE.md:
.meta/specs/YYYY-MM-DD-<topic>.md
.meta/plans/YYYY-MM-DD-<topic>.md
```

This means we can rename `docs/superpowers/` → `.meta/` and just add a redirect instruction in CLAUDE.md. No skill wrappers needed.

---

## Diagnostic: EgoVault vs metadev-protocol

| Concept metadev | EgoVault actuel | Gap |
|---|---|---|
| CLAUDE.md ≤60 lines (la loi) | 408 lines, 13 rules + structure + workflow | **Too big** — LLM ignores rules |
| GUIDELINES.md (le mentor) | Doesn't exist | G1-G13 mix law and advice |
| PILOT.md (dashboard) | PROJECT-STATUS.md | **OK** — same role, different name |
| SESSION-CONTEXT.md | SESSION-CONTEXT.md | **OK** — identical |
| `.meta/` (process separated) | `docs/superpowers/` | **OK** — same idea, different name |
| Skills (Claude Code `.claude/skills/`) | Referenced in docs, never created locally | **No gap** — Superpowers plugin handles it |
| Hooks PostToolUse (ruff auto) | No hooks | **Gap** — no automatic enforcement |
| Progressive disclosure | Everything in CLAUDE.md | **Gap** — context overload |
| `/ship` (end-of-session checklist) | Manual (user must remind) | **Gap** — needs custom skill |

---

## Decision A — Strategy for skills (updated from metadev-protocol learnings)

**Chosen: Three-layer architecture — CLAUDE.md (law) + project skills (fallbacks) + Superpowers (advanced).**

```
┌────────────────┬────────────────────────────┬──────────────────────────────────────────────┐
│     Layer      │           Source            │                    Role                      │
├────────────────┼────────────────────────────┼──────────────────────────────────────────────┤
│ CLAUDE.md      │ Our project                │ Law — automatisms, rules, redirects          │
│                │                            │ Superpowers outputs to .meta/scratch/        │
├────────────────┼────────────────────────────┼──────────────────────────────────────────────┤
│ Project skills │ .claude/skills/            │ /save-progress, /lint, /test (unique to us)  │
│                │                            │ + /brainstorm, /plan (lightweight fallbacks)  │
├────────────────┼────────────────────────────┼──────────────────────────────────────────────┤
│ Superpowers    │ obra/superpowers (installed │ Advanced workflows — overrides fallbacks     │
│ plugin         │ user-level)                │ when installed                                │
└────────────────┴────────────────────────────┴──────────────────────────────────────────────┘
```

### Skills to create in `.claude/skills/`:

| Skill | Role | Unique to us? |
|-------|------|--------------|
| `/save-progress` | Update PROJECT-STATUS.md + SESSION-CONTEXT.md, checklist | Yes — our context system |
| `/lint` | `ruff check --fix . && ruff format .` | Yes — simple utility |
| `/test` | `pytest tests/` with optional args | Yes — simple utility |
| `/brainstorm` | Lightweight fallback if Superpowers not installed | Fallback |
| `/plan` | Lightweight fallback if Superpowers not installed | Fallback |

### Key principle: no hard dependency on Superpowers

- Our fallback skills work WITHOUT Superpowers installed
- When Superpowers IS installed, its more complete versions take priority automatically
  (Claude Code gives plugins priority over project skills)
- CLAUDE.md recommends installing Superpowers but doesn't require it

### Superpowers skills we leverage (when installed):

| Superpowers skill | Replaces our... | Output redirected to |
|---|---|---|
| `superpowers:brainstorming` | `/brainstorm` (fallback) | `.meta/scratch/spec-<topic>.md` |
| `superpowers:writing-plans` | `/plan` (fallback) | `.meta/scratch/plan-<topic>.md` |
| `superpowers:executing-plans` | — (new capability) | Inline execution |
| `superpowers:systematic-debugging` | — (new capability) | Terminal |
| `superpowers:requesting-code-review` | — (new capability) | Terminal |
| `superpowers:test-driven-development` | — (new capability) | tests/ |

**Installation (once per machine):** `/install-plugin obra/superpowers`

---

## Decision B — Output path redirection (updated)

**Chosen: Redirect Superpowers outputs to `.meta/scratch/` (drafts) via CLAUDE.md instruction.**

Brainstorms and plans start as **drafts in scratch/**, then get promoted to specs/ or plans/ once validated. This is the metadev-protocol pattern.

```markdown
## Superpowers output paths

Specs and plans go in `.meta/scratch/`, not `docs/superpowers/`:
- Brainstorm drafts → `.meta/scratch/spec-<topic>.md`
- Plan drafts → `.meta/scratch/plan-<topic>.md`
- Once validated: move to `.meta/specs/` or `.meta/plans/`
- Audits → `.meta/audits/audit-results-<date>.md`
```

Superpowers reads CLAUDE.md at session start and respects user preferences.

---

## Decision C — Split CLAUDE.md (law vs mentor)

**Chosen: Split into CLAUDE.md (≤80 lines, the law) + `.meta/GUIDELINES.md` (~150 lines, the mentor).**

### What stays in CLAUDE.md (the law — always loaded):
1. Project identity (3 lines)
2. Tech stack (6 lines)
3. Project structure (tree, ~25 lines)
4. Commands (5 lines)
5. Core automatisms (session start/end, commits, context files — 15 lines)
6. Superpowers output paths (5 lines)
7. Reference to GUIDELINES.md: "Apply rules from `.meta/GUIDELINES.md`" (3 lines)

**Total: ~70 lines — well within the ≤80 target.**

### What moves to `.meta/GUIDELINES.md` (the mentor — read at session start):
- G1-G13 rules with examples
- Pre-commit checklist
- Convention details (Python, Vault, Scripts)
- Document map (permanent vs provisional)
- Architecture details (G4 VaultContext pattern)

### Key principle from metadev-protocol:
> "Too many rules in one file and the LLM ignores them. Too few and important practices get lost. The split gives precision where it matters (law) and breadth where it helps (mentor)."

---

## Decision D — Rename `docs/superpowers/` → `.meta/`

**Chosen: Rename for portability and clarity.**

```
.meta/
├── specs/              ← Active specs and brainstorm notes
│   └── future/         ← Validated specs NOT YET implemented
├── plans/              ← Active implementation plans
├── audits/             ← Audit results (dated)
├── scratch/            ← Drafts, temp files (gitignored)
├── archive/            ← Implemented or obsolete specs and plans
│   ├── specs/
│   └── plans/
├── GUIDELINES.md       ← Rules G1-G13 (the mentor)
└── ARCHITECTURE.md     ← (future: if we move it here from docs/architecture/)
```

Note: `SESSION-CONTEXT.md` and `PROJECT-STATUS.md` stay at root (they need to be visible and found immediately).

---

## Decision E — Hooks

**Chosen: Add PostToolUse hook for ruff after Python file edits.**

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

Also consider pre-commit hooks (ruff + trailing-whitespace + check-yaml).

---

## Execution plan — 6 steps (updated)

**Note:** No fallback skills (/brainstorm, /plan) in this project — Superpowers is assumed installed.
Only project-specific skills are created (/save-progress, /lint, /test).

| Step | What | Files impacted | Effort |
|------|------|---------------|--------|
| 1 | Split CLAUDE.md → law (~80 lines) + `.meta/GUIDELINES.md` (~150 lines) | CLAUDE.md, .meta/GUIDELINES.md (new) | Medium |
| 2 | Rename `docs/superpowers/` → `.meta/` + update all refs | All docs, CLAUDE.md, dev workflow spec | Medium |
| 3 | Add Superpowers output paths section in CLAUDE.md | CLAUDE.md | Small |
| 4 | Create project-specific skills: `/save-progress`, `/lint`, `/test` | .claude/skills/ (3 new dirs) | Small |
| 5 | Add hooks (ruff PostToolUse) | .claude/settings.json | Small |
| 6 | Clean stale refs (G4 "spec pending", etc.) | CLAUDE.md, .meta/GUIDELINES.md | Small |

### Dependencies:
- Step 2 must happen before Step 3 (paths reference `.meta/`)
- Step 1 can happen independently
- Steps 4, 5, 6 are independent

### Parallelizable:
- Steps 1 + 4 + 5 can run in parallel
- Then Steps 2 + 3 + 6 sequentially (they touch the same files)

---

## What this does NOT change

- **No code changes** — this is purely process/docs/config
- **Superpowers is required** — no fallback skills in this project (unlike metadev-protocol template)
- **PROJECT-STATUS.md stays at root** — not moved to `.meta/`
- **SESSION-CONTEXT.md stays at root** — not moved to `.meta/`
- **The 7-phase workflow stays** — just the spec moves from `docs/superpowers/specs/` to `.meta/specs/`
- **G1-G13 rules stay** — they just move house (CLAUDE.md → GUIDELINES.md)
