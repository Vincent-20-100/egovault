---
name: save-progress
description: "Use when the user signals end of session, asks to stop, or says save/ship/wrap up. Updates context files and prepares for clean exit."
---

# Save Progress

Update the project's living context files so the next session starts with full knowledge.

## Steps

1. **Update `PROJECT-STATUS.md`:**
   - Update "Next action" to reflect current state
   - Move completed items from "Pending tasks"
   - Add today's session to "Session history" table
   - Update roadmap if priorities changed

2. **Rewrite `SESSION-CONTEXT.md`:**
   - This file is REWRITTEN, not appended
   - Summarize current architectural decisions still active
   - List traps to avoid (learned this session)
   - Update deferred items table
   - Update open questions requiring discussion
   - Remove outdated reasoning from previous sessions

3. **Checklist before confirming:**
   - [ ] Both files reflect the TRUE current state
   - [ ] No stale information carried over
   - [ ] Next action is clear and actionable
   - [ ] Open questions are documented

4. **Commit and push** both files.

5. **Report to user:** "Progress saved. Safe to close."
