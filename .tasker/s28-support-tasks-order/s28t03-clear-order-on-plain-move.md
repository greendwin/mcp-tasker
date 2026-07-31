---
id: s28t03
slug: clear-order-on-plain-move
status: pending
---

# Clear order on plain move

**Goal**
A plain `tasker move` (`--parent`, `--root`, or `--id`) clears the moved task's `order` so it re-enters its new sibling set in the unset tail. If the task was a file *solely* to hold its order, it auto-downgrades back to inline.

**Decisions & constraints**
- `order` is a rank relative to a *specific* sibling set; carrying a value across a re-home is meaningless (sparse numbers from the old parent would drop it arbitrarily among new siblings). So plain `move` drops it.
- This is the "move, don't place" path. The explicit "move *and* place" path (`order --parent`) comes in a later slice and must NOT clear.
- Downgrade reuses `move`'s existing auto-downgrade path — only when the task has no description and no file-based subtasks after clearing order.
- Depends only on the `order` field (slice 1); does not need the reorder engine.

**Edge cases**
- Task with a description or file-based subtasks: order cleared, but stays a file (no downgrade).
- Task moved that had no order: no-op on the order dimension.
- `move --id` (rename within same parent implied by new id): still clears order — the new id may land it in a different sibling context.

**Key files**
- `src/tasker/cli/_organize_commands.py` (move command)
- `src/tasker/repo/_move_task.py` (move mechanics + existing auto-downgrade)

**Acceptance criteria**
- Moving an ordered task under a new parent leaves it with `order` unset (sorts in the new parent's unset tail by id).
- A task that was auto-upgraded to a file only for its order, moved and thereby cleared, downgrades back to an inline bullet in the destination.
- A task with a description keeps its file after a move that clears order.
