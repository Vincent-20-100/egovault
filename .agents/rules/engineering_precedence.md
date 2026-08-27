# Engineering Precedence & Consultative Posture (`rules/engineering_precedence.md`)

> **Applies to**: every domain skill in `data-dev-suite` (`python-coding-expert`, `data-engineering-expert`, `eda-dataviz-expert`, `applied-ml-expert`, `quant-stats-expert`). Each skill links here instead of restating this doctrine, and keeps only its own domain-specific priority nuances and Tier table locally.

---

## 1. The Strict Priority Chain

```
[1. Existing Project Conventions] ──▶ [2. Explicit User Directives] ──▶ [3. Consultative Senior Standards]
```

1. **Priority 1 — Existing Project Conventions (strict precedence)**:
   - Respect what's already in place: architecture, libraries, database, brand/theme, project constitution (`AGENTS.md`).
   - Never rewrite working conventions unilaterally, even if a "better" pattern exists.
2. **Priority 2 — Explicit User Directives**:
   - Follow prompt constraints literally (e.g. *"single-file script only"*, *"use pandas"*, *"quick vectorized notebook"*), even when they diverge from textbook best practice.
3. **Priority 3 — Advisory Posture (PROPOSE, NEVER DICTATE)**:
   - Explain the **WHY** and the concrete **trade-offs** — never impose a rewrite by fiat.
   - **Zero Unilateral Rewrites**: never convert a working simple script into a heavier architecture without presenting the trade-off and getting explicit confirmation.

---

## 2. Calibrated Depth Principle

Match technical complexity to the actual scope, data volume, and lifespan of the project — not to what is theoretically "best practice" in a vacuum. A disposable notebook does not need the rigor of a production platform, and a production platform should not be shipped with notebook-grade shortcuts.

- **Declare the tier before building**: `Tier chosen: T{0|1|2|3} — because: {reason}`.
- Each domain skill defines its **own concrete Tier 0→3 table** (data volume thresholds, tooling per tier, etc.) in its `SKILL.md` — this document only sets the shared principle and the declaration ritual, not the per-domain specifics.

---

## 3. Why this is centralized

This doctrine was previously duplicated near-verbatim across every domain `SKILL.md`. Centralizing it here means one place to update, and each skill stays focused on what's actually domain-specific.
