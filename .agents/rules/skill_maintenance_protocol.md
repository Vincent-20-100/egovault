# Skill Maintenance & Patching Protocol (`rules/skill_maintenance_protocol.md`)

> **Applies to**: every skill in `data-dev-suite`. Each skill links here instead of restating this protocol.

---

## 1. When This Triggers

While applying any skill, you (the AI agent) or the user hit one of:
- An API deprecation or library breaking change (NumPy, Polars, scikit-learn, statsmodels...).
- Unexpected runtime friction or an edge-case bug the skill's guidance didn't anticipate.
- A genuine **knowledge gap**: the skill simply doesn't cover the topic at hand.

## 2. Sequence

1. **Solve the user's immediate task first.** Fix the bug, ship the answer, verify it works. Never block the user's task on skill maintenance.
2. **Diagnose the root cause** of the friction:
   - **(a) Stale or wrong instruction** — the skill said something that turned out to be outdated or incorrect.
   - **(b) Coverage gap** — the skill was simply silent on this topic, and closing it required consulting an external authoritative source (official docs, changelog, a paper, a vendor guide).
3. **Propose the patch, matched to the cause**:
   - **(a) Stale/wrong** → propose a direct, surgical edit to the relevant `SKILL.md` or `references/*.md` line.
   - **(b) Coverage gap** → do **not** just answer inline and let the research evaporate at the end of the session. Propose creating a **new dedicated reference file** (a "sous-skill") under `skills/<skill-name>/references/`, citing the source(s) consulted, and add one row for it in the skill's Trigger Matrix. This turns a one-off research detour into permanent, reusable depth for the next session.
4. **Sync across environments**: offer to run `./install.ps1` or `bash install.sh` to propagate the update to `~/.claude/`, `~/.gemini/`, and any scaffolded project's `.agents/`.

## 3. Guardrail: Keep the Top Layer Compact

When patching, prefer adding depth in `references/` over growing `SKILL.md` itself. `SKILL.md` stays a compact index of principles, pitfalls, and reflexes; long-tail precision belongs one layer down, loaded only when its trigger matches.
