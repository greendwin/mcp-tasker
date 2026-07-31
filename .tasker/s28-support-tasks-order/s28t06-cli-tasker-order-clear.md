---
id: s28t06
slug: cli-tasker-order-clear
status: pending
---

# CLI: tasker order --clear

**Goal**
`tasker order --clear <ids…>` removes each listed task's order, returning it to the unset tail. Remaining ordered siblings renumber to stay well-spaced. A task that became a file *solely* to hold its order auto-downgrades back to an inline bullet.

**Decisions & constraints**
- Clearing lives on the `order` command (consistent with where order is set), not `edit`.
- Uses the reorder engine's clear operation (slice 4) to renumber the remainder.
- Auto-downgrade mirrors `move`'s existing behavior: downgrade only when the task has no description and no file-based subtasks after clearing.
- Symmetric with slice 3 (plain `move` also clears), but here the task stays under the same parent.

**Edge cases**
- Clearing a task that has a description / file-based subtasks: order cleared, file retained.
- Clearing all ordered siblings: ordered set becomes empty; everything sorts by id.
- Clearing a task that was already unset: no-op.
- Clearing multiple ids in one call: single renumber pass over the remaining ordered set.

**Key files**
- `src/tasker/cli/_organize_commands.py` (`order --clear`)
- `src/tasker/repo/_order.py` (clear op) + repo downgrade path (shared with `move`)

**Acceptance criteria**
- `tasker order --clear t02` removes `t02`'s order; it now sorts in the unset tail by id.
- Remaining ordered siblings stay correctly sequenced (well-spaced) after clear.
- A task that was a file only for its order downgrades to inline on clear; one with a description does not.
