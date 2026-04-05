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
