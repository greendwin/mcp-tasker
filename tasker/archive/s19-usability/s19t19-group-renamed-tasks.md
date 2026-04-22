---
id: s19t19
slug: group-renamed-tasks
status: done
---

# Group renamed tasks

When moving multiple tasks, group all "Renamed tasks" into a single block at the end instead of printing per-task.

Decisions:
- Pure cosmetic change — collect renames across the loop, print as one block after all "Task X moved" lines
- Same logic for root moves and parent moves
- On error mid-loop, skip the rename summary and let the error propagate
